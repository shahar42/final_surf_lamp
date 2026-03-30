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
    Get API configurations and current values from locations table.
    Returns: {
        location: {
            'wave_api_url': ..., 
            'wind_api_url': ..., 
            'wave_calculation_method': ...,
            'current_values': {
                'wave_height_m': ...,
                'wave_period_s': ...,
                'wind_speed_mps': ...,
                'wind_direction_deg': ...
            },
            'consecutive_identical_updates': ...
        }
    }
    """
    logger.info("📡 Getting location API configurations from database...")

    query = text("""
        SELECT 
            location, 
            wave_api_url, 
            wind_api_url, 
            COALESCE(wave_calculation_method, 'api') as wave_calculation_method,
            wave_height_m,
            wave_period_s,
            wind_speed_mps,
            wind_direction_deg,
            COALESCE(consecutive_identical_updates, 0) as consecutive_identical_updates
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
                    'wind_api_url': row.wind_api_url,
                    'wave_calculation_method': row.wave_calculation_method,
                    'consecutive_identical_updates': row.consecutive_identical_updates,
                    'current_values': {
                        'wave_height_m': row.wave_height_m,
                        'wave_period_s': row.wave_period_s,
                        'wind_speed_mps': row.wind_speed_mps,
                        'wind_direction_deg': row.wind_direction_deg
                    }
                }
                logger.info(f"✅ {row.location}: wave={row.wave_api_url[:50]}..., method={row.wave_calculation_method}")

        logger.info(f"✅ Loaded API configs for {len(configs)} locations")
        return configs

    except Exception as e:
        logger.error(f"❌ Failed to get location API configs: {e}")
        return {}


def get_current_location_values(engine, location):
    """
    Get current surf data values for a location from the database.

    Args:
        engine: Database engine
        location: Location name

    Returns:
        Dict with current values or None if location not found
    """
    query = text("""
        SELECT
            wave_height_m,
            wave_period_s,
            wind_speed_mps,
            wind_direction_deg,
            COALESCE(consecutive_identical_updates, 0) as consecutive_identical_updates
        FROM locations
        WHERE location = :location
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"location": location})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
    except Exception as e:
        logger.error(f"❌ Failed to get current values for {location}: {e}")
        return None


def get_active_locations(engine):
    """
    Get all locations that have active arduinos (scalable for 10K+ locations).
    Returns: ['Sdot Yam', 'Hilton Beach (Tel Aviv)', ...]

    Performance: O(1) - Single DB query instead of O(N) where N = total beaches.
    """
    query = text("""
        SELECT DISTINCT location
        FROM arduinos
        ORDER BY location
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            locations = [row[0] for row in result]
            logger.info(f"📊 Found {len(locations)} active locations")
            return locations
    except Exception as e:
        logger.error(f"❌ Failed to get active locations: {e}")
        return []


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


def update_location_conditions(engine, location, surf_data, consecutive_identical_updates=0, update_timestamp=True):
    """
    Update or insert location conditions (UPSERT).
    Auto-creates missing locations by generating API URLs from beaches.py.

    Args:
        location: Location name
        surf_data: Dict with new surf conditions
        consecutive_identical_updates: Count of identical updates
        update_timestamp: Whether to update last_value_change timestamp (True if values changed)
    """
    logger.info(f"🌊 Updating conditions for location: {location}")

    # Get API URLs from shared config (derived from beaches.py)
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from shared_config import get_api_sources_for_location

    api_sources = get_api_sources_for_location(location)
    wave_api_url = api_sources['wave'][0] if api_sources.get('wave') else ''
    wind_api_url = api_sources['wind'][0] if api_sources.get('wind') else ''

    # Prepare SQL - UPSERT with conditional last_value_change update
    # API URLs are required for new location inserts (NOT NULL constraint)
    if update_timestamp:
        query = text("""
            INSERT INTO locations (
                location,
                wave_api_url, wind_api_url,
                wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg,
                wave_calculation_method, consecutive_identical_updates,
                last_updated, last_value_change
            ) VALUES (
                :location,
                :wave_api_url, :wind_api_url,
                :wave_height, :wave_period, :wind_speed, :wind_direction,
                'api', :consecutive_identical_updates,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (location) DO UPDATE SET
                wave_height_m = EXCLUDED.wave_height_m,
                wave_period_s = EXCLUDED.wave_period_s,
                wind_speed_mps = EXCLUDED.wind_speed_mps,
                wind_direction_deg = EXCLUDED.wind_direction_deg,
                last_updated = CURRENT_TIMESTAMP,
                consecutive_identical_updates = EXCLUDED.consecutive_identical_updates,
                last_value_change = CURRENT_TIMESTAMP
        """)
    else:
        query = text("""
            INSERT INTO locations (
                location,
                wave_api_url, wind_api_url,
                wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg,
                wave_calculation_method, consecutive_identical_updates,
                last_updated, last_value_change
            ) VALUES (
                :location,
                :wave_api_url, :wind_api_url,
                :wave_height, :wave_period, :wind_speed, :wind_direction,
                'api', :consecutive_identical_updates,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (location) DO UPDATE SET
                wave_height_m = EXCLUDED.wave_height_m,
                wave_period_s = EXCLUDED.wave_period_s,
                wind_speed_mps = EXCLUDED.wind_speed_mps,
                wind_direction_deg = EXCLUDED.wind_direction_deg,
                last_updated = CURRENT_TIMESTAMP,
                consecutive_identical_updates = EXCLUDED.consecutive_identical_updates
        """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {
                "location": location,
                "wave_api_url": wave_api_url,
                "wind_api_url": wind_api_url,
                "wave_height": surf_data.get('wave_height_m', 0.0),
                "wave_period": surf_data.get('wave_period_s', 0.0),
                "wind_speed": surf_data.get('wind_speed_mps', 0.0),
                "wind_direction": surf_data.get('wind_direction_deg', 0),
                "consecutive_identical_updates": consecutive_identical_updates
            })
            conn.commit()

        logger.info(f"✅ Location updated: {location} (Identity Count: {consecutive_identical_updates})")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update location conditions for {location}: {e}")
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


def update_processor_heartbeat(engine, service_name='surf-lamp-processor'):
    """
    Update processor heartbeat timestamp (Watchdog pattern)
    Resets missed_count to 0 to signal the process is alive.

    Args:
        engine: SQLAlchemy engine
        service_name: Service identifier

    Returns:
        bool: True if successful
    """
    query = text("""
        INSERT INTO processor_heartbeat (service_name, last_alive_timestamp, missed_count, updated_at)
        VALUES (:service_name, NOW(), 0, NOW())
        ON CONFLICT (service_name)
        DO UPDATE SET
            last_alive_timestamp = NOW(),
            missed_count = 0,
            updated_at = NOW()
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {"service_name": service_name})
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update processor heartbeat: {e}")
        return False
