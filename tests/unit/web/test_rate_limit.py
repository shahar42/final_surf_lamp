"""
Unit tests for web_and_database/utils/rate_limit.py

Location-change rate limiting: 10 changes per rolling day, per user.
"""

import pytest
from freezegun import freeze_time

from utils import rate_limit


@pytest.fixture(autouse=True)
def reset_location_changes():
    rate_limit.location_changes.clear()
    yield
    rate_limit.location_changes.clear()


@pytest.mark.unit
class TestRateLimit:
    def test_ten_changes_allowed_eleventh_blocked(self):
        user_id = 1
        for _ in range(10):
            assert rate_limit.check_location_change_limit(user_id) is True
            rate_limit.record_location_change(user_id)

        assert rate_limit.check_location_change_limit(user_id) is False

    def test_counter_resets_at_utc_midnight(self):
        """The limiter keys the day on UTC midnight (not the user's local midnight)."""
        user_id = 2
        with freeze_time("2026-01-15 23:00:00"):
            for _ in range(10):
                assert rate_limit.check_location_change_limit(user_id) is True
                rate_limit.record_location_change(user_id)
            assert rate_limit.check_location_change_limit(user_id) is False

        with freeze_time("2026-01-16 00:30:00"):
            assert rate_limit.check_location_change_limit(user_id) is True

    def test_users_are_independent(self):
        for _ in range(10):
            rate_limit.record_location_change(1)

        assert rate_limit.check_location_change_limit(1) is False
        assert rate_limit.check_location_change_limit(2) is True
