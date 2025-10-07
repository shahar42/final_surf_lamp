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
PROCESSOR_UPDATE_INTERVAL_SECONDS = 3600  # 1 hour

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
"""
