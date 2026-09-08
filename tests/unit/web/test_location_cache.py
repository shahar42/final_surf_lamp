"""
Unit tests for web_and_database/utils/location_cache.py

Covers the V3 location binary cache (Redis-backed, shared per beach) and the
in-memory Location DB object cache. The location cache tests are regression
guards for the per-user leak fixed in 207f0dd: the cached blob must contain
ONLY shared location fields, never a lamp owner's thresholds or hours flags.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

import redis_manager
from config import STALE_DATA_THRESHOLD
from utils import location_cache


def make_location(**overrides):
    defaults = dict(
        wave_period_s=8,
        wave_height_m=1.2,
        wind_speed_mps=5,
        wind_direction_deg=180,
        consecutive_identical_updates=0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class RaisingRedis:
    """Simulates a Redis client that is unreachable for every operation."""

    def get(self, key):
        raise ConnectionError("redis unreachable")

    def setex(self, *args, **kwargs):
        raise ConnectionError("redis unreachable")


@pytest.fixture(autouse=True)
def reset_redis_client_singleton():
    """Isolate the redis_manager module singleton between tests."""
    original = redis_manager.redis_client
    redis_manager.redis_client = None
    yield
    redis_manager.redis_client = original


@pytest.fixture(autouse=True)
def reset_db_location_cache():
    location_cache._db_location_cache.clear()
    yield
    location_cache._db_location_cache.clear()


@pytest.mark.unit
class TestLocationBinaryCache:
    def test_two_users_same_beach_get_own_thresholds(self, fake_redis):
        """Regression for the cache leak fixed in 207f0dd."""
        redis_manager.redis_client = fake_redis
        loc = make_location()

        data_a, _ = location_cache.get_cached_location_binary(
            "Hilton Beach (Tel Aviv)", loc, 1.0, 10, quiet_hours=False, off_hours=False
        )
        data_b, _ = location_cache.get_cached_location_binary(
            "Hilton Beach (Tel Aviv)", loc, 2.5, 25, quiet_hours=False, off_hours=False
        )

        assert data_a["wave_threshold_cm"] == 100
        assert data_b["wave_threshold_cm"] == 250
        assert data_a["wind_speed_threshold_knots"] == 10
        assert data_b["wind_speed_threshold_knots"] == 25
        # shared conditions came from the same cached entry
        assert data_a["wave_height_cm"] == data_b["wave_height_cm"]

    def test_two_users_same_beach_get_own_hours_flags(self, fake_redis):
        """quiet/off flags are per-user, never shared via the cache."""
        redis_manager.redis_client = fake_redis
        loc = make_location()

        data_a, _ = location_cache.get_cached_location_binary(
            "Beach", loc, 1.0, 10, quiet_hours=True, off_hours=False
        )
        data_b, _ = location_cache.get_cached_location_binary(
            "Beach", loc, 1.0, 10, quiet_hours=False, off_hours=True
        )

        assert data_a["quiet_hours_active"] is True
        assert data_a["off_hours_active"] is False
        assert data_b["quiet_hours_active"] is False
        assert data_b["off_hours_active"] is True

    def test_cached_blob_contains_only_location_fields(self, fake_redis):
        """No threshold or hours keys are ever written into the Redis blob."""
        redis_manager.redis_client = fake_redis
        loc = make_location()

        location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        raw = fake_redis.get("location:surf:v4:Beach")
        blob = json.loads(raw)

        assert set(blob.keys()) == {
            "wave_period_s",
            "wave_height_cm",
            "wind_speed_mps",
            "wind_direction_deg",
            "stale_data_warning",
            "data_available",
        }
        assert "wave_threshold_cm" not in blob
        assert "wind_speed_threshold_knots" not in blob
        assert "quiet_hours_active" not in blob
        assert "off_hours_active" not in blob

    def test_second_call_is_cache_hit(self, fake_redis):
        redis_manager.redis_client = fake_redis
        loc = make_location()

        _, hit1 = location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)
        _, hit2 = location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        assert hit1 is False
        assert hit2 is True

    def test_ttl_is_60_seconds(self, fake_redis):
        redis_manager.redis_client = fake_redis
        loc = make_location()

        location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        ttl = fake_redis.ttl("location:surf:v4:Beach")
        assert 59 <= ttl <= 60

    def test_redis_down_returns_data_uncached(self):
        """A raising Redis client must not raise out of the cache helper."""
        redis_manager.redis_client = RaisingRedis()
        loc = make_location()

        data, hit = location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        assert hit is False
        assert data["wave_height_cm"] == 120

    def test_key_prefix_is_v4(self, fake_redis):
        """An old v3 blob (if present) must never be read as v4 data."""
        fake_redis.setex("location:surf:v3:Beach", 60, json.dumps({"stale": "old-format"}))
        redis_manager.redis_client = fake_redis
        loc = make_location()

        location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        assert fake_redis.exists("location:surf:v4:Beach")
        # v3 key is untouched/ignored, not read into the result
        cached_v4 = json.loads(fake_redis.get("location:surf:v4:Beach"))
        assert cached_v4["wave_height_cm"] == 120

    def test_stale_warning_uses_threshold_constant(self, fake_redis):
        redis_manager.redis_client = fake_redis

        loc_ok = make_location(consecutive_identical_updates=STALE_DATA_THRESHOLD)
        data_ok, _ = location_cache.get_cached_location_binary("BeachA", loc_ok, 1.0, 10, False, False)
        assert data_ok["stale_data_warning"] is False  # equal to threshold is not stale (strict >)

        loc_stale = make_location(consecutive_identical_updates=STALE_DATA_THRESHOLD + 1)
        data_stale, _ = location_cache.get_cached_location_binary("BeachB", loc_stale, 1.0, 10, False, False)
        assert data_stale["stale_data_warning"] is True

    def test_data_available_false_when_both_zero(self, fake_redis):
        redis_manager.redis_client = fake_redis
        loc = make_location(wave_height_m=0, wind_speed_mps=0)

        data, _ = location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        assert data["data_available"] is False

    def test_none_fields_become_zero(self, fake_redis):
        redis_manager.redis_client = fake_redis
        loc = make_location(
            wave_period_s=None, wave_height_m=None, wind_speed_mps=None, wind_direction_deg=None
        )

        data, _ = location_cache.get_cached_location_binary("Beach", loc, 1.0, 10, False, False)

        assert data["wave_period_s"] == 0
        assert data["wave_height_cm"] == 0
        assert data["wind_speed_mps"] == 0
        assert data["wind_direction_deg"] == 0
        assert data["data_available"] is False

    def test_get_location_stats_strips_prefix(self, fake_redis):
        redis_manager.redis_client = fake_redis
        loc = make_location()

        location_cache.get_cached_location_binary("Hilton Beach", loc, 1.0, 10, False, False)
        location_cache.get_cached_location_binary("Gordon Beach", loc, 1.0, 10, False, False)

        stats = location_cache.get_location_stats()

        assert stats["cached_locations"] == 2
        assert set(stats["locations"]) == {"Hilton Beach", "Gordon Beach"}


@pytest.mark.unit
class TestDbLocationCache:
    def test_db_location_cache_ttl_and_invalidate(self):
        mock_location = make_location()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_location

        with freeze_time("2026-01-15 12:00:00"):
            result1 = location_cache.get_location_from_db_cached(mock_db, "Beach")
            assert result1 is mock_location
            assert mock_db.query.call_count == 1

            # within the 5-minute TTL -> cache hit, no second query
            result2 = location_cache.get_location_from_db_cached(mock_db, "Beach")
            assert result2 is mock_location
            assert mock_db.query.call_count == 1

        with freeze_time("2026-01-15 12:05:01"):  # +301s, past the 300s TTL
            location_cache.get_location_from_db_cached(mock_db, "Beach")
            assert mock_db.query.call_count == 2

        location_cache.invalidate_db_location_cache("Beach")
        assert "Beach" not in location_cache._db_location_cache
