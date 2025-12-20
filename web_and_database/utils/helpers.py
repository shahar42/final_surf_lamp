import pytz
from datetime import datetime
import logging
from data_base import LOCATION_TIMEZONES

logger = logging.getLogger(__name__)

def get_current_tz_offset(user_location):
    """
    Get current UTC offset in hours for user's location.
    Automatically handles DST transitions.

    Args:
        user_location: User's location string (e.g., "Tel Aviv, Israel")

    Returns:
        int: UTC offset in hours (e.g., 2 for IST winter, 3 for IDT summer)
    """
    if not user_location or user_location not in LOCATION_TIMEZONES:
        logger.warning(f"Location '{user_location}' not in LOCATION_TIMEZONES, defaulting to UTC+2")
        return 2

    try:
        timezone_str = LOCATION_TIMEZONES[user_location]
        local_tz = pytz.timezone(timezone_str)
        now = datetime.now(local_tz)
        offset_seconds = now.utcoffset().total_seconds()
        offset_hours = int(offset_seconds / 3600)
        return offset_hours
    except Exception as e:
        logger.warning(f"Error calculating tz_offset for {user_location}: {e}")
        return 2

def is_quiet_hours(user_location, quiet_start_hour=22, quiet_end_hour=6):
    """
    Check if current time in user's location is within quiet hours (sleep time).

    Args:
        user_location: User's location string (e.g., "Tel Aviv, Israel")
        quiet_start_hour: Hour when quiet period starts (22 = 10 PM)
        quiet_end_hour: Hour when quiet period ends (6 = 6 AM)

    Returns:
        bool: True if within quiet hours, False otherwise
    """
    if not user_location or user_location not in LOCATION_TIMEZONES:
        return False  # Default to no quiet hours if location unknown

    try:
        timezone_str = LOCATION_TIMEZONES[user_location]
        local_tz = pytz.timezone(timezone_str)
        current_time = datetime.now(local_tz)
        current_hour = current_time.hour

        # Handle overnight quiet hours (e.g., 22:00 to 06:00)
        if quiet_start_hour > quiet_end_hour:
            return current_hour >= quiet_start_hour or current_hour < quiet_end_hour
        else:
            return quiet_start_hour <= current_hour < quiet_end_hour

    except Exception as e:
        logger.warning(f"Error checking quiet hours for {user_location}: {e}")
        return False  # Default to no quiet hours on error

def is_off_hours(user_location, off_time_start, off_time_end, off_times_enabled):
    """
    Check if current time in user's location is within user-defined off hours.

    Args:
        user_location: User's location string (e.g., "Tel Aviv, Israel")
        off_time_start: datetime.time object for off period start
        off_time_end: datetime.time object for off period end
        off_times_enabled: bool indicating if off-times feature is enabled

    Returns:
        bool: True if within off hours, False otherwise
    """
    if not off_times_enabled or not off_time_start or not off_time_end:
        return False

    if not user_location or user_location not in LOCATION_TIMEZONES:
        return False

    try:
        timezone_str = LOCATION_TIMEZONES[user_location]
        local_tz = pytz.timezone(timezone_str)
        current_time = datetime.now(local_tz).time()

        # Handle overnight off hours (e.g., 22:00 to 06:00)
        if off_time_start > off_time_end:
            return current_time >= off_time_start or current_time < off_time_end
        else:
            return off_time_start <= current_time < off_time_end

    except Exception as e:
        logger.warning(f"Error checking off hours for {user_location}: {e}")
        return False

def convert_wind_direction(degrees):
    """Convert wind direction from degrees to compass direction"""
    if degrees is None:
        return "--"
    
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]
