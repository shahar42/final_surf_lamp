# background_processor.py
"""
Background service for Surf Lamp processing
- Fetches surf data from APIs using configurable field mappings
- Sends data to Arduino devices via HTTP POST
- Extensive logging for debugging
"""

import os
import time
import requests
import logging
from sqlalchemy import create_engine, text
from datetime import datetime


from collections import defaultdict
import json
from arduino_transport import get_arduino_transport
from dotenv import load_dotenv
from endpoint_configs import FIELD_MAPPINGS, get_endpoint_config


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
arduino_transport = get_arduino_transport()

# Global failure tracking
arduino_failure_counts = defaultdict(int)
arduino_last_failure = defaultdict(float)
ARDUINO_FAILURE_THRESHOLD = 3  # Skip after 3 consecutive failures
ARDUINO_RETRY_DELAY = 1800     # 30 minutes before retry

# API request cache to avoid duplicate calls per cycle
api_request_cache = {}
cache_reset_time = None

# Location to timezone mapping
LOCATION_TIMEZONES = {
    "Hadera, Israel": "Asia/Jerusalem",
    "Tel Aviv, Israel": "Asia/Jerusalem", 
    "Ashdod, Israel": "Asia/Jerusalem",
    "Haifa, Israel": "Asia/Jerusalem",
    "Netanya, Israel": "Asia/Jerusalem",
    "San Diego, USA": "America/Los_Angeles",
    "Barcelona, Spain": "Europe/Madrid",
    # open for future updates
}

# Database connection (same as your Flask app)
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
    logger.info(f"Database engine created successfully")
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

def reset_api_cache():
    """Reset API cache at the start of each processing cycle"""
    global api_request_cache, cache_reset_time
    api_request_cache = {}
    cache_reset_time = time.time()
    logger.info("🗑️  API request cache reset for new processing cycle")

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

        logger.warning(f"⚠️  Current hour not found in time array, using index 0")
        return 0

    except Exception as e:
        logger.warning(f"⚠️  Error finding current hour index: {e}, using index 0")
        return 0

def should_skip_arduino(arduino_id):
    """Check if Arduino should be skipped due to recent failures"""
    failure_count = arduino_failure_counts[arduino_id]
    
    if failure_count < ARDUINO_FAILURE_THRESHOLD:
        return False  # Normal case - proceed with Arduino
    
    last_failure_time = arduino_last_failure[arduino_id]
    
    if time.time() - last_failure_time < ARDUINO_RETRY_DELAY:
        logger.info(f"Skipping Arduino {arduino_id} (failed {failure_count} times, retry in {int(ARDUINO_RETRY_DELAY - (time.time() - last_failure_time))}s)")
        return True
    else:
        # Reset failure count after retry delay
        arduino_failure_counts[arduino_id] = 0
        logger.info(f"Retrying Arduino {arduino_id} after cooldown")
        return False

def record_arduino_result(arduino_id, success):
    """Record Arduino communication result"""
    if success:
        # Reset failure count on success
        arduino_failure_counts[arduino_id] = 0
        if arduino_id in arduino_last_failure:
            del arduino_last_failure[arduino_id]
    else:
        # Increment failure count
        arduino_failure_counts[arduino_id] += 1
        arduino_last_failure[arduino_id] = time.time()
        logger.warning(f"Arduino {arduino_id} failure count: {arduino_failure_counts[arduino_id]}")

def send_to_arduino(arduino_id, surf_data, format_type="meters", location=None):
    """Send surf data to Arduino device via configurable transport with failure tracking"""
    
    # Check if we should skip this Arduino due to recent failures
    if should_skip_arduino(arduino_id):
        return False
    
    logger.info(f"📡 Sending data to Arduino {arduino_id}...")
    
    try:
        # Get Arduino IP address
        arduino_ip = get_arduino_ip(arduino_id)
        if not arduino_ip:
            logger.warning(f"⚠️  No IP address found for Arduino {arduino_id}")
            # In mock mode, we can still simulate with a placeholder IP
            if os.environ.get('ARDUINO_TRANSPORT', 'http').lower() == 'mock':
                arduino_ip = "192.168.1.100"  # Placeholder for mock demonstration
                logger.info(f"🧪 Using placeholder IP for mock: {arduino_ip}")
            else:
                record_arduino_result(arduino_id, False)  # Record failure
                return False
        
        # Get user's thresholds
        user_wave_threshold = get_user_threshold_for_arduino(arduino_id)
        user_wind_threshold = get_user_wind_threshold_for_arduino(arduino_id)
        
        # Format data based on user preferences
        formatted_data = format_for_arduino(surf_data, format_type, location)
        
        # Add thresholds to Arduino payload
        formatted_data['wave_threshold_cm'] = int(round(user_wave_threshold * 100))
        formatted_data['wind_speed_threshold_knots'] = int(round(user_wind_threshold))
        
        headers = {'Content-Type': 'application/json'}
        
        # Use transport abstraction
        success, status_code, response_text = arduino_transport.send_data(
            arduino_id, arduino_ip, formatted_data, headers
        )
        
        # Record the result for failure tracking
        record_arduino_result(arduino_id, success)
        
        if success:
            logger.info(f"✅ Successfully sent data to Arduino {arduino_id}")
            return True
        else:
            logger.warning(f"⚠️  Arduino {arduino_id} returned status {status_code}: {response_text}")
            return False
            
    except Exception as e:
        # Record failure for any exception
        record_arduino_result(arduino_id, False)
        logger.warning(f"⚠️  Error sending to Arduino {arduino_id}: {e}")
        return False

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
            tables_to_check = ['users', 'lamps', 'daily_usage', 'usage_lamps']
            for table in tables_to_check:
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

def get_lamp_api_configs():
    """Get API configurations grouped by lamp_id to handle multi-source lamps"""
    logger.info("📡 Getting lamp API configurations grouped by lamp_id...")
    
    query = text("""
        SELECT 
            ul.lamp_id,
            ul.usage_id,
            ul.http_endpoint,
            ul.api_key,
            ul.endpoint_priority,
            l.arduino_id,
            u.location,
            u.preferred_output as format
        FROM usage_lamps ul
        JOIN lamps l ON ul.lamp_id = l.lamp_id
        JOIN users u ON l.user_id = u.user_id
        WHERE ul.http_endpoint IS NOT NULL
        AND ul.http_endpoint != ''
        ORDER BY ul.lamp_id, ul.endpoint_priority
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = [dict(row._mapping) for row in result]
        
        # Group by lamp_id
        lamp_configs = {}
        for row in rows:
            lamp_id = row['lamp_id']
            if lamp_id not in lamp_configs:
                lamp_configs[lamp_id] = {
                    'arduino_id': row['arduino_id'],
                    'location': row['location'],
                    'format': row['format'],
                    'endpoints': []
                }
            
            lamp_configs[lamp_id]['endpoints'].append({
                'usage_id': row['usage_id'],
                'http_endpoint': row['http_endpoint'],
                'api_key': row['api_key'],
                'priority': row['endpoint_priority']
            })
        
        logger.info(f"✅ Found {len(lamp_configs)} lamps with multi-source configurations")
        for lamp_id, config in lamp_configs.items():
            logger.info(f"   Lamp {lamp_id}: {len(config['endpoints'])} API sources")
            
        return lamp_configs
        
    except Exception as e:
        logger.error(f"❌ Failed to get lamp API configurations: {e}")
        return {}

def get_arduinos_for_api(usage_id):
    """Get all Arduino targets that need data from this API"""
    logger.info(f"🔍 Getting Arduino targets for usage_id: {usage_id}")
    
    query = text("""
        SELECT 
            l.arduino_id, 
            l.lamp_id, 
            u.location,
            u.preferred_output as format,
            l.last_updated
        FROM lamps l
        JOIN users u ON l.user_id = u.user_id
        JOIN usage_lamps ul ON l.lamp_id = ul.lamp_id
        WHERE ul.usage_id = :usage_id
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"usage_id": usage_id})
            targets = [dict(row._mapping) for row in result]
            
        logger.info(f"✅ Found {len(targets)} Arduino targets:")
        for target in targets:
            logger.info(f"   - Arduino {target['arduino_id']} (Lamp {target['lamp_id']}) in {target['location']}")
            
        return targets
        
    except Exception as e:
        logger.error(f"❌ Failed to get Arduino targets: {e}")
        return []

def get_arduino_ip(arduino_id):
    """Get Arduino IP address from database"""
    logger.info(f"📍 Looking up IP for Arduino {arduino_id}")
    
    query = text("""
        SELECT arduino_ip 
        FROM lamps 
        WHERE arduino_id = :arduino_id
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"arduino_id": arduino_id})
            row = result.fetchone()
            
            if row and row[0]:
                ip = row[0]
                logger.info(f"✅ Found IP for Arduino {arduino_id}: {ip}")
                return ip
            else:
                logger.warning(f"⚠️  No IP address found for Arduino {arduino_id} in database")
                return None
                
    except Exception as e:
        logger.error(f"❌ Database error looking up Arduino IP: {e}")
        return None

def format_for_arduino(surf_data, format_type="meters", location=None):
    """Format surf data for Arduino consumption with location-aware time"""
    logger.info(f"🔧 Formatting data for Arduino (format: {format_type}, location: {location})")
    
    formatted = surf_data.copy()

    # Add location-aware current time
    if location and location in LOCATION_TIMEZONES:
        import pytz
        from datetime import datetime
        
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

    if 'wind_speed_mps' in formatted:
        formatted['wind_speed_mps'] = int(round(formatted['wind_speed_mps']))

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
    """Fetch surf data from external API and standardize using config"""
    # Check cache first
    cache_key = endpoint
    if cache_key in api_request_cache:
        logger.info(f"💾 Using cached data for: {endpoint}")
        return api_request_cache[cache_key]

    logger.info(f"🌊 Fetching surf data from: {endpoint}")

    try:
        # Build headers - only add Authorization if API key exists
        headers = {'User-Agent': 'SurfLamp-Agent/1.0'}

        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key}'
            logger.info(f"📤 Making API request with authentication")
        else:
            logger.info(f"📤 Making API request without authentication (public endpoint)")

        logger.info(f"📤 Headers: {headers}")

        # Make the actual API call
        response = requests.get(endpoint, headers=headers, timeout=5)
        response.raise_for_status()

        # Add 3 second delay between all API calls
        time.sleep(3)

        logger.info(f"✅ API call successful: {response.status_code}")
        logger.debug(f"📥 Raw response: {response.text[:200]}...")

        # Parse JSON response
        raw_data = response.json()

        # Standardize using endpoint configuration
        surf_data = standardize_surf_data(raw_data, endpoint)

        if surf_data:
            logger.info(f"✅ Surf data standardized successfully")
            # Cache the result
            api_request_cache[cache_key] = surf_data
            return surf_data
        else:
            logger.error(f"❌ Failed to standardize surf data")
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

def process_all_lamps():
    """Main processing function - handles multi-source API calls per lamp"""
    logger.info("🚀 ======= STARTING LAMP PROCESSING CYCLE =======")
    start_time = time.time()

    try:
        # Step 1: Test database connection
        if not test_database_connection():
            logger.error("❌ Database connection failed, aborting cycle")
            return False

        # Step 2: Get lamp configurations (grouped by lamp_id)
        lamp_configs = get_lamp_api_configs()
        if not lamp_configs:
            logger.error("❌ No lamp configurations found, aborting cycle")
            return False

        logger.info(f"📊 Processing {len(lamp_configs)} lamps with multi-source APIs...")

        # Step 3: Process each lamp
        total_database_updates = 0

        for lamp_id, lamp_config in lamp_configs.items():
            logger.info(f"\n--- Processing Lamp {lamp_id} ({lamp_config['location']}) ---")
            logger.info(f"API sources: {len(lamp_config['endpoints'])}")

            # Define required parameters for complete surf data
            required_parameters = {
                'wave_height_m', 'wave_period_s', 'wind_speed_mps', 'wind_direction_deg'
            }

            # Initialize data collection
            combined_data = {}
            successful_fetches = 0

            # Process APIs by priority until we have all required data
            for endpoint in lamp_config['endpoints']:
                # Check what parameters we're still missing
                missing_parameters = required_parameters - set(combined_data.keys())

                if not missing_parameters:
                    logger.info(f"✅ All required parameters collected! Skipping remaining APIs.")
                    break

                logger.info(f"🔍 Missing parameters: {missing_parameters}")
                logger.info(f"📡 Fetching from priority {endpoint['priority']} API...")

                try:
                    source_data = fetch_surf_data(
                        endpoint['api_key'],
                        endpoint['http_endpoint']
                    )

                    if source_data:
                        # Count how many NEW parameters this API provided
                        new_parameters = set(source_data.keys()) & missing_parameters

                        if new_parameters:
                            # Only merge the parameters we actually needed
                            for param in new_parameters:
                                combined_data[param] = source_data[param]

                            successful_fetches += 1
                            logger.info(f"✅ Priority {endpoint['priority']} API provided: {new_parameters}")
                        else:
                            logger.info(f"ℹ️  Priority {endpoint['priority']} API returned data but no new required parameters")
                    else:
                        logger.warning(f"⚠️  Priority {endpoint['priority']} API returned no data")

                except Exception as e:
                    logger.warning(f"⚠️  Priority {endpoint['priority']} API failed: {e}")
                    # Continue with other endpoints for missing data

            # Final status check
            final_missing = required_parameters - set(combined_data.keys())

            if final_missing:
                logger.warning(f"⚠️  Incomplete data for lamp {lamp_id}. Missing: {final_missing}")
                # Add NULL values for missing parameters so Arduino gets consistent data structure
                for param in final_missing:
                    combined_data[param] = 0.0 if 'deg' not in param else 0
                logger.info(f"🔧 Added default values for missing parameters")

            # Process lamp if we got any data at all
            if combined_data and successful_fetches > 0:
                logger.info(f"📊 Final data from {successful_fetches} API source(s): {list(combined_data.keys())}")

                # Always update database first (dashboard guaranteed)
                timestamp_updated = update_lamp_timestamp(lamp_id)
                conditions_updated = update_current_conditions(lamp_id, combined_data)

                if timestamp_updated and conditions_updated:
                    total_database_updates += 1
                    logger.info(f"✅ Database updated for lamp {lamp_id}")
            else:
                logger.error(f"❌ No usable data for lamp {lamp_id} - all API sources failed")

        # Final summary
        end_time = time.time()
        duration = round(end_time - start_time, 2)

        logger.info(f"\n🎉 ======= LAMP PROCESSING CYCLE COMPLETED =======")
        logger.info(f"📊 Summary:")
        logger.info(f"   - Lamps processed: {len(lamp_configs)}")
        logger.info(f"   - Database updates: {total_database_updates}")
        logger.info(f"   - Duration: {duration} seconds")
        logger.info(f"   - Status: {'SUCCESS' if total_database_updates > 0 else 'FAILED'}")

        return True

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in lamp processing cycle: {e}")
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
        logger.info("🔄 PRODUCTION MODE: Running continuously every 20 minutes")

        # Run once immediately for testing
        logger.info("Running initial cycle...")
        process_all_lamps()

        # Then schedule every 20 minutes
        import schedule
        schedule.every(20).minutes.do(process_all_lamps)

        logger.info("⏰ Scheduled to run every 20 minutes. Waiting...")
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
