"""
Unit tests for web_and_database/utils/helpers.py (misc helpers and caches).

Tests:
- convert_wind_direction (cardinal points, sector boundary rounding, None fallback)
- get_sunset_info_cached (cache hits within 24h, cache expiration after 24h)
- get_coordinates_cached (keyed per user, location change invalidation, default fallback)
- invalidate_user_coordinates_cache (explicit invalidation)
"""

from unittest.mock import MagicMock
import pytest
from freezegun import freeze_time

from utils import helpers
from utils.helpers import (
    convert_wind_direction,
    get_sunset_info_cached,
    get_coordinates_cached,
    invalidate_user_coordinates_cache,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear in-memory caches before and after each test."""
    helpers._sunset_cache.clear()
    helpers._coordinates_cache.clear()
    yield
    helpers._sunset_cache.clear()
    helpers._coordinates_cache.clear()


@pytest.mark.unit
class TestWindDirection:
    def test_wind_direction_cardinal_points(self):
        """Standard cardinal points: 0->N, 90->E, 180->S, 270->W, 360->N."""
        assert convert_wind_direction(0) == "N"
        assert convert_wind_direction(90) == "E"
        assert convert_wind_direction(180) == "S"
        assert convert_wind_direction(270) == "W"
        assert convert_wind_direction(360) == "N"

    def test_wind_direction_boundaries(self):
        """Rounding behavior at 22.5 deg sector boundaries."""
        # 0 to 11.24 -> N (index 0)
        assert convert_wind_direction(11) == "N"
        # 11.25 to 33.74 -> NNE (index 1)
        assert convert_wind_direction(12) == "NNE"
        assert convert_wind_direction(22.5) == "NNE"
        assert convert_wind_direction(33) == "NNE"
        # 34 -> NE (index 2)
        assert convert_wind_direction(34) == "NE"
        assert convert_wind_direction(45) == "NE"
        # Near 360: 349 -> NNW, 350 -> N
        assert convert_wind_direction(348) == "NNW"
        assert convert_wind_direction(350) == "N"

    def test_wind_direction_none_returns_dashes(self):
        """degrees=None returns safe fallback '--'."""
        assert convert_wind_direction(None) == "--"


@pytest.mark.unit
class TestSunsetCache:
    def test_sunset_cache_hit_within_24h(self):
        """Second call within 24h returns cached result without re-invoking function."""
        mock_func = MagicMock(return_value={"sunset_trigger": True, "day_of_year": 15})

        with freeze_time("2026-01-15 10:00:00"):
            res1 = get_sunset_info_cached("Tel Aviv", mock_func)
            res2 = get_sunset_info_cached("Tel Aviv", mock_func)

        assert res1 == {"sunset_trigger": True, "day_of_year": 15}
        assert res2 == res1
        assert mock_func.call_count == 1

    def test_sunset_cache_expires_after_24h(self):
        """Cache expires after 24 hours (86400 seconds) -> recomputed."""
        mock_func = MagicMock(side_effect=[
            {"sunset_trigger": False, "day_of_year": 15},
            {"sunset_trigger": True, "day_of_year": 16},
        ])

        with freeze_time("2026-01-15 10:00:00") as frozen_time:
            res1 = get_sunset_info_cached("Tel Aviv", mock_func)
            assert res1["day_of_year"] == 15
            assert mock_func.call_count == 1

            # Tick 24 hours and 1 second forward
            frozen_time.tick(delta=86401)
            res2 = get_sunset_info_cached("Tel Aviv", mock_func)
            assert res2["day_of_year"] == 16
            assert mock_func.call_count == 2


@pytest.mark.unit
class TestCoordinatesCache:
    def test_coordinates_cache_keyed_per_user(self):
        """Two users with different or same locations get separate cache entries."""
        coords_dict = {
            "Hilton Beach (Tel Aviv)": {"latitude": 32.0910, "longitude": 34.7710},
            "Bat Galim (Haifa)": {"latitude": 32.8242, "longitude": 34.9897},
        }

        user1_coords = get_coordinates_cached(user_id=1, user_location="Hilton Beach (Tel Aviv)", location_coords_dict=coords_dict)
        user2_coords = get_coordinates_cached(user_id=2, user_location="Bat Galim (Haifa)", location_coords_dict=coords_dict)

        assert user1_coords["latitude"] == 32.0910
        assert user2_coords["latitude"] == 32.8242
        assert "user_1" in helpers._coordinates_cache
        assert "user_2" in helpers._coordinates_cache

    def test_coordinates_cache_invalidated_on_location_change(self):
        """When user location changes, cache detects mismatch and fetches new coords."""
        coords_dict = {
            "Hilton Beach (Tel Aviv)": {"latitude": 32.0910, "longitude": 34.7710},
            "Bat Galim (Haifa)": {"latitude": 32.8242, "longitude": 34.9897},
        }

        # User starts in Tel Aviv
        c1 = get_coordinates_cached(user_id=10, user_location="Hilton Beach (Tel Aviv)", location_coords_dict=coords_dict)
        assert c1["latitude"] == 32.0910

        # User changes location to Haifa
        c2 = get_coordinates_cached(user_id=10, user_location="Bat Galim (Haifa)", location_coords_dict=coords_dict)
        assert c2["latitude"] == 32.8242

    def test_coordinates_cache_manual_invalidate(self):
        """invalidate_user_coordinates_cache removes user from cache."""
        coords_dict = {"Hilton Beach (Tel Aviv)": {"latitude": 32.0910, "longitude": 34.7710}}

        get_coordinates_cached(user_id=42, user_location="Hilton Beach (Tel Aviv)", location_coords_dict=coords_dict)
        assert "user_42" in helpers._coordinates_cache

        invalidate_user_coordinates_cache(42)
        assert "user_42" not in helpers._coordinates_cache

    def test_coordinates_unknown_location_falls_back_to_default(self):
        """Unknown location falls back to Tel Aviv coordinates in coords_dict or hardcoded default."""
        coords_dict = {
            "Tel Aviv": {"latitude": 32.0853, "longitude": 34.7818}
        }
        res = get_coordinates_cached(user_id=99, user_location="Unknown Location", location_coords_dict=coords_dict)
        assert res["latitude"] == 32.0853
        assert res["longitude"] == 34.7818

        # If coords_dict doesn't even have Tel Aviv:
        empty_dict = {}
        res_default = get_coordinates_cached(user_id=100, user_location="Unknown", location_coords_dict=empty_dict)
        assert res_default == {"latitude": 32.0853, "longitude": 34.7818}
