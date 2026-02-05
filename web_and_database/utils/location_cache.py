"""
Location-based binary data cache for V3 protocol.
Eliminates duplicate encoding for lamps in same location.

Architecture:
- Cache key: location name
- Cache value: pre-packed surf data (no user-specific fields)
- TTL: 60 seconds (aligns with API refresh)
- Merge with user settings on retrieval
"""

from redis_manager import get_redis_client
from typing import Tuple, Optional, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)

def get_cached_location_binary(
    location_name: str,
    location_obj,
    effective_wave_threshold_m: float,
    effective_wind_threshold_knots: float,
    quiet_hours: bool,
    off_hours: bool
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Get cached surf data for a location, or build and cache it.

    Returns: (surf_data_dict, cache_hit: bool)

    Cache strategy:
    - Key: location:surf:v3:{location_name}
    - TTL: 60 seconds (surf data updates every ~15min, but keep fresh)
    - Stores: JSON dict of surf data (without user-specific settings)
    """
    redis = get_redis_client()
    cache_key = f"location:surf:v3:{location_name}"

    if redis:
        try:
            cached = redis.get(cache_key)
            if cached:
                surf_data = json.loads(cached)
                logger.debug(f"🎯 Location cache HIT for {location_name}")
                return surf_data, True
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

    # Cache miss - build surf data
    from config import STALE_DATA_THRESHOLD
    surf_data = {
        'wave_period_s': int(location_obj.wave_period_s or 0),
        'wave_height_cm': int(round((location_obj.wave_height_m or 0) * 100)),
        'wave_threshold_cm': int(effective_wave_threshold_m * 100),
        'wind_speed_mps': int(round(location_obj.wind_speed_mps or 0)),
        'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
        'wind_direction_deg': location_obj.wind_direction_deg or 0,
        'stale_data_warning': (getattr(location_obj, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD,
        'data_available': bool(location_obj.wave_height_m or location_obj.wind_speed_mps),
        'quiet_hours_active': quiet_hours,
        'off_hours_active': off_hours
    }

    # Cache it
    if redis:
        try:
            redis.setex(cache_key, 60, json.dumps(surf_data))
            logger.debug(f"📦 Cached surf data for {location_name}")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    return surf_data, False


def get_location_stats():
    """Get cache hit rate statistics for monitoring"""
    redis = get_redis_client()
    if not redis:
        return None

    try:
        # Count cached locations
        keys = redis.keys("location:surf:v3:*")
        return {
            'cached_locations': len(keys),
            'locations': [k.decode().replace('location:surf:v3:', '') for k in keys]
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return None
