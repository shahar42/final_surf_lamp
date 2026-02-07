#!/usr/bin/env python3
"""
Shared Configuration for Surf Lamp System
Single source of truth for timing thresholds and business logic constants.

This file prevents business logic duplication across:
- MCP Supabase Server (status determination)
- Background Monitor (update intervals)
- Frontend Dashboard (warning thresholds)
- Background Processor (data refresh logic)
"""

import json
import os
import sys
from pathlib import Path

# ============================================================================
# LAMP STATUS THRESHOLDS (used for determining online/stale/offline status)
# ============================================================================

# How recently data must be updated to consider a lamp "online"
LAMP_ONLINE_THRESHOLD_SECONDS = 3600  # 1 hour
LAMP_ONLINE_THRESHOLD_MINUTES = LAMP_ONLINE_THRESHOLD_SECONDS / 60  # 60 minutes

# How old data can be before considering a lamp "stale" (warning state)
LAMP_STALE_THRESHOLD_SECONDS = 86400  # 24 hours
LAMP_STALE_THRESHOLD_HOURS = LAMP_STALE_THRESHOLD_SECONDS / 3600  # 24 hours

# Anything older than STALE threshold is considered "offline"

# ============================================================================
# MONITORING INTERVALS (how often background services check for updates)
# ============================================================================

# How often the monitor checks lamp health
MONITOR_CHECK_INTERVAL_SECONDS = 3600  # 1 hour (matches LAMP_ONLINE_THRESHOLD)

# How often the background processor fetches new weather data
PROCESSOR_UPDATE_INTERVAL_SECONDS = 900  # 15 minutes

# ============================================================================
# API RATE LIMITING (for location-based weather API calls)
# ============================================================================

# Minimum time between API calls for the same location
MIN_LOCATION_API_CALL_INTERVAL_SECONDS = 600  # 10 minutes

# Redis rate limiting for user actions
USER_ACTION_RATE_LIMIT_SECONDS = 300  # 5 minutes between user preference changes

# ============================================================================
# REDIS FALLBACK CONFIGURATION (for database fallback during Redis outages)
# ============================================================================

# Cooldown period between database writes for same Arduino during Redis outage
DB_FALLBACK_COOLDOWN_SECONDS = 300  # 5 minutes (prevents DB overload)

# Sampling rate during Redis outages (0.1 = 10% of heartbeats written to DB)
DB_FALLBACK_SAMPLING_RATE = 0.1  # Reduces load by 90% during worst-case outages

# Batch size for bulk sync operations (Redis → Database)
REDIS_SYNC_BATCH_SIZE = 1000  # Process 1000 Arduinos per batch to prevent memory issues

# Interval for Redis-to-Database sync task
REDIS_SYNC_INTERVAL_SECONDS = 300  # 5 minutes

# ============================================================================
# TIMEZONE SETTINGS (enforce UTC everywhere for consistency)
# ============================================================================

# Always use UTC for database timestamps and comparisons
USE_UTC_TIMEZONE = True

# ============================================================================
# APP CONSTANTS (Shared between web app and processor)
# ============================================================================

# Beach-based locations (import from beaches module for consistency)
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_and_database'))
    from locations import get_all_beach_names
    SURF_LOCATIONS = get_all_beach_names()
except ImportError:
    # Fallback for environments without web_and_database module
    SURF_LOCATIONS = [
        "Hilton Beach (Tel Aviv)",
        "Bat Galim (Haifa)",
        "Ashdod (Gil Beach)",
        "Sironit Beach (Netanya)",
        "Olga Beach (Hadera)",
        "Ashkelon (Marina)",
        "Sokolov Beach (Nahariya)"
    ]

BRIGHTNESS_LEVELS = {
    'LOW': 0.05,
    'MID': 0.3,
    'HIGH': 1.0
}

# Threshold limits
THRESHOLD_LIMITS = {
    'WAVE_MIN': 0.0,
    'WAVE_MAX': 3.0,
    'WIND_MIN': 1.0,
    'WIND_MAX': 40.0
}

# ============================================================================
# SQL INTERVAL STRINGS (for use in PostgreSQL queries)
# ============================================================================

def get_online_interval_sql() -> str:
    """Return PostgreSQL INTERVAL string for online threshold"""
    return f"INTERVAL '{LAMP_ONLINE_THRESHOLD_SECONDS} seconds'"

def get_stale_interval_sql() -> str:
    """Return PostgreSQL INTERVAL string for stale threshold"""
    return f"INTERVAL '{LAMP_STALE_THRESHOLD_SECONDS} seconds'"

# ============================================================================
# VALIDATION (ensure thresholds make logical sense)
# ============================================================================

assert LAMP_ONLINE_THRESHOLD_SECONDS < LAMP_STALE_THRESHOLD_SECONDS, \
    "Online threshold must be less than stale threshold"

assert MONITOR_CHECK_INTERVAL_SECONDS <= LAMP_ONLINE_THRESHOLD_SECONDS, \
    "Monitor should check at least as often as online threshold"

# ============================================================================
# USAGE EXAMPLES (for documentation purposes)
# ============================================================================

# ============================================================================
# API ENDPOINTS (Multi-source with priority-based fallback)
# ============================================================================

def _load_location_endpoints():
    """
    Load location endpoints from beaches.py (single source of truth).

    Architecture: beaches.py is PRIMARY, JSON is deprecated fallback.
    Performance: Loads once at module import, cached in memory forever.
    Scales to 10,000+ locations with zero query overhead.

    Returns:
        dict: Location endpoints configuration
    """
    # PRIMARY: Generate from beaches.py (single source of truth)
    config = _generate_fallback_multi_source()

    if config:
        print(f"✅ Loaded {len(config)} locations from beaches.py (single source of truth)")
        return config

    # DEPRECATED FALLBACK: JSON file (backward compatibility only)
    json_path = Path(__file__).parent / 'location_endpoints.json'
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                fallback_config = json.load(f)
                print(f"⚠️ beaches.py failed, using JSON fallback ({len(fallback_config)} locations)")
                return fallback_config
        except Exception as e:
            print(f"❌ Both beaches.py and JSON failed: {e}")

    print("❌ No location endpoints available")
    return {}

# ============================================================================
# FALLBACK CONFIGURATION - Single Source of Truth
# ============================================================================
# Fallback configuration dynamically generated from beaches.py (ONE TRUE TELLING)

def _generate_fallback_multi_source():
    """
    Generate fallback configuration from beaches.py (single source of truth).
    Used only if location_endpoints.json fails to load.
    """
    fallback = {}

    # Try to generate beach endpoints dynamically
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_and_database'))
        from locations import get_all_beaches
        from locations.beach_service import get_api_urls_for_beach

        for beach in get_all_beaches():
            name = beach['english_name']
            urls = get_api_urls_for_beach(name)
            if urls:
                wave_url, wind_url = urls
                fallback[name] = [
                    {"url": wave_url, "priority": 1, "type": "wave"},
                    {"url": wind_url, "priority": 2, "type": "wind"}
                ]
    except ImportError:
        pass  # Will use legacy fallback below

    # Legacy city locations (backward compatibility) - hardcoded minimal set
    fallback.update({
        "Tel Aviv, Israel": [
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 2, "type": "wind"}
        ],
        "Hadera, Israel": [
            {"url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json", "priority": 1, "type": "wave"},
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.4500&longitude=34.9100&hourly=wave_height,wave_period,wave_direction", "priority": 2, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=32.4500&longitude=34.9100&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 3, "type": "wind"}
        ],
        "Ashdod, Israel": [
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.7939&longitude=34.6328&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=31.7939&longitude=34.6328&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 2, "type": "wind"}
        ],
        "Haifa, Israel": [
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.7940&longitude=34.9896&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=32.7940&longitude=34.9896&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 2, "type": "wind"}
        ],
        "Netanya, Israel": [
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.3215&longitude=34.8532&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=32.3215&longitude=34.8532&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 2, "type": "wind"}
        ],
        "Nahariya, Israel": [
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=33.006&longitude=35.094&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=33.006&longitude=35.094&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 2, "type": "wind"}
        ],
        "Ashkelon, Israel": [
            {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.6699&longitude=34.5738&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=31.6699&longitude=34.5738&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 2, "type": "wind"}
        ],
        "Eilat, Israel": [
            {"url": "https://api.open-meteo.com/v1/forecast?latitude=29.5500&longitude=34.9519&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 1, "type": "wind"}
        ]
    })

    return fallback

# Generate fallback configuration (only used if location_endpoints.json fails)
_FALLBACK_MULTI_SOURCE_LOCATIONS = _generate_fallback_multi_source()




# Load configuration once at module import (cached forever)
MULTI_SOURCE_LOCATIONS = _load_location_endpoints()

def get_api_sources_for_location(location):
    """
    Get API sources for a location, sorted by priority.

    Args:
        location: Location name (e.g., "Hadera, Israel")

    Returns:
        dict with 'wave' and 'wind' lists, each containing URLs in priority order
    """
    sources = MULTI_SOURCE_LOCATIONS.get(location, [])

    # Group by type and sort by priority
    wave_sources = sorted([s for s in sources if s['type'] == 'wave'], key=lambda x: x['priority'])
    wind_sources = sorted([s for s in sources if s['type'] == 'wind'], key=lambda x: x['priority'])

    return {
        'wave': [s['url'] for s in wave_sources],
        'wind': [s['url'] for s in wind_sources]
    }

def get_wave_calculation_method(location):
    """
    Determine if location uses formula or API for wave calculation.

    Args:
        location: Location name

    Returns:
        'formula' if location has no wave sources, 'api' otherwise
    """
    sources = MULTI_SOURCE_LOCATIONS.get(location, [])
    has_wave_api = any(s['type'] == 'wave' for s in sources)
    return 'api' if has_wave_api else 'formula'

"""
Example 1: Use in MCP Server SQL query
----------------------------------------
from shared_config import get_online_interval_sql, get_stale_interval_sql

query = f'''
    CASE
        WHEN cc.last_updated > NOW() - {get_online_interval_sql()} THEN 'online'
        WHEN cc.last_updated > NOW() - {get_stale_interval_sql()} THEN 'stale'
        ELSE 'offline'
    END as status
'''

Example 2: Use in Monitor sleep interval
-----------------------------------------
from shared_config import MONITOR_CHECK_INTERVAL_SECONDS

await asyncio.sleep(MONITOR_CHECK_INTERVAL_SECONDS)

Example 3: Use in Python datetime comparisons
----------------------------------------------
from shared_config import LAMP_ONLINE_THRESHOLD_SECONDS
from datetime import datetime, timedelta, timezone

cutoff = datetime.now(timezone.utc) - timedelta(seconds=LAMP_ONLINE_THRESHOLD_SECONDS)
is_online = lamp.last_updated > cutoff

Example 4: Get API sources with fallback
-----------------------------------------
from shared_config import get_api_sources_for_location

sources = get_api_sources_for_location("Hadera, Israel")
# sources = {
#     'wave': ['https://isramar...', 'https://marine-api...'],
#     'wind': ['http://api.openweathermap...']
# }
"""
