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

# Key version bumped v3 -> v4 when user-specific fields were removed from the
# cached blob, so a deploy never reads an old blob carrying another user's settings.
CACHE_KEY_PREFIX = "location:surf:v4:"
CACHE_TTL_SECONDS = 60


def _build_location_conditions(location_obj) -> Dict[str, Any]:
    """Location-only fields. Safe to share between every lamp at this beach."""
    from config import STALE_DATA_THRESHOLD
    return {
        'wave_period_s': int(location_obj.wave_period_s or 0),
        'wave_height_cm': int(round((location_obj.wave_height_m or 0) * 100)),
        'wind_speed_mps': int(round(location_obj.wind_speed_mps or 0)),
        'wind_direction_deg': location_obj.wind_direction_deg or 0,
        'stale_data_warning': (getattr(location_obj, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD,
        'data_available': bool(location_obj.wave_height_m or location_obj.wind_speed_mps),
    }


def get_cached_location_binary(
    location_name: str,
    location_obj,
    effective_wave_threshold_m: float,
    effective_wind_threshold_knots: float,
    quiet_hours: bool,
    off_hours: bool
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Get surf data for one lamp: shared location conditions (cached per beach)
    merged with this lamp owner's thresholds and quiet/off-hours flags.

    Returns: (surf_data_dict, cache_hit: bool)

    Cache strategy:
    - Key: location:surf:v4:{location_name}
    - TTL: 60 seconds (surf data updates every ~15min, but keep fresh)
    - Stores: ONLY location conditions. Thresholds and hours flags are
      per-user and are merged in after the cache read, never stored.
      Storing them would hand one owner's settings to every other lamp
      at the same beach.
    """
    redis = get_redis_client()
    cache_key = f"{CACHE_KEY_PREFIX}{location_name}"

    conditions = None
    cache_hit = False

    if redis:
        try:
            cached = redis.get(cache_key)
            if cached:
                conditions = json.loads(cached)
                cache_hit = True
                logger.debug(f"🎯 Location cache HIT for {location_name}")
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

    if conditions is None:
        conditions = _build_location_conditions(location_obj)
        if redis:
            try:
                redis.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(conditions))
                logger.debug(f"📦 Cached surf data for {location_name}")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

    # Per-user fields: merged on every call, never cached.
    surf_data = dict(conditions)
    surf_data['wave_threshold_cm'] = int(effective_wave_threshold_m * 100)
    surf_data['wind_speed_threshold_knots'] = int(round(effective_wind_threshold_knots))
    surf_data['quiet_hours_active'] = quiet_hours
    surf_data['off_hours_active'] = off_hours

    return surf_data, cache_hit


def get_location_stats():
    """Get cache hit rate statistics for monitoring"""
    redis = get_redis_client()
    if not redis:
        return None

    try:
        # Count cached locations
        keys = redis.keys(f"{CACHE_KEY_PREFIX}*")
        return {
            'cached_locations': len(keys),
            'locations': [k.replace(CACHE_KEY_PREFIX, '') for k in keys]
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return None


# ============================================================================
# DATABASE QUERY CACHE (separate from binary protocol cache above)
# ============================================================================

import time

# In-memory cache for Location database objects: {location_name: (location_obj, timestamp)}
_db_location_cache = {}
DB_CACHE_TTL_SECONDS = 300  # 5 minutes (processor updates every 15 min)

def get_location_from_db_cached(db, location_name):
    """
    Get Location object from cache or database.

    Optimization: Location surf data only updates every 15 minutes via background
    processor, but we query it on EVERY API call. Caching for 5 minutes eliminates
    ~67% of redundant database queries.

    Performance Impact:
    - Before: Every request queries database (~5-10ms per query)
    - After: Cache hit returns in ~0.1ms
    - At 1000 requests/day: Saves ~5-10 seconds of DB time

    Args:
        db: SQLAlchemy session
        location_name: Location name (e.g., "tel-aviv")

    Returns:
        Location object or None if not found
    """
    now = time.time()

    # Check cache first
    if location_name in _db_location_cache:
        cached_obj, timestamp = _db_location_cache[location_name]
        age = now - timestamp

        if age < DB_CACHE_TTL_SECONDS:
            logger.debug(f"✅ DB cache HIT for {location_name} (age: {age:.1f}s)")
            return cached_obj

        logger.debug(f"⏰ DB cache STALE for {location_name} (age: {age:.1f}s)")

    # Cache miss or stale - fetch from database
    from data_base import Location

    location_obj = db.query(Location).filter(Location.location == location_name).first()

    # Update cache
    if location_obj:
        _db_location_cache[location_name] = (location_obj, now)
        logger.debug(f"💾 DB cache UPDATED for {location_name}")
    else:
        logger.warning(f"⚠️  Location {location_name} not found in database")

    return location_obj

def invalidate_db_location_cache(location_name=None):
    """
    Manually invalidate database cache for a location or all locations.

    Call this after updating location data in background processor to ensure
    fresh data is served immediately.

    Args:
        location_name: Specific location to invalidate, or None for all
    """
    if location_name:
        if location_name in _db_location_cache:
            del _db_location_cache[location_name]
            logger.info(f"🗑️  DB cache invalidated for {location_name}")
    else:
        _db_location_cache.clear()
        logger.info(f"🗑️  All DB location cache cleared ({len(_db_location_cache)} entries)")

def get_db_cache_stats():
    """
    Get database cache statistics for monitoring.

    Returns:
        dict with cache size, hit rate, oldest entry age, etc.
    """
    now = time.time()
    stats = {
        'size': len(_db_location_cache),
        'locations': list(_db_location_cache.keys()),
        'ttl_seconds': DB_CACHE_TTL_SECONDS
    }

    if _db_location_cache:
        ages = [(loc, now - ts) for loc, (_, ts) in _db_location_cache.items()]
        oldest = max(ages, key=lambda x: x[1])
        stats['oldest_entry'] = {
            'location': oldest[0],
            'age_seconds': round(oldest[1], 1)
        }

    return stats
