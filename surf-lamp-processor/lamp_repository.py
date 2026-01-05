"""
Lamp Repository (Refactored for Location-Centric Architecture)
Database access layer for surf lamp operations.

NEW ARCHITECTURE:
- Location-centric: One API call per location updates locations table
- All arduinos at that location inherit the data
- Arduino table tracks polling activity only

Responsibilities:
- All SQL queries and database operations
- Connection management and transactions
- Batch operations for performance
- Configuration loading from database

Dependencies: sqlalchemy, data_base module
"""

import os
import sys
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def test_database_connection(engine):
    """Test database connection and show table info"""
    logger.info("🔍 Testing database connection...")

    try:
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")

            # Check tables exist (NEW SCHEMA)
            ALLOWED_TABLES = {'users', 'arduinos', 'locations', 'password_reset_tokens', 'error_reports', 'broadcasts'}
            tables_to_check = ['users', 'arduinos', 'locations']

            for table in tables_to_check:
                # Validate table name against whitelist
                if table not in ALLOWED_TABLES:
                    logger.error(f"❌ Security: Invalid table name '{table}' - not in whitelist")
                    continue

                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    logger.info(f"✅ Table {table}: {count} records")
                except Exception as e:
                    logger.error(f"❌ Table {table} check failed: {e}")

            return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_location_api_configs(engine):
    """
    Get API configurations from locations table.
    Returns: {location: {'wave_api_url': ..., 'wind_api_url': ...}}
    """
    logger.info("📡 Getting location API configurations from database...")

    query = text("""
        SELECT location, wave_api_url, wind_api_url
        FROM locations
        WHERE location IN (
            SELECT DISTINCT location FROM arduinos
        )
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            configs = {}
            for row in result:
                configs[row.location] = {
                    'wave_api_url': row.wave_api_url,
                    'wind_api_url': row.wind_api_url
                }
                logger.info(f"✅ {row.location}: wave={row.wave_api_url[:50]}..., wind={row.wind_api_url[:50]}...")

        logger.info(f"✅ Loaded API configs for {len(configs)} locations")
        return configs

    except Exception as e:
        logger.error(f"❌ Failed to get location API configs: {e}")
        return {}


def get_arduinos_for_location(engine, location):
    """
    Get all arduinos in a specific location.
    Returns: [{'arduino_id': 4433, 'user_id': 6, 'location': 'Hadera, Israel'}, ...]
    """
    logger.info(f"🔍 Getting arduinos for location: {location}")

    query = text("""
        SELECT arduino_id, user_id, location, last_poll_time
        FROM arduinos
        WHERE location = :location
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"location": location})
            arduinos = [dict(row._mapping) for row in result]

        logger.info(f"✅ Found {len(arduinos)} arduinos in {location}:")
        for arduino in arduinos:
            logger.info(f"   - Arduino {arduino['arduino_id']} (User {arduino['user_id']})")

        return arduinos

    except Exception as e:
        logger.error(f"❌ Failed to get arduinos for location: {e}")
        return []


def update_location_conditions(engine, location, surf_data):
    """
    Update locations table with latest surf data (ONCE per location).
    All arduinos at this location inherit this data.

    Args:
        location: Location name (e.g., "Hadera, Israel")
        surf_data: Dict with wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg

    Returns:
        bool: True if successful
    """
    logger.info(f"🌊 Updating conditions for location: {location}")

    query = text("""
        UPDATE locations
        SET
            wave_height_m = :wave_height,
            wave_period_s = :wave_period,
            wind_speed_mps = :wind_speed,
            wind_direction_deg = :wind_direction,
            last_updated = CURRENT_TIMESTAMP
        WHERE location = :location
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {
                "location": location,
                "wave_height": surf_data.get('wave_height_m', 0.0),
                "wave_period": surf_data.get('wave_period_s', 0.0),
                "wind_speed": surf_data.get('wind_speed_mps', 0.0),
                "wind_direction": surf_data.get('wind_direction_deg', 0)
            })
            conn.commit()

        logger.info(f"✅ Location conditions updated: {location} (wave={surf_data.get('wave_height_m')}m, wind={surf_data.get('wind_speed_mps')}m/s)")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update location conditions for {location}: {e}")
        return False


def batch_update_arduino_timestamps(engine, arduino_ids):
    """
    Update last_poll_time for multiple arduinos in a single transaction.

    Args:
        arduino_ids: List of arduino IDs to update

    Returns:
        bool: True if successful
    """
    if not arduino_ids:
        return True

    logger.info(f"⏰ Batch updating timestamps for {len(arduino_ids)} arduinos")

    query = text("""
        UPDATE arduinos
        SET last_poll_time = CURRENT_TIMESTAMP
        WHERE arduino_id = ANY(:arduino_ids)
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {"arduino_ids": arduino_ids})
            conn.commit()

        logger.info(f"✅ Timestamps batch updated for {len(arduino_ids)} arduinos")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to batch update arduino timestamps: {e}")
        return False


def get_user_threshold_for_arduino(engine, arduino_id):
    """
    Get user's wave threshold for this Arduino.
    (Kept for backward compatibility - thresholds are per-user, not per-arduino)
    """
    query = text("""
        SELECT u.wave_threshold_m
        FROM users u
        JOIN arduinos a ON u.user_id = a.user_id
        WHERE a.arduino_id = :arduino_id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"arduino_id": arduino_id})
            row = result.fetchone()
            return row[0] if row and row[0] else 1.0
    except Exception as e:
        logger.error(f"Failed to get threshold for Arduino {arduino_id}: {e}")
        return 1.0  # Safe default


def get_user_wind_threshold_for_arduino(engine, arduino_id):
    """
    Get user's wind threshold for this Arduino.
    (Kept for backward compatibility - thresholds are per-user, not per-arduino)
    """
    query = text("""
        SELECT u.wind_threshold_knots
        FROM users u
        JOIN arduinos a ON u.user_id = a.user_id
        WHERE a.arduino_id = :arduino_id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"arduino_id": arduino_id})
            row = result.fetchone()
            return row[0] if row and row[0] else 22.0
    except Exception as e:
        logger.error(f"Failed to get wind threshold for Arduino {arduino_id}: {e}")
        return 22.0  # Safe default
