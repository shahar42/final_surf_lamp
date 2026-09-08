"""
Unit tests for background_processor.sync_redis_to_database

Heartbeats land in the Redis hash arduino:last_seen on every lamp poll; this
job is the only thing that copies them into arduinos.last_poll_time, which
the health endpoint, MCP tools and dashboard staleness logic read.

History: the job imported a SessionLocal that lamp_repository never defined.
The ImportError was swallowed by the outer except, so the sync silently
failed on every run. test_sync_reaches_the_database is the regression guard.

The bulk UPDATE uses Postgres-only syntax (UPDATE ... FROM (VALUES ...) with
::timestamptz casts), so the engine is mocked and the emitted SQL inspected
rather than executed against SQLite.
"""

import re
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import background_processor
import redis_manager
from shared_config import REDIS_SYNC_BATCH_SIZE


class FakeConn:
    """Records every executed statement; rowcount = rows in that batch."""

    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, query, *args, **kwargs):
        sql = str(query)
        self.statements.append(sql)
        result = MagicMock()
        result.rowcount = len(re.findall(r"\(\d+, '", sql))  # one "(id, 'ts')" tuple per row
        return result

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture
def fake_conn(monkeypatch):
    conn = FakeConn()
    engine = MagicMock()
    engine.connect.return_value = conn
    monkeypatch.setattr(background_processor, "engine", engine)
    return conn


@pytest.fixture
def health_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(redis_manager, "record_redis_health", lambda *a, **k: calls.append((a, k)))
    return calls


@pytest.fixture
def seeded_redis(fake_redis, monkeypatch):
    monkeypatch.setattr(redis_manager, "redis_client", fake_redis)
    return fake_redis


def seed(redis, entries):
    for arduino_id, ts in entries.items():
        redis.hset("arduino:last_seen", arduino_id, ts)


@pytest.mark.unit
class TestSyncRedisToDatabase:
    def test_sync_reaches_the_database(self, seeded_redis, fake_conn, health_calls):
        """Regression: the job must actually execute SQL, not die on an import."""
        seed(seeded_redis, {"14": "1768478400.5", "6689108": "1768478460.0"})

        assert background_processor.sync_redis_to_database() is True

        assert len(fake_conn.statements) == 1
        assert fake_conn.commits == 1
        assert fake_conn.closed is True
        assert health_calls and health_calls[-1][1].get("success") is True

    def test_bulk_update_only_advances_newer_timestamps(self, seeded_redis, fake_conn, health_calls):
        seed(seeded_redis, {"14": "1768478400"})
        background_processor.sync_redis_to_database()
        sql = fake_conn.statements[0]
        assert "UPDATE arduinos" in sql
        assert "last_poll_time IS NULL OR" in sql
        assert "> a.last_poll_time" in sql

    def test_ids_are_ints_and_timestamps_iso_utc(self, seeded_redis, fake_conn, health_calls):
        seed(seeded_redis, {"14": "1768478400"})
        background_processor.sync_redis_to_database()
        sql = fake_conn.statements[0]
        expected_ts = datetime.fromtimestamp(1768478400, timezone.utc).isoformat()
        assert f"(14, '{expected_ts}')" in sql

    def test_batches_of_configured_size(self, seeded_redis, fake_conn, health_calls):
        n = REDIS_SYNC_BATCH_SIZE * 2 + 5
        seed(seeded_redis, {str(i): "1768478400" for i in range(1, n + 1)})

        assert background_processor.sync_redis_to_database() is True

        assert len(fake_conn.statements) == 3
        assert fake_conn.commits == 3

    def test_invalid_entries_skipped_not_fatal(self, seeded_redis, fake_conn, health_calls):
        seed(seeded_redis, {"14": "1768478400", "abc": "1768478400", "15": "not-a-number"})

        assert background_processor.sync_redis_to_database() is True

        sql = fake_conn.statements[0]
        assert "(14," in sql
        assert "abc" not in sql
        assert "(15," not in sql

    def test_only_invalid_entries_returns_true_without_sql(self, seeded_redis, fake_conn, health_calls):
        seed(seeded_redis, {"abc": "x"})
        assert background_processor.sync_redis_to_database() is True
        assert fake_conn.statements == []

    def test_empty_hash_returns_true_without_sql(self, seeded_redis, fake_conn, health_calls):
        assert background_processor.sync_redis_to_database() is True
        assert fake_conn.statements == []

    def test_no_redis_returns_false(self, monkeypatch, fake_conn):
        monkeypatch.setattr(redis_manager, "redis_client", None)
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert background_processor.sync_redis_to_database() is False
        assert fake_conn.statements == []

    def test_db_error_rolls_back_and_reports_failure(self, seeded_redis, fake_conn, health_calls):
        seed(seeded_redis, {"14": "1768478400"})

        def boom(*a, **k):
            raise RuntimeError("db down")

        fake_conn.execute = boom
        assert background_processor.sync_redis_to_database() is False
        assert fake_conn.rollbacks == 1
        assert fake_conn.closed is True
        assert health_calls[-1][1].get("success") is False
