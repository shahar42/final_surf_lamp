"""
Threshold Logic Module for Range Alert Feature

This module provides server-side logic to simulate range-based alerts (e.g., "alert only
if waves are between 1m-3m") without modifying Arduino firmware.

Strategy: The Arduino has fixed logic: `if (current >= threshold) blink()`
We dynamically manipulate the threshold value sent to the Arduino based on user's [min, max] range.

Logic:
- If current < min: Send threshold = min → Arduino: current >= min = FALSE → No blink
- If min <= current <= max: Send threshold = min → Arduino: current >= min = TRUE → Blinks
- If current > max: Send threshold = 9999 → Arduino: current >= 9999 = FALSE → No blink
"""

import logging

logger = logging.getLogger(__name__)

# Constants
IMPOSSIBLE_THRESHOLD = 9999  # Threshold value that will never be reached (for disabling alerts)


def calculate_effective_threshold(current_value, user_min, user_max=None):
    """
    Calculates the threshold to send to the Arduino to simulate a range check.

    This function implements a "server-side shim" that allows range-based alerts
    without changing Arduino firmware. The Arduino's fixed logic is:
    `if (current >= threshold) blink()`. We manipulate `threshold` to achieve
    range behavior.

    Args:
        current_value (float or None): Current surf condition value (wave height, wind speed).
                                       Can be None if API fetch failed.
        user_min (float): Minimum threshold set by user (lower bound of range).
        user_max (float or None): Maximum threshold set by user (upper bound of range).
                                  If None, behaves like traditional threshold (backwards compatible).

    Returns:
        float: The effective threshold to send to Arduino.

    Examples:
        # Traditional mode (no max set)
        >>> calculate_effective_threshold(2.5, 1.0, None)
        1.0

        # Range mode: current is within range [1, 3]
        >>> calculate_effective_threshold(2.0, 1.0, 3.0)
        1.0  # Arduino will blink (2.0 >= 1.0)

        # Range mode: current is below min
        >>> calculate_effective_threshold(0.5, 1.0, 3.0)
        1.0  # Arduino won't blink (0.5 < 1.0)

        # Range mode: current is above max
        >>> calculate_effective_threshold(4.0, 1.0, 3.0)
        9999  # Arduino won't blink (4.0 < 9999)

        # Edge case: current is None (API failure)
        >>> calculate_effective_threshold(None, 1.0, 3.0)
        1.0  # Fail safely to traditional behavior
    """

    # Handle API failure case - fail safely to traditional threshold behavior
    if current_value is None:
        logger.warning("Current value is None (API failure), using traditional threshold")
        return user_min

    # Backwards compatible mode: no max threshold set
    if user_max is None:
        return user_min

    # Range mode: if current exceeds max, make threshold impossible to reach
    if current_value > user_max:
        logger.debug(f"Current {current_value} > max {user_max}, disabling alert")
        return IMPOSSIBLE_THRESHOLD

    # Range mode: current is <= max, use min as threshold
    # This handles both:
    # - current < min: Arduino sees (current < min) = FALSE → no blink
    # - min <= current <= max: Arduino sees (current >= min) = TRUE → blinks
    return user_min


def validate_threshold_range(min_value, max_value):
    """
    Validates user-provided threshold range.

    Args:
        min_value (float): Minimum threshold value.
        max_value (float or None): Maximum threshold value. Can be None.

    Returns:
        tuple: (is_valid: bool, error_message: str or None)

    Examples:
        >>> validate_threshold_range(1.0, 3.0)
        (True, None)

        >>> validate_threshold_range(3.0, 1.0)
        (False, "Minimum threshold must be less than or equal to maximum threshold")

        >>> validate_threshold_range(1.0, None)
        (True, None)

        >>> validate_threshold_range(-1.0, 3.0)
        (False, "Threshold values must be non-negative")
    """

    # Validate non-negative values
    if min_value < 0:
        return False, "Threshold values must be non-negative"

    if max_value is not None and max_value < 0:
        return False, "Threshold values must be non-negative"

    # Validate min <= max when max is set
    if max_value is not None and min_value > max_value:
        return False, "Minimum threshold must be less than or equal to maximum threshold"

    return True, None
