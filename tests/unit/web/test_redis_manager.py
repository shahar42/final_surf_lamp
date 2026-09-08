"""
Unit tests for web_and_database/redis_manager.py

Covers the Redis client singleton (connect/socket timeouts, fail-fast on an
unreachable host), the distributed DB-write rate limiter and its in-memory
fallback, and Redis health recording.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

import redis_manager


@pytest.fixture(autouse=True)
def reset_redis_manager_state(monkeypatch):
    """Isolate the module-level singleton and fallback dict between tests."""
    original_client = redis_manager.redis_client
    original_fallback = redis_manager._db_write_history_fallback
    redis_manager.redis_client = None
    redis_manager._db_write_history_fallback = {}
    monkeypatch.delenv("REDIS_URL", raising=False)
    yield
    redis_manager.redis_client = original_client
    redis_manager._db_write_history_fallback = original_fallback


@pytest.mark.unit
class TestGetRedisClient:
    def test_no_redis_url_returns_none(self):
        assert redis_manager.get_redis_client() is None

    def test_client_has_socket_timeouts(self, monkeypatch):
        captured = {}

        def fake_from_url(url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return MagicMock()

        monkeypatch.setattr(redis_manager.redis, "from_url", fake_from_url)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        client = redis_manager.get_redis_client()

        assert client is not None
        assert captured["socket_connect_timeout"] == redis_manager.REDIS_CONNECT_TIMEOUT_SECONDS
        assert captured["socket_timeout"] == redis_manager.REDIS_SOCKET_TIMEOUT_SECONDS
        assert captured["socket_connect_timeout"] == 2
        assert captured["socket_timeout"] == 2

    @pytest.mark.slow
    def test_unreachable_redis_fails_fast(self, monkeypatch):
        """A non-routable host must fail within a few seconds, not hang on the
        OS TCP timeout (60s+). The ping runs in a daemon thread with a join
        timeout so a regression FAILS this test instead of hanging the suite."""
        import threading

        monkeypatch.setenv("REDIS_URL", "redis://10.255.255.1:6379/0")

        client = redis_manager.get_redis_client()
        assert client is not None

        outcome = {}

        def ping():
            try:
                client.ping()
                outcome["result"] = "unexpected success"
            except Exception as e:  # any redis error is the expected path
                outcome["result"] = type(e).__name__

        worker = threading.Thread(target=ping, daemon=True)
        start = time.monotonic()
        worker.start()
        worker.join(timeout=5.0)
        elapsed = time.monotonic() - start

        assert not worker.is_alive(), f"ping still blocked after {elapsed:.1f}s (no socket timeout)"
        assert outcome["result"] != "unexpected success"
        assert elapsed < 5.0


@pytest.mark.unit
class TestCanWriteToDb:
    def test_can_write_to_db_redis_nx_semantics(self, fake_redis):
        redis_manager.redis_client = fake_redis

        assert redis_manager.can_write_to_db("arduino_1") is True
        assert redis_manager.can_write_to_db("arduino_1") is False

    def test_can_write_to_db_fallback_sampling(self, monkeypatch):
        """No Redis -> ~10% of unique-ID checks pass (DB_FALLBACK_SAMPLING_RATE)."""
        import random

        # Seeded private generator patched in, so the global RNG state is untouched.
        rng = random.Random(42)
        monkeypatch.setattr(redis_manager.random, "random", rng.random)
        redis_manager.redis_client = None

        trials = 2000
        allowed = sum(
            1 for i in range(trials) if redis_manager.can_write_to_db(f"arduino_{i}")
        )
        ratio = allowed / trials

        assert 0.05 <= ratio <= 0.15

    def test_fallback_uses_in_memory_cooldown_after_sampling_passes(self, monkeypatch):
        """Once sampling lets a write through, the same ID is cooled down."""
        monkeypatch.setattr("random.random", lambda: 0.0)  # always pass sampling gate
        redis_manager.redis_client = None

        assert redis_manager.can_write_to_db("arduino_1") is True
        redis_manager.record_db_write("arduino_1")
        assert redis_manager.can_write_to_db("arduino_1") is False


@pytest.mark.unit
class TestRecordDbWrite:
    def test_record_db_write_no_redis_does_not_raise(self):
        """Regression for the UnboundLocalError on the fallback dict rebind."""
        redis_manager.redis_client = None

        redis_manager.record_db_write("arduino_x")  # must not raise

        assert "arduino_x" in redis_manager._db_write_history_fallback

    def test_fallback_history_cleanup_over_1000(self):
        with freeze_time("2026-01-15 12:00:00"):
            now = datetime.now(timezone.utc)
            old_time = now - timedelta(minutes=11)  # older than the 600s cutoff
            for i in range(1000):
                redis_manager._db_write_history_fallback[f"old_{i}"] = old_time
            redis_manager._db_write_history_fallback["recent"] = now - timedelta(minutes=1)

            redis_manager.record_db_write("new_arduino")  # pushes len over 1000, triggers cleanup

            remaining = redis_manager._db_write_history_fallback
            assert "recent" in remaining
            assert "new_arduino" in remaining
            assert not any(k.startswith("old_") for k in remaining)

    def test_fallback_history_capped_at_5000(self):
        with freeze_time("2026-01-15 12:00:00"):
            now = datetime.now(timezone.utc)
            # all recent (well within the 600s age cutoff) so only the 5000-cap trims them
            for i in range(5999):
                redis_manager._db_write_history_fallback[f"id_{i}"] = now - timedelta(seconds=i % 50)

            redis_manager.record_db_write("newest")

            assert len(redis_manager._db_write_history_fallback) == 5000
            assert "newest" in redis_manager._db_write_history_fallback


@pytest.mark.unit
class TestRecordRedisHealth:
    def test_record_redis_health_success_resets_failures(self, monkeypatch):
        import data_base

        mock_health = MagicMock()
        mock_health.consecutive_failures = 5
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_health
        monkeypatch.setattr(data_base, "SessionLocal", MagicMock(return_value=mock_session))

        redis_manager.record_redis_health("web", success=True)

        assert mock_health.consecutive_failures == 0
        assert mock_health.is_healthy is True
        mock_session.commit.assert_called_once()

    def test_record_redis_health_unhealthy_after_3_failures(self, monkeypatch):
        import data_base

        mock_health = MagicMock()
        mock_health.consecutive_failures = 2
        mock_health.total_failures_24h = 0
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_health
        monkeypatch.setattr(data_base, "SessionLocal", MagicMock(return_value=mock_session))

        redis_manager.record_redis_health("web", success=False, error_message="timeout")

        assert mock_health.consecutive_failures == 3
        assert mock_health.is_healthy is False
        mock_session.commit.assert_called_once()
