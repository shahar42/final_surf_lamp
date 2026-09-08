"""
Unit tests for the pure helpers in web_and_database/blueprints/admin.py

NOTE on thresholds: get_device_status hardcodes 15 min (active) and 60 min
(stale) cutoffs. shared_config.py defines LAMP_ONLINE_THRESHOLD_SECONDS (1h)
and LAMP_STALE_THRESHOLD_SECONDS (24h) as the system-wide values, and the
health endpoint and MCP tools use those. The two disagree. These tests pin
the *current* admin behaviour so a future unification is a deliberate change.
"""

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from blueprints.admin import get_broadcast_expiry, get_device_status

NOW = datetime(2026, 1, 15, 12, 0, 0)


@pytest.mark.unit
class TestDeviceStatus:
    def test_never_when_null(self):
        assert get_device_status(None, NOW) == ("never", "Never connected", None)

    def test_active_just_now(self):
        status, text, iso = get_device_status(NOW - timedelta(seconds=30), NOW)
        assert status == "active"
        assert text == "Just now"
        assert iso == (NOW - timedelta(seconds=30)).isoformat()

    def test_active_under_15_minutes(self):
        status, text, _ = get_device_status(NOW - timedelta(minutes=14), NOW)
        assert (status, text) == ("active", "14 min ago")

    def test_stale_between_15_and_60_minutes(self):
        assert get_device_status(NOW - timedelta(minutes=15), NOW)[0] == "stale"
        assert get_device_status(NOW - timedelta(minutes=59), NOW)[0] == "stale"

    def test_offline_at_60_minutes_in_hours(self):
        status, text, _ = get_device_status(NOW - timedelta(hours=1), NOW)
        assert (status, text) == ("offline", "1 hour ago")
        status, text, _ = get_device_status(NOW - timedelta(hours=5), NOW)
        assert (status, text) == ("offline", "5 hours ago")

    def test_offline_over_48_hours_in_days(self):
        status, text, _ = get_device_status(NOW - timedelta(hours=48), NOW)
        assert (status, text) == ("offline", "2 days ago")
        status, text, _ = get_device_status(NOW - timedelta(days=10), NOW)
        assert (status, text) == ("offline", "10 days ago")

    def test_timezone_aware_input_is_normalised(self):
        """DB rows may come back tz-aware; comparison must not raise or shift."""
        aware = (NOW - timedelta(minutes=5)).replace(tzinfo=timezone.utc)
        status, text, iso = get_device_status(aware, NOW)
        assert (status, text) == ("active", "5 min ago")
        assert "+" not in iso  # tzinfo stripped before isoformat


@pytest.mark.unit
class TestBroadcastExpiry:
    @freeze_time("2026-01-15 12:00:00")
    @pytest.mark.parametrize("requested,hours", [(2, 2), (5, 5), (10, 10), ("5", 5)])
    def test_allowed_durations(self, requested, hours):
        assert get_broadcast_expiry(requested) == datetime(2026, 1, 15, 12 + hours, 0, 0)

    @freeze_time("2026-01-15 12:00:00")
    @pytest.mark.parametrize("requested", [None, "", 3, 24, "abc", -1])
    def test_anything_else_defaults_to_two_hours(self, requested):
        assert get_broadcast_expiry(requested) == datetime(2026, 1, 15, 14, 0, 0)
