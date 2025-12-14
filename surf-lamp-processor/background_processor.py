# background_processor.py
"""
Background service for Surf Lamp processing
- Fetches surf data from APIs using configurable field mappings
- Updates database with current surf conditions
- Extensive logging for debugging

⚠️  CRITICAL ARCHITECTURAL NOTES FOR MAINTAINERS ⚠️
=================================================

DO NOT CHANGE THE FOLLOWING CORE ARCHITECTURE:

1. 🔄 PULL-BASED COMMUNICATION:
   - Arduino devices MUST fetch data from the web server (every 13 minutes)
   - This service ONLY updates the database - it does NOT push data to Arduino
   - NEVER call send_to_arduino() in the processing loop
   - Arduino pull-based architecture eliminates network complexity and firewall issues

2. 📍 LOCATION-BASED PROCESSING:
   - API calls MUST be grouped by location to eliminate duplicate requests
   - Multiple lamps in the same location share the same API endpoints
   - This prevents rate limiting (429 errors) and reduces API call volume by ~70%
   - NEVER revert to lamp-by-lamp processing

3. 🎯 MULTI-SOURCE PRIORITY SYSTEM:
   - Each location uses multiple API sources with priority ordering
   - Priority 1: Wave data (Isramar) - highest priority, most reliable
   - Priority 2+: Wind data (Open-Meteo variants) - backup sources
   - Data merging combines fields from all sources for complete surf conditions
   - NEVER simplify to single API source per location

4. 💾 BATCH DATABASE WRITES:
   - All lamps in a location are updated in single transactions
   - Reduces database operations by 85% (1,008/day → 144/day)
   - Faster processing and lower database load

5. ⏱️  OPTIMIZED UPDATE FREQUENCY:
   - Processor runs every 15 minutes (96 cycles/day)
   - Better alignment with Arduino 13-minute polling
   - More predictable data freshness (avg 8 minutes old)

These architectural decisions solve critical production issues:
- Eliminates 429 rate limiting errors
- Maintains data completeness (wave + wind data)
- Reduces processing time from 25 minutes to <2 minutes
- Reduces database operations by 85%
- Preserves reliable Arduino communication
"""

import os
import time
import requests
import logging
from sqlalchemy import create_engine, text


import json
from dotenv import load_dotenv
from endpoint_configs import get_endpoint_config


load_dotenv()
# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lamp_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Note: LOCATION_TIMEZONES imported from web_and_database/data_base.py within functions
# (see format_for_arduino function for dynamic import pattern)

# Database connection 
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set!")
    exit(1)

try:
    # For Supabase, explicitly require SSL
    connect_args = {}
    if "supabase.com" in DATABASE_URL:
        connect_args["sslmode"] = "require"
        
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    exit(1)


def extract_field_value(data, field_path):
    """
    Navigate nested JSON using field path like ['wind', 'speed'] or ['data', 0, 'value']

    Args:
        data: JSON data (dict or list)
        field_path: List of keys/indices to navigate

    Returns:
        Extracted value or None if not found
    """
    try:
        value = data
        for key in field_path:
            if isinstance(value, list) and isinstance(key, int):
                value = value[key]
            elif isinstance(value, dict):
                value = value[key]
            else:
                return None
        return value
    except (KeyError, TypeError, IndexError):
        return None

# Cache removal - no longer needed with location-based processing

def get_current_hour_index(time_array):
    """
    Find the index in the hourly time array that corresponds to the current hour.

    Args:
        time_array: List of time strings like ["2025-09-13T00:00", "2025-09-13T01:00", ...]

    Returns:
        int: Index for current hour, or 0 if not found
    """
    try:
        from datetime import datetime
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        current_hour_str = current_hour.strftime("%Y-%m-%dT%H:%M")

        logger.info(f"🕐 Looking for current hour: {current_hour_str}")

        for i, time_str in enumerate(time_array):
            if time_str.startswith(current_hour_str):
                logger.info(f"✅ Found current hour at index {i}: {time_str}")
                return i

        logger.warning("⚠️  Current hour not found in time array, using index 0")
        return 0

    except Exception as e:
        logger.warning(f"⚠️  Error finding current hour index: {e}, using index 0")
        return 0

# send_to_arduino() and related functions removed - unused push model
# Arduinos now pull data via GET /api/arduino/<id>/data endpoint

def apply_conversions(value, conversions, field_name):
    """
    Apply conversion functions to extracted field values.
    
    Args:
        value: Raw value from API
        conversions: Dict of conversion functions
        field_name: Name of the field being converted
        
    Returns:
        Converted value or original value if no conversion
    """
    if value is None or conversions is None:
        return value
        
    conversion_func = conversions.get(field_name)
    if conversion_func and callable(conversion_func):
        try:
            return conversion_func(value)
        except Exception as e:
            logger.warning(f"Conversion failed for {field_name}: {e}")
            return value
    
    return value

# In surf-lamp-processor/background_processor.py

def standardize_surf_data(raw_data, endpoint_url):
    """
    Extract standardized fields using endpoint-specific configuration.
    Only returns fields that are actually found in the API response.
    """
    logger.info(f"🔧 Standardizing data from: {endpoint_url}")

    config = get_endpoint_config(endpoint_url)
    if not config:
        logger.error(f"❌ No field mapping config found for {endpoint_url}")
        return None

    logger.info(f"✅ Found config with {len(config)} field mappings")

    # Start with an empty dictionary
    standardized = {}

    if config.get('custom_extraction'):
        from endpoint_configs import extract_isramar_data
        standardized = extract_isramar_data(raw_data)
    else:
        conversions = config.get('conversions', {})

        # For Open-Meteo APIs, find the current hour index in the time array
        current_hour_index = 0
        if "open-meteo.com" in endpoint_url and "hourly" in raw_data:
            time_array = raw_data.get("hourly", {}).get("time", [])
            if time_array:
                current_hour_index = get_current_hour_index(time_array)

        for standard_field, field_path in config.items():
            if standard_field in ['fallbacks', 'conversions', 'custom_extraction']:
                continue

            # For Open-Meteo hourly data, replace hardcoded index with current hour index
            if ("open-meteo.com" in endpoint_url and
                len(field_path) == 3 and
                field_path[0] == "hourly" and
                isinstance(field_path[2], int)):

                logger.info(f"🕐 Using current hour index {current_hour_index} for {standard_field}")
                field_path = [field_path[0], field_path[1], current_hour_index]

            raw_value = extract_field_value(raw_data, field_path)

            # IMPORTANT: Only add the field if a value was actually found
            if raw_value is not None:
                converted_value = apply_conversions(raw_value, conversions, standard_field)
                standardized[standard_field] = converted_value

    # Only add metadata if some data was actually extracted
    if standardized:
        standardized['timestamp'] = int(time.time())
        standardized['source_endpoint'] = endpoint_url

    logger.info(f"✅ Standardized data: {json.dumps(standardized, indent=2)}")
    return standardized

def test_database_connection():
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

def get_location_based_configs():
    """Get API configurations grouped by location - PURE LOCATION-CENTRIC APPROACH"""
    logger.info("📡 Getting location-based API configurations...")

    try:
        # Import the source of truth for location configurations
        import sys
        import os

        # Add the web_and_database directory to path using relative path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        web_db_path = os.path.join(parent_dir, 'web_and_database')
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

def get_lamps_for_location(location):
    """Get all lamps in a specific location"""
    logger.info(f"🔍 Getting lamps for location: {location}")

    query = text("""
        SELECT
            l.arduino_id,
            l.lamp_id,
            u.location,
            u.preferred_output as format,
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


def format_for_arduino(surf_data, format_type="meters", location=None):
    """Format surf data for Arduino consumption with location-aware time"""
    logger.info(f"🔧 Formatting data for Arduino (format: {format_type}, location: {location})")

    formatted = surf_data.copy()

    # Add location-aware current time (import shared timezone mapping from data_base)
    if location:
        import sys
        import pytz
        from datetime import datetime

        # Import LOCATION_TIMEZONES from shared config (single source of truth)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        web_db_path = os.path.join(parent_dir, 'web_and_database')
        if web_db_path not in sys.path:
            sys.path.append(web_db_path)

        from data_base import LOCATION_TIMEZONES

        if location in LOCATION_TIMEZONES:
            timezone_str = LOCATION_TIMEZONES[location]
            local_tz = pytz.timezone(timezone_str)
            current_time = datetime.now(local_tz)

            formatted['local_time'] = current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
            formatted['timezone'] = timezone_str
            logger.info(f"🕐 Added local time: {formatted['local_time']}")

    # Convert wave height to cm and wind speed to integer
    if 'wave_height_m' in formatted:
        formatted['wave_height_cm'] = int(round(formatted['wave_height_m'] * 100))
        del formatted['wave_height_m']

    # Keep wind_speed_mps as float for Arduino precision
    # Arduino uses: windSpeedLEDs = windSpeed * 18.0 / 13.0
    # Converting to int loses precision (e.g., 3.93 → 4, 4.35 → 4)

    if format_type == "feet":
        if 'wave_height_cm' in formatted:
            formatted["wave_height_ft"] = round(formatted["wave_height_cm"] / 30.48, 2)
        if 'wind_speed_mps' in formatted:
            formatted["wind_speed_mph"] = round(formatted["wind_speed_mps"] * 2.237, 2)
        logger.info(f"   Converted to imperial: {formatted.get('wave_height_ft', 0)}ft waves")
    else:
        logger.info(f"   Metric format: {formatted.get('wave_height_cm', 0)}cm waves")
    
    return formatted

def fetch_surf_data(api_key, endpoint):
    """Fetch surf data from external API and standardize using config

    ⚠️  CRITICAL MAINTAINER NOTE: WIND SPEED UNITS ⚠️
    ==============================================
    ALL Open-Meteo wind APIs MUST include "&wind_speed_unit=ms" parameter!
    - Without this parameter, APIs return km/h instead of m/s
    - This causes incorrect wind speed calculations throughout the system
    - Arduino expects wind_speed_mps (meters per second) from database
    - ALWAYS verify new wind endpoints include "&wind_speed_unit=ms"

    Example correct URL:
    https://api.open-meteo.com/v1/forecast?lat=32.0&lon=34.0&hourly=wind_speed_10m&wind_speed_unit=ms
    """
    logger.info(f"🌊 Fetching surf data from: {endpoint}")

    # CRITICAL VALIDATION: Check wind speed unit parameter
    if "wind_speed_10m" in endpoint and "open-meteo.com" in endpoint:
        if "&wind_speed_unit=ms" not in endpoint:
            logger.error("❌ CRITICAL ERROR: Open-Meteo wind endpoint missing '&wind_speed_unit=ms' parameter!")
            logger.error(f"❌ Endpoint: {endpoint}")
            logger.error("❌ This will return km/h instead of m/s and break wind calculations!")
            return None

    try:
        # Build headers - only add Authorization if API key exists
        headers = {'User-Agent': 'SurfLamp-Agent/1.0'}

        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key}'
            logger.info("📤 Making API request with authentication")
        else:
            logger.info("📤 Making API request without authentication (public endpoint)")

        logger.info(f"📤 Headers: {headers}")

        # Make the API call with retry logic for rate limiting and timeouts
        max_retries = 3
        base_delay = 60  # Start with 60 seconds for rate limit retries

        # Use longer timeout for OpenWeatherMap as it can be slower than marine APIs
        timeout_seconds = 30 if "openweathermap.org" in endpoint else 15
        logger.info(f"📤 Using {timeout_seconds}s timeout for this API")

        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, headers=headers, timeout=timeout_seconds)
                response.raise_for_status()
                break  # Success, exit retry loop
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Request timeout ({timeout_seconds}s) for {endpoint}")
                if attempt < max_retries - 1:  # Not the last attempt
                    delay = 30  # Shorter delay for timeout retries
                    logger.warning(f"⚠️ Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ All timeout retry attempts failed for {endpoint}")
                    return None
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:  # Not the last attempt
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"⚠️ Rate limited (429). Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limited after {max_retries} attempts, giving up")
                        raise e
                else:
                    raise e  # Other HTTP errors, don't retry

        # Add 30 second delay between all API calls to avoid rate limiting
        time.sleep(30)

        logger.info(f"✅ API call successful: {response.status_code}")
        logger.debug(f"📥 Raw response: {response.text[:200]}...")

        # Parse JSON response
        raw_data = response.json()

        # Standardize using endpoint configuration
        surf_data = standardize_surf_data(raw_data, endpoint)

        if surf_data:
            logger.info("✅ Surf data standardized successfully")
            return surf_data
        else:
            logger.error("❌ Failed to standardize surf data")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ HTTP request failed for {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing failed for {endpoint}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching surf data from {endpoint}: {e}")
        return None


def get_user_threshold_for_arduino(arduino_id):
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

def get_user_wind_threshold_for_arduino(arduino_id):
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


    
def update_lamp_timestamp(lamp_id):
    """Update lamp's last_updated timestamp"""
    logger.info(f"⏰ Updating timestamp for lamp {lamp_id}")
    
    query = text("""
        UPDATE lamps 
        SET last_updated = CURRENT_TIMESTAMP 
        WHERE lamp_id = :lamp_id
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"lamp_id": lamp_id})
            conn.commit()
            
        logger.info(f"✅ Timestamp updated for lamp {lamp_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update timestamp for lamp {lamp_id}: {e}")
        return False

def update_current_conditions(lamp_id, surf_data):
    """Update current_conditions table with latest surf data"""
    logger.info(f" Updating current conditions for lamp {lamp_id}")
    
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

def batch_update_lamp_timestamps(lamp_ids):
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
            result = conn.execute(query, {"lamp_ids": lamp_ids})
            conn.commit()

        logger.info(f"✅ Timestamps batch updated for {len(lamp_ids)} lamps")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to batch update timestamps: {e}")
        return False

def batch_update_current_conditions(lamp_ids, surf_data):
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

def process_all_lamps():
    """Main processing function - Location-based processing with multi-source priority"""
    logger.info("🚀 ======= STARTING LOCATION-BASED PROCESSING CYCLE =======")
    start_time = time.time()

    try:
        # Step 1: Test database connection
        if not test_database_connection():
            logger.error("❌ Database connection failed, aborting cycle")
            return False

        # Step 2: Get location-based API configurations
        location_configs = get_location_based_configs()
        if not location_configs:
            logger.error("❌ No location configurations found, aborting cycle")
            return False

        logger.info(f"📊 Processing {len(location_configs)} locations with multi-source APIs...")

        # Step 3: Process each location with multi-source priority
        total_lamps_updated = 0
        total_api_calls = 0

        for location, config in location_configs.items():
            logger.info(f"\n--- Processing Location: {location} ---")
            logger.info(f"Available API sources: {len(config['endpoints'])}")

            # Get all lamps in this location
            lamps = get_lamps_for_location(location)
            if not lamps:
                logger.warning(f"⚠️  No lamps found for location: {location}")
                continue

            # Try each API source in priority order until we get complete data
            combined_surf_data = {}

            for endpoint in config['endpoints']:
                logger.info(f"  Trying API: {endpoint['website_url']} (Priority: {endpoint['priority']})")
                total_api_calls += 1

                # Fetch data from this API source
                surf_data = fetch_surf_data(
                    endpoint['api_key'],
                    endpoint['http_endpoint']
                )

                if surf_data:
                    # Merge data, prioritizing fields from higher priority sources
                    for field, value in surf_data.items():
                        if field not in combined_surf_data or value is not None:
                            combined_surf_data[field] = value

                    logger.info(f"✅ Got data: {list(surf_data.keys())}")
                else:
                    logger.warning(f"⚠️  Failed to get data from {endpoint['website_url']}")

            # Check if we have sufficient data
            if not combined_surf_data:
                logger.error(f"❌ No data obtained for location {location}")
                continue

            logger.info(f"📊 Combined data for {location}: {list(combined_surf_data.keys())}")

            # Batch update all lamps in this location
            logger.info(f"📦 Batch updating {len(lamps)} lamps in {location}")

            # Extract all lamp IDs for this location (dynamic - adapts to any number of lamps)
            lamp_ids = [lamp['lamp_id'] for lamp in lamps]

            # Batch update timestamps and conditions
            timestamp_updated = batch_update_lamp_timestamps(lamp_ids)
            conditions_updated = batch_update_current_conditions(lamp_ids, combined_surf_data)

            if timestamp_updated and conditions_updated:
                total_lamps_updated += len(lamps)
                logger.info(f"✅ Batch updated {len(lamps)} lamps successfully")

                # Log individual lamp details for monitoring
                for lamp in lamps:
                    logger.info(f"   ✓ Lamp {lamp['lamp_id']} (Arduino {lamp['arduino_id']})")
            else:
                # Fallback to individual updates if batch fails
                logger.error(f"❌ Batch update failed for {location}")
                logger.warning("⚠️  Attempting individual fallback updates...")
                lamps_updated_for_location = 0
                for lamp in lamps:
                    logger.info(f"  Fallback: Updating lamp {lamp['lamp_id']} (Arduino {lamp['arduino_id']})")
                    timestamp_ok = update_lamp_timestamp(lamp['lamp_id'])
                    conditions_ok = update_current_conditions(lamp['lamp_id'], combined_surf_data)
                    if timestamp_ok and conditions_ok:
                        lamps_updated_for_location += 1
                        total_lamps_updated += 1
                        logger.info(f"   ✓ Lamp {lamp['lamp_id']} updated via fallback")
                    else:
                        logger.error(f"   ✗ Fallback failed for lamp {lamp['lamp_id']}")
                logger.info(f"📊 Fallback updated {lamps_updated_for_location}/{len(lamps)} lamps in {location}")

        # Final summary
        end_time = time.time()
        duration = round(end_time - start_time, 2)

        logger.info("\n🎉 ======= LOCATION-BASED PROCESSING CYCLE COMPLETED =======")
        logger.info("📊 Summary:")
        logger.info(f"   - Locations processed: {len(location_configs)}")
        logger.info(f"   - Total API calls made: {total_api_calls}")
        logger.info(f"   - Lamps updated: {total_lamps_updated}")
        logger.info(f"   - Duration: {duration} seconds")
        logger.info("   - Status: SUCCESS")

        return True

    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)

        logger.info("\n🚫 ======= LOCATION-BASED PROCESSING CYCLE FAILED =======")
        logger.info("📊 Summary:")
        logger.info(f"   - Error: {str(e)}")
        logger.info(f"   - Duration: {duration} seconds")
        logger.info("   - Status: FAILED")

        logger.error(f"💥 CRITICAL ERROR in processing cycle: {e}")
        return False

def run_once():
    """Run processing once for testing"""
    logger.info("🧪 Running single test cycle...")
    return process_all_lamps()

def main():
    """Main function - choose test mode or continuous mode"""
    logger.info("🚀 Starting Surf Lamp Background Processor...")
    
    # Check if we're in test mode
    test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
    
    if test_mode:
        logger.info("🧪 TEST MODE: Running once and exiting")
        success = run_once()
        exit(0 if success else 1)
    
    else:
        logger.info("🔄 PRODUCTION MODE: Running continuously every 15 minutes")

        # Run once immediately for testing
        logger.info("Running initial cycle...")
        process_all_lamps()

        # Then schedule every 15 minutes
        import schedule
        schedule.every(15).minutes.do(process_all_lamps)

        logger.info("⏰ Scheduled to run every 15 minutes. Waiting...")
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
