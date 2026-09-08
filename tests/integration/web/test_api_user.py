"""
Integration tests for the user-preference API (blueprints/api_user.py).
Every endpoint: happy path, validation, and auth.
"""

from datetime import time

import pytest

from config import THRESHOLD_LIMITS

ENDPOINTS = [
    ("/update-location", {"location": "Sdot Yam"}),
    ("/update-threshold", {"threshold_min": 1.0}),
    ("/update-wind-threshold", {"threshold_min": 15}),
    ("/update-off-times", {"enabled": True}),
    ("/update-theme", {"theme": "day"}),
    ("/update-led-theme", {"theme_id": "classic_surf"}),
    ("/update-brightness", {"brightness": 0.3}),
    ("/update-unit-preference", {"unit_preference": "feet"}),
    ("/toggle-quiet-hours", {"enabled": False}),
]


def reload_user(db_session, user):
    from data_base import User
    db_session.expire_all()
    return db_session.query(User).filter_by(user_id=user.user_id).one()


@pytest.mark.integration
class TestAuthOnEveryEndpoint:
    @pytest.mark.parametrize("path,payload", ENDPOINTS)
    def test_all_endpoints_require_login(self, client, path, payload):
        resp = client.post(path, json=payload)
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")


@pytest.mark.integration
class TestWaveThreshold:
    def test_update_threshold_persists_min_max(self, client, lamp, login, db_session):
        login(lamp[1])
        resp = client.post("/update-threshold", json={"threshold_min": 0.8, "threshold_max": 2.2})
        assert resp.status_code == 200
        user = reload_user(db_session, lamp[1])
        assert (user.wave_threshold_m, user.wave_threshold_max_m) == (0.8, 2.2)

    def test_update_threshold_min_only_clears_max(self, client, lamp, login, db_session):
        login(lamp[1])
        client.post("/update-threshold", json={"threshold_min": 1.5})
        user = reload_user(db_session, lamp[1])
        assert user.wave_threshold_m == 1.5 and user.wave_threshold_max_m is None

    def test_update_threshold_rejects_min_above_max(self, client, lamp, login):
        login(lamp[1])
        resp = client.post("/update-threshold", json={"threshold_min": 2.0, "threshold_max": 1.0})
        assert resp.status_code == 400

    def test_update_threshold_rejects_out_of_limits(self, client, lamp, login):
        login(lamp[1])
        assert client.post("/update-threshold", json={"threshold_min": THRESHOLD_LIMITS["WAVE_MAX"] + 1}).status_code == 400
        assert client.post("/update-threshold", json={"threshold_min": 1.0, "threshold_max": THRESHOLD_LIMITS["WAVE_MAX"] + 1}).status_code == 400

    def test_update_threshold_rejects_garbage(self, client, lamp, login):
        login(lamp[1])
        assert client.post("/update-threshold", json={"threshold_min": "big"}).status_code == 400


@pytest.mark.integration
class TestWindThreshold:
    def test_update_wind_threshold_persists(self, client, lamp, login, db_session):
        login(lamp[1])
        resp = client.post("/update-wind-threshold", json={"threshold_min": 12, "threshold_max": 30})
        assert resp.status_code == 200
        user = reload_user(db_session, lamp[1])
        assert (user.wind_threshold_knots, user.wind_threshold_max_knots) == (12.0, 30.0)

    def test_update_wind_threshold_rejects_out_of_limits(self, client, lamp, login):
        login(lamp[1])
        assert client.post("/update-wind-threshold", json={"threshold_min": THRESHOLD_LIMITS["WIND_MIN"] - 1}).status_code == 400
        assert client.post("/update-wind-threshold", json={"threshold_min": 30, "threshold_max": 20}).status_code == 400


@pytest.mark.integration
class TestOffTimes:
    def test_update_off_times_persists_and_enables(self, client, lamp, login, db_session):
        login(lamp[1])
        resp = client.post("/update-off-times", json={"enabled": True, "start_time": "22:30", "end_time": "06:15"})
        assert resp.status_code == 200
        user = reload_user(db_session, lamp[1])
        assert user.off_times_enabled is True
        assert user.off_time_start == time(22, 30)
        assert user.off_time_end == time(6, 15)

    def test_update_off_times_disable_keeps_times(self, client, lamp, login, db_session):
        login(lamp[1])
        client.post("/update-off-times", json={"enabled": True, "start_time": "22:00", "end_time": "06:00"})
        client.post("/update-off-times", json={"enabled": False})
        user = reload_user(db_session, lamp[1])
        assert user.off_times_enabled is False
        assert user.off_time_start == time(22, 0)


@pytest.mark.integration
class TestLocation:
    def test_update_location_cascades_to_arduinos(self, client, lamp, login, db_session):
        """1:N rule: one fetch per location updates all child devices, so the
        arduino rows must follow the user."""
        from data_base import Arduino, Location
        login(lamp[1])
        resp = client.post("/update-location", json={"location": "Hilton Beach (Tel Aviv)"})
        assert resp.status_code == 200, resp.get_json()
        assert reload_user(db_session, lamp[1]).location == "Hilton Beach (Tel Aviv)"
        assert db_session.query(Arduino).filter_by(arduino_id=14).one().location == "Hilton Beach (Tel Aviv)"
        assert db_session.query(Location).filter_by(location="Hilton Beach (Tel Aviv)").one()  # auto-created
        with client.session_transaction() as s:
            assert s["user_location"] == "Hilton Beach (Tel Aviv)"

    def test_update_location_invalidates_coordinate_cache(self, client, lamp, login):
        from utils import helpers
        from sunset_calculator import LOCATION_COORDS
        helpers.get_coordinates_cached(lamp[1].user_id, "Sdot Yam", LOCATION_COORDS)
        assert f"user_{lamp[1].user_id}" in helpers._coordinates_cache
        login(lamp[1])
        client.post("/update-location", json={"location": "Hilton Beach (Tel Aviv)"})
        assert f"user_{lamp[1].user_id}" not in helpers._coordinates_cache

    def test_update_location_rejects_unknown_beach(self, client, lamp, login):
        login(lamp[1])
        resp = client.post("/update-location", json={"location": "Atlantis"})
        assert resp.status_code == 400

    def test_update_location_daily_limit(self, client, lamp, login):
        from utils import rate_limit
        login(lamp[1])
        for _ in range(10):
            rate_limit.record_location_change(lamp[1].user_id)
        resp = client.post("/update-location", json={"location": "Hilton Beach (Tel Aviv)"})
        assert resp.status_code == 429


@pytest.mark.integration
class TestThemesBrightnessUnits:
    def test_update_led_theme_only_known_themes(self, client, lamp, login, db_session):
        login(lamp[1])
        assert client.post("/update-led-theme", json={"theme_id": "ocean_sunset"}).status_code == 200
        assert reload_user(db_session, lamp[1]).theme == "ocean_sunset"
        assert client.post("/update-led-theme", json={"theme_id": "neon"}).status_code == 400

    def test_update_led_theme_rejects_dark(self, client, lamp, login):
        """'dark' exists in firmware Themes.cpp but not in the V3 enum; the API
        keeps it out so no user ends up with a theme the wire cannot carry."""
        login(lamp[1])
        assert client.post("/update-led-theme", json={"theme_id": "dark"}).status_code == 400

    def test_update_theme_day_or_dark(self, client, lamp, login, db_session):
        login(lamp[1])
        assert client.post("/update-theme", json={"theme": "day"}).status_code == 200
        assert client.post("/update-theme", json={"theme": "purple"}).status_code == 400

    def test_update_brightness_in_unit_interval(self, client, lamp, login, db_session):
        login(lamp[1])
        assert client.post("/update-brightness", json={"brightness": 0.05}).status_code == 200
        assert reload_user(db_session, lamp[1]).brightness_level == 0.05
        assert client.post("/update-brightness", json={"brightness": 0.0}).status_code == 400
        assert client.post("/update-brightness", json={"brightness": 1.5}).status_code == 400

    def test_update_unit_preference(self, client, lamp, login, db_session):
        login(lamp[1])
        assert client.post("/update-unit-preference", json={"unit_preference": "feet"}).status_code == 200
        assert reload_user(db_session, lamp[1]).preferred_output == "feet"
        assert client.post("/update-unit-preference", json={"unit_preference": "cubits"}).status_code == 400

    def test_toggle_quiet_hours(self, client, lamp, login, db_session):
        login(lamp[1])
        assert client.post("/toggle-quiet-hours", json={"enabled": True}).status_code == 200
        assert reload_user(db_session, lamp[1]).quiet_times_enabled is True
        client.post("/toggle-quiet-hours", json={"enabled": False})
        assert reload_user(db_session, lamp[1]).quiet_times_enabled is False
