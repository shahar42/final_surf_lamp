"""
Integration tests for GET /api/arduino/v3/<id>/data, the endpoint every
current lamp polls. Responses are decoded with the same C++ parser the
firmware shares, so these assertions are about what the LEDs will do.
"""

from datetime import datetime, time, timedelta, timezone

import pytest
from freezegun import freeze_time

from ..conftest import ALL_DAY, BROWSER_UA, LAMP_UA, decode_v3

MAX_WAVE_THRESH_CM = 0x3FF
MAX_WIND_THRESH_KN = 0x7F
MID_BRIGHTNESS_PCT = 30  # BRIGHTNESS_LEVELS['MID'] * 100
NOON_UTC = "2026-01-15 10:00:00"      # 12:00 Israel
LATE_UTC = "2026-01-15 21:00:00"      # 23:00 Israel, inside default quiet hours


def get_v3(client, arduino_id, headers=LAMP_UA):
    return client.get(f"/api/arduino/v3/{arduino_id}/data", headers=headers)


@pytest.mark.integration
class TestShape:
    def test_v3_returns_26_bytes_octet_stream(self, client, lamp):
        resp = get_v3(client, 14)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/octet-stream"
        assert len(resp.data) == 26
        decode_v3(resp.data)  # CRCs valid

    def test_v3_unknown_arduino_404(self, client, lamp):
        resp = get_v3(client, 999)
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Arduino not found"

    def test_v3_mac_derived_large_id_works(self, client, make_location, make_user, make_arduino):
        loc = make_location()
        user = make_user(location=loc.location)
        make_arduino(16777215, user, loc.location)
        assert get_v3(client, 16777215).status_code == 200


@pytest.mark.integration
class TestConditions:
    def test_v3_carries_location_readings(self, client, lamp):
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_wave_height() == 120
        assert surf.get_wave_period() == 8
        assert surf.get_wind_speed() == 5
        assert surf.get_wind_direction() == 180
        assert surf.get_data_available() is True

    def test_v3_stale_warning_from_consecutive_updates(self, client, make_location, make_user, make_arduino):
        from config import STALE_DATA_THRESHOLD
        loc = make_location(consecutive_identical_updates=STALE_DATA_THRESHOLD + 1)
        user = make_user(location=loc.location)
        make_arduino(14, user, loc.location)
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_stale_data() is True

    def test_v3_data_available_false_when_no_conditions(self, client, make_location, make_user, make_arduino):
        loc = make_location(wave_height_m=None, wind_speed_mps=None)
        user = make_user(location=loc.location)
        make_arduino(14, user, loc.location)
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_data_available() is False
        assert surf.get_wave_height() == 0


@pytest.mark.integration
class TestHoursAndBrightness:
    @freeze_time(NOON_UTC)
    def test_v3_off_hours_flag_set(self, client, make_location, make_user, make_arduino):
        loc = make_location()
        user = make_user(location=loc.location, **ALL_DAY)
        make_arduino(14, user, loc.location)
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_off_hours() is True
        assert surf.get_quiet_hours() is False

    @freeze_time(LATE_UTC)
    def test_v3_off_hours_and_quiet_hours_both_reported(self, client, make_location, make_user, make_arduino):
        """Both bits travel; the firmware's priority chain (errors > OFF > QUIET)
        decides. The server must not suppress OFF because QUIET is also true."""
        loc = make_location()
        user = make_user(location=loc.location, quiet_times_enabled=True, **ALL_DAY)
        make_arduino(14, user, loc.location)
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_off_hours() is True
        assert surf.get_quiet_hours() is True

    @freeze_time(LATE_UTC)
    def test_v3_quiet_hours_forces_mid_brightness(self, client, make_location, make_user, make_arduino):
        loc = make_location()
        user = make_user(location=loc.location, quiet_times_enabled=True, brightness_level=1.0)
        make_arduino(14, user, loc.location)
        surf, settings = decode_v3(get_v3(client, 14).data)
        assert surf.get_quiet_hours() is True
        assert settings.get_brightness() == MID_BRIGHTNESS_PCT

    @freeze_time(NOON_UTC)
    def test_v3_normal_hours_uses_user_brightness(self, client, make_location, make_user, make_arduino):
        loc = make_location()
        user = make_user(location=loc.location, quiet_times_enabled=True, brightness_level=1.0)
        make_arduino(14, user, loc.location)
        surf, settings = decode_v3(get_v3(client, 14).data)
        assert surf.get_quiet_hours() is False
        assert settings.get_brightness() == 100


@pytest.mark.integration
class TestThresholdShim:
    def test_v3_threshold_inside_range_sends_min(self, client, make_location, make_user, make_arduino):
        loc = make_location(wave_height_m=1.5)
        user = make_user(location=loc.location, wave_threshold_m=1.0, wave_threshold_max_m=2.0)
        make_arduino(14, user, loc.location)
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_wave_threshold() == 100  # blink: 150 >= 100

    def test_v3_threshold_shim_above_max_sends_saturated_sentinel(self, client, make_location, make_user, make_arduino):
        """Wave 2.5 m above the user's 2.0 m max: the lamp must NOT blink, so the
        threshold on the wire must exceed any reading (field max, not a wrapped value)."""
        loc = make_location(wave_height_m=2.5, wind_speed_mps=20.0)  # 20 m/s = 38.9 kn
        user = make_user(location=loc.location, wave_threshold_m=1.0, wave_threshold_max_m=2.0,
                         wind_threshold_knots=10.0, wind_threshold_max_knots=30.0)
        make_arduino(14, user, loc.location)
        surf, _ = decode_v3(get_v3(client, 14).data)
        assert surf.get_wave_threshold() == MAX_WAVE_THRESH_CM
        assert surf.get_wave_threshold() > surf.get_wave_height()
        assert surf.get_wind_threshold() == MAX_WIND_THRESH_KN

    def test_v3_two_lamps_same_beach_different_owners(self, client, make_location, make_user, make_arduino):
        """End-to-end guard for the location-cache leak fixed in 207f0dd."""
        loc = make_location(wave_height_m=1.2)
        alice = make_user(location=loc.location, wave_threshold_m=1.0, wave_threshold_max_m=3.0, wind_threshold_knots=10.0)
        bob = make_user(location=loc.location, wave_threshold_m=0.5, wave_threshold_max_m=0.6, wind_threshold_knots=25.0)
        make_arduino(14, alice, loc.location)
        make_arduino(15, bob, loc.location)

        surf_a, _ = decode_v3(get_v3(client, 14).data)
        surf_b, _ = decode_v3(get_v3(client, 15).data)  # served from the location cache

        assert surf_a.get_wave_threshold() == 100          # inside Alice's range -> blink
        assert surf_b.get_wave_threshold() == MAX_WAVE_THRESH_CM  # above Bob's max -> quiet
        assert surf_a.get_wind_threshold() == 10
        assert surf_b.get_wind_threshold() == 25
        assert surf_a.get_wave_height() == surf_b.get_wave_height()  # shared conditions identical


@pytest.mark.integration
class TestSettings:
    def test_v3_fetch_interval_min_7_minutes(self, client, make_location, make_user, make_arduino):
        loc = make_location()
        user = make_user(location=loc.location)
        make_arduino(14, user, loc.location, request_interval_minutes=3)
        _, settings = decode_v3(get_v3(client, 14).data)
        assert settings.get_fetch_interval_ms() == 7 * 60 * 1000

    def test_v3_default_interval_13_minutes(self, client, lamp):
        _, settings = decode_v3(get_v3(client, 14).data)
        assert settings.get_fetch_interval_ms() == 13 * 60 * 1000

    def test_v3_coordinates_and_tz_for_users_beach(self, client, lamp):
        from locations.beaches import get_beach_by_name
        beach = get_beach_by_name("Sdot Yam")
        _, settings = decode_v3(get_v3(client, 14).data)
        assert settings.get_latitude() == pytest.approx(beach["latitude"], abs=2e-4)
        assert settings.get_longitude() == pytest.approx(beach["longitude"], abs=2e-4)
        assert settings.get_tz_offset() in (2, 3)  # hours, DST dependent

    def test_v3_theme_travels(self, client, make_location, make_user, make_arduino):
        import message_wrapper
        loc = make_location()
        user = make_user(location=loc.location, theme="ocean_sunset")
        make_arduino(14, user, loc.location)
        _, settings = decode_v3(get_v3(client, 14).data)
        assert settings.get_led_theme() == message_wrapper.LEDTheme.OCEAN_SUNSET


@pytest.mark.integration
class TestHeartbeat:
    def test_v3_physical_ua_records_heartbeat(self, client, lamp, fake_redis):
        with freeze_time("2026-01-15 10:00:00"):
            get_v3(client, 14, headers=LAMP_UA)
        ts = float(fake_redis.hget("arduino:last_seen", "14"))
        assert ts == datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc).timestamp()

    def test_v3_dashboard_ua_does_not_record_heartbeat(self, client, lamp, fake_redis):
        get_v3(client, 14, headers=BROWSER_UA)
        assert fake_redis.hget("arduino:last_seen", "14") is None

    def test_v3_redis_down_still_returns_200(self, client, lamp):
        import redis_manager

        class Raising:
            def __getattr__(self, name):
                def boom(*a, **k):
                    raise ConnectionError("redis unreachable")
                return boom

        redis_manager.redis_client = Raising()
        resp = get_v3(client, 14)
        assert resp.status_code == 200
        assert len(resp.data) == 26
