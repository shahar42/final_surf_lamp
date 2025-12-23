"""
Lamp Repository
Database access layer for surf lamp operations.

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

            # Check tables exist
            # SECURITY: Whitelist of allowed table names to prevent SQL injection
            ALLOWED_TABLES = {'users', 'lamps', 'daily_usage', 'usage_lamps', 'current_conditions', 'location_websites', 'password_reset_tokens'}
            tables_to_check = ['users', 'lamps', 'daily_usage', 'usage_lamps']

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


def get_location_based_configs(engine):
    """Get API configurations grouped by location - PURE LOCATION-CENTRIC APPROACH"""
    logger.info("📡 Getting location-based API configurations...")

    try:
        # Import the source of truth for location configurations
        # Add the web_and_database directory to path using relative path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        web_db_path = os.path.join(parent_dir, 'web_and_database')
        if web_db_path not in sys.path:
            sys.path.append(web_db_path)

        from data_base import get_active_location_config

        # Get the active configuration (stormglass or multi-source)
        ACTIVE_LOCATIONS = get_active_location_config()

        # Get all distinct locations that have active users
        query = text("SELECT DISTINCT location FROM users WHERE location IS NOT NULL")
        with engine.connect() as conn:
            result = conn.execute(query)
            active_locations = [row[0] for row in result]

        logger.info(f"📍 Found {len(active_locations)} active user locations: {active_locations}")

        # Build location configs using active configuration as source of truth
        location_configs = {}
        for location in active_locations:
            if location in ACTIVE_LOCATIONS:
                # Convert location config format to expected format
                endpoints = []
                for source in ACTIVE_LOCATIONS[location]:
                    endpoints.append({
                        'usage_id': None,  # Not needed for pure location-centric approach
                        'website_url': source['url'],
                        'api_key': source.get('api_key'),  # For stormglass API key
                        'http_endpoint': source['url'],
                        'priority': source['priority']
                    })

                location_configs[location] = {'endpoints': endpoints}
                logger.info(f"✅ {location}: {len(endpoints)} API sources from active configuration")
            else:
                logger.warning(f"⚠️  Location '{location}' not found in active configuration")

        logger.info(f"✅ Pure location-centric configuration complete: {len(location_configs)} locations")
        for location, config in location_configs.items():
            for endpoint in config['endpoints']:
                logger.info(f"   {location}: {endpoint['website_url']} (Priority: {endpoint['priority']})")

        return location_configs

    except Exception as e:
        logger.error(f"❌ Failed to get location configurations: {e}")
        return {}


def get_lamps_for_location(engine, location):
    """Get all lamps in a specific location"""
    logger.info(f"🔍 Getting lamps for location: {location}")

    query = text("""
        SELECT
            l.arduino_id,
            l.lamp_id,
            u.location,
            l.last_updated
        FROM lamps l
        JOIN users u ON l.user_id = u.user_id
        WHERE u.location = :location
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"location": location})
            lamps = [dict(row._mapping) for row in result]

        logger.info(f"✅ Found {len(lamps)} lamps in {location}:")
        for lamp in lamps:
            logger.info(f"   - Arduino {lamp['arduino_id']} (Lamp {lamp['lamp_id']})")

        return lamps

    except Exception as e:
        logger.error(f"❌ Failed to get lamps for location: {e}")
        return []


def get_user_threshold_for_arduino(engine, arduino_id):
    """Get user's wave threshold for this Arduino"""
    query = text("""
        SELECT u.wave_threshold_m
        FROM users u
        JOIN lamps l ON u.user_id = l.user_id
        WHERE l.arduino_id = :arduino_id
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
    """Get user's wind threshold for this Arduino"""
    query = text("""
        SELECT u.wind_threshold_knots
        FROM users u
        JOIN lamps l ON u.user_id = l.user_id
        WHERE l.arduino_id = :arduino_id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"arduino_id": arduino_id})
            row = result.fetchone()
            return row[0] if row and row[0] else 22.0
    except Exception as e:
        logger.error(f"Failed to get wind threshold for Arduino {arduino_id}: {e}")
        return 22.0  # Safe default


def update_lamp_timestamp(engine, lamp_id):
    """Update lamp's last_updated timestamp"""
    logger.info(f"⏰ Updating timestamp for lamp {lamp_id}")

    query = text("""
        UPDATE lamps
        SET last_updated = CURRENT_TIMESTAMP
        WHERE lamp_id = :lamp_id
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {"lamp_id": lamp_id})
            conn.commit()

        logger.info(f"✅ Timestamp updated for lamp {lamp_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update timestamp for lamp {lamp_id}: {e}")
        return False


def update_current_conditions(engine, lamp_id, surf_data):
    """Update current_conditions table with latest surf data"""
    logger.info(f"🌊 Updating current conditions for lamp {lamp_id}")

    query = text("""
        INSERT INTO current_conditions (
            lamp_id, wave_height_m, wave_period_s,
            wind_speed_mps, wind_direction_deg, last_updated
        ) VALUES (
            :lamp_id, :wave_height_m, :wave_period_s,
            :wind_speed_mps, :wind_direction_deg, CURRENT_TIMESTAMP
        )
        ON CONFLICT (lamp_id)
        DO UPDATE SET
            wave_height_m = EXCLUDED.wave_height_m,
            wave_period_s = EXCLUDED.wave_period_s,
            wind_speed_mps = EXCLUDED.wind_speed_mps,
            wind_direction_deg = EXCLUDED.wind_direction_deg,
            last_updated = CURRENT_TIMESTAMP
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "lamp_id": lamp_id,
                "wave_height_m": surf_data.get('wave_height_m', 0.0),
                "wave_period_s": surf_data.get('wave_period_s', 0.0),
                "wind_speed_mps": surf_data.get('wind_speed_mps', 0.0),
                "wind_direction_deg": surf_data.get('wind_direction_deg', 0)
            })
            conn.commit()

        logger.info(f"✅ Current conditions updated for lamp {lamp_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update current conditions for lamp {lamp_id}: {e}")
        return False


def batch_update_lamp_timestamps(engine, lamp_ids):
    """
    Update timestamps for multiple lamps in a single transaction.

    Args:
        lamp_ids: List of lamp IDs to update

    Returns:
        bool: True if successful
    """
    if not lamp_ids:
        return True

    logger.info(f"⏰ Batch updating timestamps for {len(lamp_ids)} lamps")

    query = text("""
        UPDATE lamps
        SET last_updated = CURRENT_TIMESTAMP
        WHERE lamp_id = ANY(:lamp_ids)
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {"lamp_ids": lamp_ids})
            conn.commit()

        logger.info(f"✅ Timestamps batch updated for {len(lamp_ids)} lamps")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to batch update timestamps: {e}")
        return False


def batch_update_current_conditions(engine, lamp_ids, surf_data):
    """
    Update current conditions for multiple lamps with the same surf data.
    Uses PostgreSQL unnest() for safe parameterized bulk upsert.

    Args:
        lamp_ids: List of lamp IDs to update
        surf_data: Dict with wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg

    Returns:
        bool: True if successful
    """
    if not lamp_ids:
        return True

    logger.info(f"📊 Batch updating conditions for {len(lamp_ids)} lamps")

    query = text("""
        INSERT INTO current_conditions (
            lamp_id, wave_height_m, wave_period_s,
            wind_speed_mps, wind_direction_deg, last_updated
        )
        SELECT
            unnest(:lamp_ids),
            :wave_height,
            :wave_period,
            :wind_speed,
            :wind_direction,
            CURRENT_TIMESTAMP
        ON CONFLICT (lamp_id)
        DO UPDATE SET
            wave_height_m = EXCLUDED.wave_height_m,
            wave_period_s = EXCLUDED.wave_period_s,
            wind_speed_mps = EXCLUDED.wind_speed_mps,
            wind_direction_deg = EXCLUDED.wind_direction_deg,
            last_updated = CURRENT_TIMESTAMP
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "lamp_ids": lamp_ids,
                "wave_height": surf_data.get('wave_height_m', 0.0),
                "wave_period": surf_data.get('wave_period_s', 0.0),
                "wind_speed": surf_data.get('wind_speed_mps', 0.0),
                "wind_direction": surf_data.get('wind_direction_deg', 0)
            })
            conn.commit()

        logger.info(f"✅ Conditions batch updated for {len(lamp_ids)} lamps")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to batch update conditions: {e}")
        return False
