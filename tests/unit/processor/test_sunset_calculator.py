"""
Unit tests for surf-lamp-processor/sunset_calculator.py

Still live: the V1 device endpoint and the V2/V3 coordinate lookup read
LOCATION_COORDS from here. The firmware-side calculator was removed in
207f0dd; this is the only sunset logic left in the system.
"""

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from locations.beaches import get_all_beaches
from sunset_calculator import LOCATION_COORDS, add_location_coords, get_sunset_info

ISRAEL_SUMMER = timezone(timedelta(hours=3))


@pytest.mark.unit
class TestLocationCoords:
    def test_every_beach_present_with_coordinates_and_timezone(self):
        for beach in get_all_beaches():
            entry = LOCATION_COORDS[beach["english_name"]]
            assert entry["latitude"] == beach["latitude"]
            assert entry["longitude"] == beach["longitude"]
            assert entry["timezone"]

    def test_legacy_city_names_still_resolve(self):
        """Users registered before the beach migration keep working."""
        for legacy in ("Tel Aviv", "Tel Aviv, Israel", "Haifa, Israel", "Hadera, Israel"):
            assert legacy in LOCATION_COORDS

    def test_add_location_coords(self):
        add_location_coords("Test Reef", 10.0, 20.0, "UTC")
        try:
            assert LOCATION_COORDS["Test Reef"] == {"latitude": 10.0, "longitude": 20.0, "timezone": "UTC"}
        finally:
            LOCATION_COORDS.pop("Test Reef", None)


@pytest.mark.unit
class TestSunsetInfo:
    def test_result_shape(self):
        with freeze_time("2026-06-15 09:00:00"):
            info = get_sunset_info("Sdot Yam")
        assert set(info) == {"sunset_trigger", "day_of_year", "sunset_time", "in_window"}
        assert info["day_of_year"] == 166
        assert len(info["sunset_time"]) == 5 and ":" in info["sunset_time"]

    def test_trigger_outside_window(self):
        with freeze_time("2026-06-15 09:00:00"):  # noon in Israel, far from sunset
            info = get_sunset_info("Sdot Yam")
        assert info["sunset_trigger"] is False
        assert info["in_window"] is False

    def test_trigger_inside_window(self):
        """Read the computed sunset for the day, then freeze time onto it."""
        with freeze_time("2026-06-15 09:00:00"):
            hh, mm = map(int, get_sunset_info("Sdot Yam")["sunset_time"].split(":"))
        sunset_local = datetime(2026, 6, 15, hh, mm, tzinfo=ISRAEL_SUMMER)
        with freeze_time(sunset_local):
            info = get_sunset_info("Sdot Yam", trigger_window_minutes=15)
        assert info["sunset_trigger"] is True

    def test_window_width_respected(self):
        with freeze_time("2026-06-15 09:00:00"):
            hh, mm = map(int, get_sunset_info("Sdot Yam")["sunset_time"].split(":"))
        sunset_local = datetime(2026, 6, 15, hh, mm, tzinfo=ISRAEL_SUMMER)
        with freeze_time(sunset_local + timedelta(minutes=20)):
            assert get_sunset_info("Sdot Yam", trigger_window_minutes=15)["sunset_trigger"] is False
            assert get_sunset_info("Sdot Yam", trigger_window_minutes=30)["sunset_trigger"] is True

    def test_unknown_location_falls_back_to_tel_aviv_not_error(self):
        with freeze_time("2026-06-15 09:00:00"):
            unknown = get_sunset_info("Atlantis")
            tel_aviv = get_sunset_info("Tel Aviv")
        assert unknown == tel_aviv

    def test_summer_sunset_later_than_winter(self):
        with freeze_time("2026-06-15 09:00:00"):
            summer = get_sunset_info("Sdot Yam")["sunset_time"]
        with freeze_time("2026-12-15 09:00:00"):
            winter = get_sunset_info("Sdot Yam")["sunset_time"]
        assert summer > winter  # "19:4x" > "16:4x" as strings, same-width HH:MM
