# background_processor.py
"""
Background service for Surf Lamp processing with threading optimization
- Fetches surf data from APIs using configurable field mappings
- Sends data to Arduino devices via HTTP POST in parallel
- Extensive logging for debugging
"""

import os
import time
import requests
import logging
from sqlalchemy import create_engine, text
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Database connection configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set!")
    exit(1)

try:
    # Connection pool configuration for threading
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,          # Base connections in pool
        max_overflow=30,       # Additional connections beyond pool_size
        pool_timeout=30,       # Seconds to wait for connection
        pool_recycle=3600      # Recycle connections after 1 hour
    )
    logger.info(f"Database engine created with connection pooling")
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
    Only returns fields that are actually found in the API response.
    """
    logger.info(f"Standardizing data from: {endpoint_url}")
    
    config = get_endpoint_config(endpoint_url)
    if not config:
        logger.error(f"No field mapping config found for {endpoint_url}")
        return None
    
    logger.info(f"Found config with {len(config)} field mappings")
    
    # Start with an empty dictionary
    standardized = {}
    
    if config.get('custom_extraction'):
        from endpoint_configs import extract_isramar_data
        standardized = extract_isramar_data(raw_data)
    else:
        conversions = config.get('conversions', {})
        
        for standard_field, field_path in config.items():
            if standard_field in ['fallbacks', 'conversions', 'custom_extraction']:
                continue
            
            raw_value = extract_field_value(raw_data, field_path)
            
            # Only add the field if a value was actually found
            if raw_value is not None:
                converted_value = apply_conversions(raw_value, conversions, standard_field)
                standardized[standard_field] = converted_value

    # Only add metadata if some data was actually extracted
    if standardized:
        standardized['timestamp'] = int(time.time())
        standardized['source_endpoint'] = endpoint_url
    
    logger.info(f"Standardized data: {json.dumps(standardized, indent=2)}")
    return standardized

def test_database_connection():
    """Test database connection and show table info"""
    logger.info("Testing database connection...")
    
    try:
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            
            # Check tables exist
            tables_to_check = ['users', 'lamps', 'daily_usage', 'usage_lamps']
            for table in tables_to_check:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    logger.info(f"Table {table}: {count} records")
                except Exception as e:
                    logger.error(f"Table {table} check failed: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_lamp_api_configs():
    """Get API configurations grouped by lamp_id to handle multi-source lamps"""
    logger.info("Getting lamp API configurations grouped by lamp_id...")
    
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
        
        logger.info(f"Found {len(lamp_configs)} lamps with multi-source configurations")
        for lamp_id, config in lamp_configs.items():
            logger.info(f"Lamp {lamp_id}: {len(config['endpoints'])} API sources")
            
        return lamp_configs
        
    except Exception as e:
        logger.error(f"Failed to get lamp API configurations: {e}")
        return {}

def get_arduino_ip(arduino_id):
    """Get Arduino IP address from database"""
    logger.info(f"Looking up IP for Arduino {arduino_id}")
    
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
                logger.info(f"Found IP for Arduino {arduino_id}: {ip}")
                return ip
            else:
                logger.warning(f"No IP address found for Arduino {arduino_id} in database")
                return None
                
    except Exception as e:
        logger.error(f"Database error looking up Arduino IP: {e}")
        return None

def fetch_surf_data(api_key, endpoint):
    """Fetch surf data from external API and standardize using config"""
    logger.info(f"Fetching surf data from: {endpoint}")
    
    try:
        # Build headers - only add Authorization if API key exists
        headers = {'User-Agent': 'SurfLamp-Agent/1.0'}
        
        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key}'
            logger.info(f"Making API request with authentication")
        else:
            logger.info(f"Making API request without authentication (public endpoint)")
        
        logger.info(f"Headers: {headers}")
        
        # Make the actual API call
        response = requests.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"API call successful: {response.status_code}")
        logger.debug(f"Raw response: {response.text[:200]}...")
        
        # Parse JSON response
        raw_data = response.json()
        
        # Standardize using endpoint configuration
        surf_data = standardize_surf_data(raw_data, endpoint)
        
        if surf_data:
            logger.info(f"Surf data standardized successfully")
            return surf_data
        else:
            logger.error(f"Failed to standardize surf data")
            return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed for {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed for {endpoint}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching surf data from {endpoint}: {e}")
        return None

def format_for_arduino(surf_data, format_type="meters"):
    """Format surf data for Arduino consumption"""
    logger.info(f"Formatting data for Arduino (format: {format_type})")
    
    formatted = surf_data.copy()
    
    # Convert units if needed
    if format_type == "feet":
        if surf_data.get("wave_height_m"):
            formatted["wave_height_ft"] = round(surf_data["wave_height_m"] * 3.28084, 2)
        if surf_data.get("wind_speed_mps"):
            formatted["wind_speed_mph"] = round(surf_data["wind_speed_mps"] * 2.237, 2)
        logger.info(f"Converted to imperial: {formatted.get('wave_height_ft', 0)}ft waves, {formatted.get('wind_speed_mph', 0)}mph wind")
    else:
        logger.info(f"Metric format: {formatted.get('wave_height_m', 0)}m waves, {formatted.get('wind_speed_mps', 0)}mps wind")
    
    return formatted

def send_to_arduino(arduino_id, surf_data, format_type="meters"):
    """Send surf data to Arduino device via configurable transport"""
    logger.info(f"Sending data to Arduino {arduino_id}...")
    
    try:
        # Get Arduino IP address
        arduino_ip = get_arduino_ip(arduino_id)
        if not arduino_ip:
            logger.warning(f"No IP address found for Arduino {arduino_id}")
            # In mock mode, we can still simulate with a placeholder IP
            if os.environ.get('ARDUINO_TRANSPORT', 'http').lower() == 'mock':
                arduino_ip = "192.168.1.100"  # Placeholder for mock demonstration
                logger.info(f"Using placeholder IP for mock: {arduino_ip}")
            else:
                return False
        
        # Format data based on user preferences
        formatted_data = format_for_arduino(surf_data, format_type)
        headers = {'Content-Type': 'application/json'}
        
        # Use transport abstraction
        success, status_code, response_text = arduino_transport.send_data(
            arduino_id, arduino_ip, formatted_data, headers
        )
        
        if success:
            logger.info(f"Successfully sent data to Arduino {arduino_id}")
            return True
        else:
            logger.warning(f"Arduino {arduino_id} returned status {status_code}: {response_text}")
            return False
            
    except Exception as e:
        logger.warning(f"Error sending to Arduino {arduino_id}: {e}")
        return False

def update_lamp_timestamp(lamp_id):
    """Update lamp's last_updated timestamp"""
    logger.info(f"Updating timestamp for lamp {lamp_id}")
    
    query = text("""
        UPDATE lamps 
        SET last_updated = CURRENT_TIMESTAMP 
        WHERE lamp_id = :lamp_id
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"lamp_id": lamp_id})
            conn.commit()
            
        logger.info(f"Timestamp updated for lamp {lamp_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update timestamp for lamp {lamp_id}: {e}")
        return False

def update_current_conditions(lamp_id, surf_data):
    """Update current_conditions table with latest surf data"""
    logger.info(f"Updating current conditions for lamp {lamp_id}")
    
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
            
        logger.info(f"Current conditions updated for lamp {lamp_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update current conditions for lamp {lamp_id}: {e}")
        return False

def process_single_lamp_arduino_update(lamp_id, lamp_config, combined_data):
    """
    Process a single lamp's Arduino update and database operations.
    This function runs in a separate thread for each lamp.
    
    Args:
        lamp_id: Unique lamp identifier
        lamp_config: Configuration dict containing arduino_id, format, etc.
        combined_data: Surf data to send to Arduino
        
    Returns:
        tuple: (lamp_id, arduino_success, db_success)
    """
    logger.info(f"Thread processing lamp {lamp_id}")
    
    try:
        # Always update database first (ensures dashboard data even if Arduino fails)
        timestamp_updated = update_lamp_timestamp(lamp_id)
        conditions_updated = update_current_conditions(lamp_id, combined_data)
        db_success = timestamp_updated and conditions_updated
        
        if db_success:
            logger.info(f"Database updated successfully for lamp {lamp_id}")
        else:
            logger.warning(f"Database update failed for lamp {lamp_id}")
        
        # Attempt Arduino communication
        arduino_success = send_to_arduino(
            lamp_config['arduino_id'], 
            combined_data, 
            lamp_config['format']
        )
        
        if arduino_success:
            logger.info(f"Arduino {lamp_config['arduino_id']} updated successfully")
        else:
            logger.warning(f"Arduino {lamp_config['arduino_id']} update failed")
        
        return lamp_id, arduino_success, db_success
        
    except Exception as e:
        logger.error(f"Thread error processing lamp {lamp_id}: {e}")
        return lamp_id, False, False

def process_arduino_updates_threaded(lamps_with_data, max_workers=50):
    """
    Process Arduino updates for multiple lamps using threading.
    
    Args:
        lamps_with_data: List of tuples (lamp_id, lamp_config, combined_data)
        max_workers: Maximum number of concurrent threads
        
    Returns:
        tuple: (successful_db_updates, successful_arduino_updates, failed_updates)
    """
    logger.info(f"Starting threaded Arduino processing for {len(lamps_with_data)} lamps")
    logger.info(f"Using ThreadPoolExecutor with max_workers={max_workers}")
    
    successful_db_updates = 0
    successful_arduino_updates = 0
    failed_updates = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all lamp processing tasks to the thread pool
        future_to_lamp = {
            executor.submit(
                process_single_lamp_arduino_update, 
                lamp_id, 
                lamp_config, 
                combined_data
            ): lamp_id
            for lamp_id, lamp_config, combined_data in lamps_with_data
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_lamp):
            lamp_id = future_to_lamp[future]
            
            try:
                # Wait for thread completion with timeout
                lamp_id_result, arduino_success, db_success = future.result(timeout=15)
                
                # Count successes and failures
                if db_success:
                    successful_db_updates += 1
                if arduino_success:
                    successful_arduino_updates += 1
                if not arduino_success or not db_success:
                    failed_updates += 1
                    
                logger.info(f"Completed lamp {lamp_id_result}: DB={db_success}, Arduino={arduino_success}")
                
            except Exception as e:
                logger.error(f"Thread exception for lamp {lamp_id}: {e}")
                failed_updates += 1
    
    logger.info(f"Threaded processing complete: DB={successful_db_updates}, Arduino={successful_arduino_updates}, Failed={failed_updates}")
    return successful_db_updates, successful_arduino_updates, failed_updates

def process_all_lamps():
    """Main processing function with threaded Arduino communication"""
    logger.info("======= STARTING LAMP PROCESSING CYCLE =======")
    start_time = time.time()
    
    try:
        # Step 1: Test database connection
        if not test_database_connection():
            logger.error("Database connection failed, aborting cycle")
            return False
        
        # Step 2: Get lamp configurations (grouped by lamp_id)
        lamp_configs = get_lamp_api_configs()
        if not lamp_configs:
            logger.error("No lamp configurations found, aborting cycle")
            return False
        
        logger.info(f"Processing {len(lamp_configs)} lamps with multi-source APIs...")
        
        # Step 3: Fetch API data for each lamp (sequential, as before)
        lamps_with_data = []
        
        for lamp_id, lamp_config in lamp_configs.items():
            logger.info(f"Processing Lamp {lamp_id} ({lamp_config['location']})")
            logger.info(f"API sources: {len(lamp_config['endpoints'])}")
            
            # Fetch data from all API sources for this lamp
            combined_data = {}
            successful_fetches = 0
            
            for endpoint in lamp_config['endpoints']:
                logger.info(f"Fetching from priority {endpoint['priority']} API...")
                
                try:
                    source_data = fetch_surf_data(
                        endpoint['api_key'], 
                        endpoint['http_endpoint']
                    )
                    
                    if source_data:
                        # Merge data from this source
                        combined_data.update(source_data)
                        successful_fetches += 1
                        logger.info(f"Priority {endpoint['priority']} API successful")
                    else:
                        logger.warning(f"Priority {endpoint['priority']} API returned no data")
                        
                except Exception as e:
                    logger.warning(f"Priority {endpoint['priority']} API failed: {e}")
            
            # Add lamp to processing queue if we got any data
            if combined_data and successful_fetches > 0:
                logger.info(f"Combined data from {successful_fetches}/{len(lamp_config['endpoints'])} sources")
                lamps_with_data.append((lamp_id, lamp_config, combined_data))
            else:
                logger.error(f"No usable data for lamp {lamp_id} - all API sources failed")
        
        # Step 4: Process Arduino updates using threading
        if lamps_with_data:
            api_fetch_time = time.time() - start_time
            logger.info(f"API fetch phase completed in {api_fetch_time:.1f} seconds")
            logger.info(f"Starting threaded Arduino processing for {len(lamps_with_data)} lamps...")
            
            # Thread pool size calculation: reasonable limit based on network capacity
            max_workers = min(50, len(lamps_with_data))  # Don't exceed lamp count
            
            successful_db_updates, successful_arduino_updates, failed_updates = process_arduino_updates_threaded(
                lamps_with_data, 
                max_workers=max_workers
            )
        else:
            successful_db_updates = successful_arduino_updates = failed_updates = 0
            logger.error("No lamps had usable data for processing")
        
        # Final summary
        end_time = time.time()
        total_duration = round(end_time - start_time, 2)
        arduino_duration = round(end_time - start_time - api_fetch_time, 2) if lamps_with_data else 0
        
        logger.info(f"======= LAMP PROCESSING CYCLE COMPLETED =======")
        logger.info(f"Summary:")
        logger.info(f"  - Total lamps: {len(lamp_configs)}")
        logger.info(f"  - Lamps with data: {len(lamps_with_data)}")
        logger.info(f"  - Database updates: {successful_db_updates}")
        logger.info(f"  - Arduino updates: {successful_arduino_updates}")
        logger.info(f"  - Failed updates: {failed_updates}")
        logger.info(f"  - API fetch time: {api_fetch_time:.1f} seconds")
        logger.info(f"  - Arduino comm time: {arduino_duration:.1f} seconds")
        logger.info(f"  - Total duration: {total_duration} seconds")
        logger.info(f"  - Status: {'SUCCESS' if successful_db_updates > 0 else 'FAILED'}")
        
        return successful_db_updates > 0
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in lamp processing cycle: {e}")
        return False

def run_once():
    """Run processing once for testing"""
    logger.info("Running single test cycle...")
    return process_all_lamps()

def main():
    """Main function - choose test mode or continuous mode"""
    logger.info("Starting Surf Lamp Background Processor...")
    
    # Check if we're in test mode
    test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
    
    if test_mode:
        logger.info("TEST MODE: Running once and exiting")
        success = run_once()
        exit(0 if success else 1)
    
    else:
        logger.info("PRODUCTION MODE: Running continuously every 30 minutes")
        
        # Run once immediately for testing
        logger.info("Running initial cycle...")
        process_all_lamps()
        
        # Then schedule every 30 minutes
        import schedule
        schedule.every(30).minutes.do(process_all_lamps)
        
        logger.info("Scheduled to run every 30 minutes. Waiting...")
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
