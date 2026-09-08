"""
Unit tests for web_and_database/utils/helpers.py (hours and timezone logic).

Tests:
- is_quiet_hours (overnight window, boundaries, disabled flag, custom window)
- is_off_hours (overnight window, same-day window, timezone awareness, disabled flag)
- get_current_tz_offset (summer DST vs winter, unknown fallback)
"""

from datetime import time
import pytest
from freezegun import freeze_time

from utils.helpers import is_quiet_hours, is_off_hours, get_current_tz_offset


@pytest.mark.unit
class TestHoursLogic:
    # Israel is Asia/Jerusalem (UTC+2 in winter, UTC+3 in summer)
    LOCATION = "Hilton Beach (Tel Aviv)"

    # --- Quiet Hours Tests ---

    @freeze_time("2026-01-15 21:00:00")  # 21:00 UTC = 23:00 Israel (winter UTC+2)
    def test_quiet_hours_overnight_window_inside(self, mock_location_timezones):
        """23:00 local time is inside default 22:00 - 06:00 quiet hours -> True."""
        assert is_quiet_hours(self.LOCATION, quiet_times_enabled=True) is True

    @freeze_time("2026-01-15 10:00:00")  # 10:00 UTC = 12:00 Israel (winter UTC+2)
    def test_quiet_hours_overnight_window_outside(self, mock_location_timezones):
        """12:00 local time is outside quiet hours -> False."""
        assert is_quiet_hours(self.LOCATION, quiet_times_enabled=True) is False

    @freeze_time("2026-01-15 20:00:00")  # 20:00 UTC = 22:00 Israel (winter UTC+2)
    def test_quiet_hours_boundary_start_inclusive(self, mock_location_timezones):
        """22:00 local is the start boundary (inclusive) -> True."""
        assert is_quiet_hours(self.LOCATION, quiet_times_enabled=True, quiet_start_hour=22, quiet_end_hour=6) is True

    @freeze_time("2026-01-15 04:00:00")  # 04:00 UTC = 06:00 Israel (winter UTC+2)
    def test_quiet_hours_boundary_end_exclusive(self, mock_location_timezones):
        """06:00 local is the end boundary (exclusive) -> False."""
        assert is_quiet_hours(self.LOCATION, quiet_times_enabled=True, quiet_start_hour=22, quiet_end_hour=6) is False

    @freeze_time("2026-01-15 21:00:00")  # 23:00 Israel
    def test_quiet_hours_disabled_flag_wins(self, mock_location_timezones):
        """enabled=False returns False even during quiet hours window."""
        assert is_quiet_hours(self.LOCATION, quiet_times_enabled=False) is False

    def test_quiet_hours_unknown_location_false(self, mock_location_timezones):
        """Location not in LOCATION_TIMEZONES returns False."""
        assert is_quiet_hours("Unknown Nonexistent Beach", quiet_times_enabled=True) is False
        assert is_quiet_hours("", quiet_times_enabled=True) is False
        assert is_quiet_hours(None, quiet_times_enabled=True) is False

    @freeze_time("2026-01-15 10:00:00")  # 12:00 Israel
    def test_quiet_hours_custom_window_same_day(self, mock_location_timezones):
        """Custom daytime window: start=9, end=17. 12:00 is inside; 18:00 is outside."""
        # 12:00 local is inside 9..17
        assert is_quiet_hours(self.LOCATION, quiet_times_enabled=True, quiet_start_hour=9, quiet_end_hour=17) is True

        # At 16:00 UTC = 18:00 Israel -> outside 9..17
        with freeze_time("2026-01-15 16:00:00"):
            assert is_quiet_hours(self.LOCATION, quiet_times_enabled=True, quiet_start_hour=9, quiet_end_hour=17) is False

    # --- Off Hours Tests ---

    @freeze_time("2026-01-15 00:00:00")  # 00:00 UTC = 02:00 Israel (winter UTC+2)
    def test_off_hours_overnight_window(self, mock_location_timezones):
        """start 22:00, end 06:00, now 02:00 local -> True."""
        assert is_off_hours(
            user_location=self.LOCATION,
            off_time_start=time(22, 0),
            off_time_end=time(6, 0),
            off_times_enabled=True,
        ) is True

    def test_off_hours_same_day_window(self, mock_location_timezones):
        """start 13:00, end 15:00. At 14:00 local -> True; at 16:00 local -> False."""
        # 12:00 UTC = 14:00 Israel -> inside 13:00..15:00
        with freeze_time("2026-01-15 12:00:00"):
            assert is_off_hours(
                user_location=self.LOCATION,
                off_time_start=time(13, 0),
                off_time_end=time(15, 0),
                off_times_enabled=True,
            ) is True

        # 14:00 UTC = 16:00 Israel -> outside 13:00..15:00
        with freeze_time("2026-01-15 14:00:00"):
            assert is_off_hours(
                user_location=self.LOCATION,
                off_time_start=time(13, 0),
                off_time_end=time(15, 0),
                off_times_enabled=True,
            ) is False

    def test_off_hours_disabled_or_missing_times_false(self, mock_location_timezones):
        """off_times_enabled=False or missing start/end times returns False."""
        assert is_off_hours(self.LOCATION, time(22, 0), time(6, 0), off_times_enabled=False) is False
        assert is_off_hours(self.LOCATION, None, time(6, 0), off_times_enabled=True) is False
        assert is_off_hours(self.LOCATION, time(22, 0), None, off_times_enabled=True) is False
        assert is_off_hours(None, time(22, 0), time(6, 0), off_times_enabled=True) is False

    @freeze_time("2026-01-15 12:00:00")  # 12:00 UTC
    def test_off_hours_uses_location_timezone_not_server(self, mock_location_timezones):
        """Same UTC instant:
        - In Israel (UTC+2), local time is 14:00 (inside 13:00-15:00 window -> True)
        - In Honolulu (UTC-10), local time is 02:00 (outside 13:00-15:00 window -> False)
        """
        israel_off = is_off_hours(
            user_location="Hilton Beach (Tel Aviv)",
            off_time_start=time(13, 0),
            off_time_end=time(15, 0),
            off_times_enabled=True,
        )
        honolulu_off = is_off_hours(
            user_location="Waikiki Beach (Honolulu)",
            off_time_start=time(13, 0),
            off_time_end=time(15, 0),
            off_times_enabled=True,
        )
        assert israel_off is True
        assert honolulu_off is False

    # --- Timezone Offset Tests ---

    def test_tz_offset_summer_vs_winter(self, mock_location_timezones):
        """Israel: UTC+3 in July (IDT summer), UTC+2 in January (IST winter)."""
        with freeze_time("2026-07-15 12:00:00"):
            assert get_current_tz_offset(self.LOCATION) == 3

        with freeze_time("2026-01-15 12:00:00"):
            assert get_current_tz_offset(self.LOCATION) == 2

    def test_tz_offset_unknown_location_defaults_to_2(self, mock_location_timezones):
        """Unknown or empty location safely defaults to 2 (UTC+2)."""
        assert get_current_tz_offset("Nonexistent Spot") == 2
        assert get_current_tz_offset("") == 2
        assert get_current_tz_offset(None) == 2
