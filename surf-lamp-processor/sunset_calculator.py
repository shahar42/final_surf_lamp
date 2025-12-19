"""
Sunset/Sunrise calculation for Surf Lamp animation triggers
Uses astral library for accurate astronomical calculations
"""
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
import logging

logger = logging.getLogger(__name__)

# Location coordinates for surf spots (add more as needed)
LOCATION_COORDS = {
    "Tel Aviv": {"latitude": 32.0853, "longitude": 34.7818, "timezone": "Asia/Jerusalem"},
    "Haifa": {"latitude": 32.7940, "longitude": 34.9896, "timezone": "Asia/Jerusalem"},
    "Eilat": {"latitude": 29.5581, "longitude": 34.9482, "timezone": "Asia/Jerusalem"},
    "Herzliya": {"latitude": 32.1624, "longitude": 34.8080, "timezone": "Asia/Jerusalem"},
    # Add more locations as needed
}

def get_sunset_info(location_name: str, trigger_window_minutes: int = 15) -> dict:
    """
    Calculate sunset information for a given location.

    Args:
        location_name: Name of surf location (e.g., "Tel Aviv")
        trigger_window_minutes: Minutes before/after sunset to trigger animation (default: 15)

    Returns:
        dict with keys:
            - sunset_trigger (bool): True if currently in sunset window
            - day_of_year (int): Day of year (1-365/366)
            - sunset_time (str): Sunset time in HH:MM format
            - in_window (bool): Whether currently in trigger window
    """
    try:
        # Get location coordinates
        if location_name not in LOCATION_COORDS:
            logger.warning(f"Location '{location_name}' not in LOCATION_COORDS, using Tel Aviv as default")
            location_name = "Tel Aviv"

        coords = LOCATION_COORDS[location_name]

        # Create location object
        location = LocationInfo(
            name=location_name,
            region="Israel",
            timezone=coords["timezone"],
            latitude=coords["latitude"],
            longitude=coords["longitude"]
        )

        # Calculate today's sunset
        now = datetime.now()
        s = sun(location.observer, date=now.date(), tzinfo=location.timezone)
        sunset_time = s["sunset"]

        # Calculate trigger window (±15 minutes around sunset)
        window_start = sunset_time - timedelta(minutes=trigger_window_minutes)
        window_end = sunset_time + timedelta(minutes=trigger_window_minutes)

        # Check if current time is in window
        in_window = window_start <= now.astimezone() <= window_end

        return {
            "sunset_trigger": in_window,
            "day_of_year": now.timetuple().tm_yday,
            "sunset_time": sunset_time.strftime("%H:%M"),
            "in_window": in_window
        }

    except Exception as e:
        logger.error(f"Error calculating sunset for {location_name}: {e}")
        # Fallback: no trigger
        return {
            "sunset_trigger": False,
            "day_of_year": datetime.now().timetuple().tm_yday,
            "sunset_time": "Unknown",
            "in_window": False
        }

def add_location_coords(location_name: str, latitude: float, longitude: float, timezone: str = "Asia/Jerusalem"):
    """
    Add new location coordinates for sunset calculation.

    Args:
        location_name: Name of surf location
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        timezone: Timezone string (default: Asia/Jerusalem)
    """
    LOCATION_COORDS[location_name] = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone
    }
    logger.info(f"Added location: {location_name} ({latitude}, {longitude})")

# Example usage:
if __name__ == "__main__":
    # Test sunset calculation
    locations = ["Tel Aviv", "Haifa", "Eilat"]

    for location in locations:
        info = get_sunset_info(location, trigger_window_minutes=15)
        print(f"\n{location}:")
        print(f"  Sunset time: {info['sunset_time']}")
        print(f"  In trigger window: {info['in_window']}")
        print(f"  Animation trigger: {info['sunset_trigger']}")
        print(f"  Day of year: {info['day_of_year']}")
