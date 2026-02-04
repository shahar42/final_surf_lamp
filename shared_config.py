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
# TIMEZONE SETTINGS (enforce UTC everywhere for consistency)
# ============================================================================

# Always use UTC for database timestamps and comparisons
USE_UTC_TIMEZONE = True

# ============================================================================
# APP CONSTANTS (Shared between web app and processor)
# ============================================================================

SURF_LOCATIONS = [
    "Hadera, Israel",
    "Tel Aviv, Israel", 
    "Ashdod, Israel",
    "Haifa, Israel",
    "Netanya, Israel",
    "Ashkelon, Israel",
    "Nahariya, Israel"
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

# Multi-source location configuration with priority-based fallback
# Each location has a list of API sources with:
# - url: API endpoint
# - priority: Lower number = higher priority (try first)
# - type: 'wave' or 'wind'
MULTI_SOURCE_LOCATIONS = {
    "Tel Aviv, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"}
    ],
    "Hadera, Israel": [
        {"url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json", "priority": 1, "type": "wave"},
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.4500&longitude=34.9100&hourly=wave_height,wave_period,wave_direction", "priority": 2, "type": "wave"}
    ],
    "Ashdod, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.7939&longitude=34.6328&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"}
    ],
    "Haifa, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.7940&longitude=34.9896&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"}
    ],
    "Netanya, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.3215&longitude=34.8532&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"}
    ],
    "Nahariya, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=33.006&longitude=35.094&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"}
    ],
    "Ashkelon, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.6699&longitude=34.5738&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"}
    ],
    "Eilat, Israel": [
        {"url": "https://api.open-meteo.com/v1/forecast?latitude=29.5500&longitude=34.9519&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms", "priority": 1, "type": "wind"}
    ]
}

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
