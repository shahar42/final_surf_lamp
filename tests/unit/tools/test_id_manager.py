"""
Unit tests for tools/manufacturing/id_manager.py (legacy sequential IDs).

Still used by the manufacturing dashboard for old-style firmware. It queried
a `lamps` table that has not existed since the schema refactor (the table is
`arduinos`), so every call raised. Fixed alongside these tests.

Runs against the SQLite DATABASE_URL set in tests/conftest.py; the
`arduinos` table is created from the ORM metadata.
"""

import pytest
from sqlalchemy import create_engine, text

import data_base
from id_manager import IDManager


@pytest.fixture
def manager():
    m = IDManager()  # reads DATABASE_URL (SQLite test file)
    data_base.Base.metadata.create_all(bind=m.engine)
    with m.engine.begin() as conn:
        for table in reversed(data_base.Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield m
    m.engine.dispose()


def insert_ids(manager, ids):
    with manager.engine.begin() as conn:
        conn.execute(text("INSERT INTO users (user_id, username, password_hash, email, location, theme, preferred_output, sport_type, is_admin, off_times_enabled, quiet_times_enabled, brightness_level) "
                          "VALUES (1, 'm', 'x', 'm@example.com', 'Sdot Yam', 'classic_surf', 'meters', 'surfing', 0, 0, 1, 0.3)"))
        conn.execute(text("INSERT INTO locations (location, wave_api_url, wind_api_url) VALUES ('Sdot Yam', 'w', 'x')"))
        for i in ids:
            conn.execute(text("INSERT INTO arduinos (arduino_id, user_id, location, request_interval_minutes) VALUES (:i, 1, 'Sdot Yam', 13)"), {"i": i})


@pytest.mark.unit
class TestIdManager:
    def test_requires_database_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(ValueError):
            IDManager()

    def test_next_id_starts_at_one_when_empty(self, manager):
        assert manager.get_next_available_id() == 1

    def test_next_id_is_max_plus_one(self, manager):
        insert_ids(manager, [3, 14, 7])
        assert manager.get_next_available_id() == 15

    def test_is_id_available(self, manager):
        insert_ids(manager, [14])
        assert manager.is_id_available(14) is False
        assert manager.is_id_available(15) is True

    def test_get_used_ids_descending_with_limit(self, manager):
        insert_ids(manager, [3, 14, 7])
        assert manager.get_used_ids() == [14, 7, 3]
        assert manager.get_used_ids(limit=2) == [14, 7]

    def test_statistics_detect_gaps(self, manager):
        insert_ids(manager, [1, 2, 5])
        stats = manager.get_id_statistics()
        assert stats["total_ids_used"] == 3
        assert stats["highest_id"] == 5
        assert stats["next_available_id"] == 6
        assert stats["gaps_exist"] is True

    def test_statistics_no_gaps(self, manager):
        insert_ids(manager, [1, 2, 3])
        assert manager.get_id_statistics()["gaps_exist"] is False

    def test_mac_derived_ids_do_not_break_next_id(self, manager):
        """A 24-bit MAC-derived lamp in the table pushes 'next sequential' past
        it; the README already says not to use sequential allocation for those.
        This just pins that the query still works with large IDs present."""
        insert_ids(manager, [14, 16777215])
        assert manager.get_next_available_id() == 16777216
