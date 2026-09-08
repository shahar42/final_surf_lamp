"""
Unit tests for web_and_database/utils/threshold_logic.py

Tests the server-side shim for range alerts.
Arduino firmware has: if (current >= threshold) blink()
Server manipulates threshold so:
- current < min: threshold = min (does not blink)
- min <= current <= max: threshold = min (blinks)
- current > max: threshold = 9999 sentinel (does not blink)
"""

import pytest
from utils.threshold_logic import (
    IMPOSSIBLE_THRESHOLD,
    calculate_effective_threshold,
    validate_threshold_range,
)


@pytest.mark.unit
class TestThresholdLogic:
    def test_below_min_returns_min(self):
        """current < min -> threshold == min (lamp does not blink)."""
        result = calculate_effective_threshold(current_value=0.5, user_min=1.0, user_max=3.0)
        assert result == 1.0

    def test_inside_range_returns_min(self):
        """min <= current <= max -> threshold == min (lamp blinks)."""
        result = calculate_effective_threshold(current_value=2.0, user_min=1.0, user_max=3.0)
        assert result == 1.0

    def test_above_max_returns_impossible(self):
        """current > max -> threshold == 9999 sentinel (lamp does not blink)."""
        result = calculate_effective_threshold(current_value=4.0, user_min=1.0, user_max=3.0)
        assert result == IMPOSSIBLE_THRESHOLD
        assert result == 9999

    def test_no_max_behaves_as_simple_threshold(self):
        """user_max None -> threshold == min always."""
        assert calculate_effective_threshold(current_value=0.5, user_min=1.0, user_max=None) == 1.0
        assert calculate_effective_threshold(current_value=1.5, user_min=1.0, user_max=None) == 1.0
        assert calculate_effective_threshold(current_value=5.0, user_min=1.0, user_max=None) == 1.0

    def test_current_none_returns_min(self):
        """no surf data yet (None) -> returns min safely, never crashes."""
        result = calculate_effective_threshold(current_value=None, user_min=1.2, user_max=2.5)
        assert result == 1.2

    def test_boundary_equal_to_max_blinks(self):
        """current == max is inside range -> returns min."""
        result = calculate_effective_threshold(current_value=3.0, user_min=1.0, user_max=3.0)
        assert result == 1.0

    def test_boundary_equal_to_min_blinks(self):
        """current == min is inside range -> returns min."""
        result = calculate_effective_threshold(current_value=1.0, user_min=1.0, user_max=3.0)
        assert result == 1.0

    def test_validate_range_rejects_min_above_max(self):
        """validate_threshold_range rejects min > max."""
        is_valid, msg = validate_threshold_range(min_value=3.0, max_value=1.0)
        assert is_valid is False
        assert msg == "Minimum threshold must be less than or equal to maximum threshold"

    def test_validate_range_accepts_equal_min_max(self):
        """validate_threshold_range accepts min == max."""
        is_valid, msg = validate_threshold_range(min_value=2.0, max_value=2.0)
        assert is_valid is True
        assert msg is None

    def test_validate_range_rejects_negative(self):
        """validate_threshold_range rejects negative values."""
        is_valid, msg = validate_threshold_range(min_value=-1.0, max_value=2.0)
        assert is_valid is False
        assert msg == "Threshold values must be non-negative"

        is_valid, msg = validate_threshold_range(min_value=1.0, max_value=-0.5)
        assert is_valid is False
        assert msg == "Threshold values must be non-negative"

        # Valid range with None max
        is_valid, msg = validate_threshold_range(min_value=1.0, max_value=None)
        assert is_valid is True
        assert msg is None
