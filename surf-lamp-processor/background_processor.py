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
import json
from dotenv import load_dotenv
# Import the endpoint configuration system
# Import the endpoint configuration system
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

# Database connection (same as your Flask app)
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set!")
    exit(1)

try:
    engine = create_engine(DATABASE_URL)
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

def standardize_surf_data(raw_data, endpoint_url):
    """
    Extract standardized fields using endpoint-specific configuration.
    
    Args:
        raw_data: Raw JSON response from API
        endpoint_url: The API endpoint URL
        
    Returns:
        Dict with standardized surf data fields
    """
    logger.info(f"🔧 Standardizing data from: {endpoint_url}")
    
    # Get configuration for this endpoint
    config = get_endpoint_config(endpoint_url)
    if not config:
        logger.error(f"❌ No field mapping config found for {endpoint_url}")
        logger.error(f"   Supported endpoints: {list(FIELD_MAPPINGS.keys())}")
        return None
    
    logger.info(f"✅ Found config with {len(config)} field mappings")
    
    standardized = {}
    conversions = config.get('conversions', {})
    fallbacks = config.get('fallbacks', {})
    
    # Extract each configured field
    for standard_field, field_path in config.items():
        if standard_field in ['fallbacks', 'conversions']:
            continue
            
        # Extract the raw value
        raw_value = extract_field_value(raw_data, field_path)
        logger.debug(f"   {standard_field}: {field_path} -> {raw_value}")
        
        # Apply conversions if configured
        converted_value = apply_conversions(raw_value, conversions, standard_field)
        
        # Use fallback if value is None
        if converted_value is None:
            converted_value = fallbacks.get(standard_field)
            logger.debug(f"   {standard_field}: Using fallback -> {converted_value}")
        
        standardized[standard_field] = converted_value
    
    # Add required fields with fallbacks if not present
    required_fields = ['wave_height_m', 'wave_period_s', 'wind_speed_mps', 'wind_direction_deg']
    for field in required_fields:
        if field not in standardized:
            standardized[field] = fallbacks.get(field, 0.0)
    
    # Add metadata
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

def get_unique_api_configs():
    """Get unique API configurations to avoid redundant calls"""
    logger.info("📡 Getting unique API configurations...")
    
    query = text("""
        SELECT DISTINCT 
            du.usage_id,
            du.website_url,
            ul.api_key, 
            ul.http_endpoint
        FROM daily_usage du
        JOIN usage_lamps ul ON du.usage_id = ul.usage_id
        WHERE ul.http_endpoint IS NOT NULL
        AND ul.http_endpoint != ''
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            configs = [dict(row._mapping) for row in result]
            
        logger.info(f"✅ Found {len(configs)} unique API configurations:")
        for i, config in enumerate(configs, 1):
            logger.info(f"   {i}. {config['website_url']} (usage_id: {config['usage_id']})")
            
        return configs
        
    except Exception as e:
        logger.error(f"❌ Failed to get API configurations: {e}")
        return []

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

def fetch_surf_data(api_key, endpoint):
    """Fetch surf data from external API and standardize using config"""
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
        response = requests.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"✅ API call successful: {response.status_code}")
        logger.debug(f"📥 Raw response: {response.text[:200]}...")
        
        # Parse JSON response
        raw_data = response.json()
        
        # Standardize using endpoint configuration
        surf_data = standardize_surf_data(raw_data, endpoint)
        
        if surf_data:
            logger.info(f"✅ Surf data standardized successfully")
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

def format_for_arduino(surf_data, format_type="meters"):
    """Format surf data for Arduino consumption"""
    logger.info(f"🔧 Formatting data for Arduino (format: {format_type})")
    
    formatted = surf_data.copy()
    
    # Convert units if needed
    if format_type == "feet":
        if surf_data.get("wave_height_m"):
            formatted["wave_height_ft"] = round(surf_data["wave_height_m"] * 3.28084, 2)
        if surf_data.get("wind_speed_mps"):
            formatted["wind_speed_mph"] = round(surf_data["wind_speed_mps"] * 2.237, 2)
        logger.info(f"   Converted to imperial: {formatted.get('wave_height_ft', 0)}ft waves, {formatted.get('wind_speed_mph', 0)}mph wind")
    else:
        logger.info(f"   Metric format: {formatted.get('wave_height_m', 0)}m waves, {formatted.get('wind_speed_mps', 0)}mps wind")
    
    return formatted

def send_to_arduino(arduino_id, surf_data, format_type="meters"):
    """Send surf data to Arduino device via HTTP POST"""
    logger.info(f"📡 Sending data to Arduino {arduino_id}...")
    
    try:
        # Get Arduino IP address
        arduino_ip = get_arduino_ip(arduino_id)
        if not arduino_ip:
            logger.error(f"❌ No IP address found for Arduino {arduino_id}")
            return False
        
        # Format data based on user preferences
        formatted_data = format_for_arduino(surf_data, format_type)
        
        # Prepare HTTP POST
        arduino_url = f"http://{arduino_ip}/api/update"
        headers = {'Content-Type': 'application/json'}
        
        logger.info(f"📤 POST URL: {arduino_url}")
        logger.info(f"📤 POST Headers: {headers}")
        logger.info(f"📤 POST Data: {json.dumps(formatted_data, indent=2)}")
        
        # Make the HTTP POST to Arduino
        response = requests.post(
            arduino_url, 
            json=formatted_data, 
            headers=headers,
            timeout=10
        )
        
        logger.info(f"📥 Arduino response status: {response.status_code}")
        logger.info(f"📥 Arduino response body: {response.text}")
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully sent data to Arduino {arduino_id}")
            return True
        else:
            logger.error(f"❌ Arduino {arduino_id} returned status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to send data to Arduino {arduino_id}: {e}")
        return False

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
    """Main processing function - complete loop with real API calls"""
    logger.info("🚀 ======= STARTING LAMP PROCESSING CYCLE =======")
    start_time = time.time()
    
    try:
        # Step 1: Test database connection
        if not test_database_connection():
            logger.error("❌ Database connection failed, aborting cycle")
            return False
        
        # Step 2: Get unique API configurations
        api_configs = get_unique_api_configs()
        if not api_configs:
            logger.error("❌ No API configurations found, aborting cycle")
            return False
        
        logger.info(f"📊 Processing {len(api_configs)} unique API configurations...")
        
        # Step 3: Process each API configuration
        total_arduinos_updated = 0
        
        for i, config in enumerate(api_configs, 1):
            logger.info(f"\n--- Processing API {i}/{len(api_configs)} ---")
            logger.info(f"API: {config['website_url']}")
            
            # Fetch surf data once per API
            surf_data = fetch_surf_data(
                config['api_key'], 
                config['http_endpoint']
            )
            
            if surf_data is None:
                logger.error(f"❌ Skipping API {config['usage_id']} due to fetch failure")
                continue
            
            # Get all Arduino devices that need this data
            arduino_targets = get_arduinos_for_api(config['usage_id'])
            
            if not arduino_targets:
                logger.warning(f"⚠️  No Arduino targets found for API {config['usage_id']}")
                continue
            
            # Send to all relevant Arduino devices
            for j, target in enumerate(arduino_targets, 1):
                logger.info(f"\n  Sending to Arduino {j}/{len(arduino_targets)}")
                
                success = send_to_arduino(
                    target['arduino_id'], 
                    surf_data, 
                    target['format']
                )
                
                # Update timestamp regardless of Arduino success
                # (we fetched the data successfully)
                update_success = update_lamp_timestamp(target['lamp_id'])

                # Update current conditions table with surf data
                conditions_updated = update_current_conditions(target['lamp_id'], surf_data)
                
                if success and update_success:
                    total_arduinos_updated += 1
                    logger.info(f"✅ Arduino {target['arduino_id']} processed successfully")
                else:
                    logger.error(f"❌ Issues processing Arduino {target['arduino_id']}")
        
        # Final summary
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.info(f"\n🎉 ======= LAMP PROCESSING CYCLE COMPLETED =======")
        logger.info(f"📊 Summary:")
        logger.info(f"   - APIs processed: {len(api_configs)}")
        logger.info(f"   - Arduinos updated: {total_arduinos_updated}")
        logger.info(f"   - Duration: {duration} seconds")
        logger.info(f"   - Status: SUCCESS")
        
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
        logger.info("🔄 PRODUCTION MODE: Running continuously every 30 minutes")
        
        # Run once immediately for testing
        logger.info("Running initial cycle...")
        process_all_lamps()
        
        # Then schedule every 30 minutes
        import schedule
        schedule.every(30).minutes.do(process_all_lamps)
        
        logger.info("⏰ Scheduled to run every 30 minutes. Waiting...")
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
