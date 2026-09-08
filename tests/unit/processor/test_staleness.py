"""
Unit tests for background_processor.is_data_identical

This comparison drives the consecutive_identical_updates counter, which in
turn sets the stale_data_warning bit every lamp receives. Too strict and
lamps show a false "stale" after tiny float jitter; too loose and a frozen
upstream API goes unnoticed.
"""

import pytest

from background_processor import is_data_identical

BASE = {"wave_height_m": 1.2, "wave_period_s": 8.0, "wind_speed_mps": 5.0, "wind_direction_deg": 180}


@pytest.mark.unit
class TestIsDataIdentical:
    def test_identical_dicts(self):
        assert is_data_identical(BASE, dict(BASE)) is True

    def test_identical_within_float_tolerance(self):
        new = dict(BASE, wave_height_m=1.2004, wind_speed_mps=5.0009)
        assert is_data_identical(BASE, new) is True

    def test_difference_above_tolerance_not_identical(self):
        assert is_data_identical(BASE, dict(BASE, wave_height_m=1.202)) is False
        assert is_data_identical(BASE, dict(BASE, wind_direction_deg=181)) is False

    def test_missing_old_data_not_identical(self):
        """First run for a location: nothing to compare against."""
        assert is_data_identical(None, BASE) is False
        assert is_data_identical({}, BASE) is False

    def test_both_none_field_counts_as_match(self):
        old = dict(BASE, wind_direction_deg=None)
        new = dict(BASE, wind_direction_deg=None)
        assert is_data_identical(old, new) is True

    def test_one_side_none_not_identical(self):
        assert is_data_identical(dict(BASE, wind_speed_mps=None), BASE) is False
        assert is_data_identical(BASE, dict(BASE, wind_speed_mps=None)) is False

    def test_missing_key_treated_as_none(self):
        new = dict(BASE)
        del new["wave_period_s"]
        assert is_data_identical(BASE, new) is False

    def test_extra_keys_ignored(self):
        new = dict(BASE, timestamp=123, source_endpoint="x")
        assert is_data_identical(BASE, new) is True

    def test_string_numbers_compared_numerically(self):
        """DB rows can come back as Decimal/str; comparison is on float value."""
        new = {k: str(v) for k, v in BASE.items()}
        assert is_data_identical(BASE, new) is True

    def test_non_numeric_not_identical(self):
        assert is_data_identical(BASE, dict(BASE, wave_height_m="n/a")) is False
