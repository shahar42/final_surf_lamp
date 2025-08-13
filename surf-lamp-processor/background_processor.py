# background_processor.py
"""
Background service for Surf Lamp processing
- Fetches surf data from APIs
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
    
    # First, check if arduino_ip column exists in lamps table
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
                logger.warning("   You may need to add 'arduino_ip' column to lamps table")
                logger.warning("   ALTER TABLE lamps ADD COLUMN arduino_ip VARCHAR(15);")
                logger.warning("   UPDATE lamps SET arduino_ip = '192.168.1.100' WHERE arduino_id = 1001;")
                return None
                
    except Exception as e:
        logger.error(f"❌ Database error looking up Arduino IP: {e}")
        logger.error(f"   This might mean arduino_ip column doesn't exist yet")
        return None

def fetch_surf_data(api_key, endpoint):
    """Fetch surf data from external API"""
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
        
        # For testing, let's simulate API response
        # Comment out this simulation and uncomment requests.get() for real API
        logger.info("⚠️  SIMULATING API RESPONSE (for testing)")
        
        # Simulated surf data
        surf_data = {
            "wave_height_m": 1.8,
            "wave_period_s": 9.2,
            "wind_speed_mps": 8.5,
            "wind_direction_deg": 225,
            "location": "Test Location",
            "timestamp": int(time.time())
        }
        
        logger.info(f"✅ Surf data received: {json.dumps(surf_data, indent=2)}")
        return surf_data
        
        # Real API call (uncomment when ready):
        # response = requests.get(endpoint, headers=headers, timeout=30)
        # response.raise_for_status()
        # raw_data = response.json()
        # surf_data = standardize_surf_data(raw_data)
        # logger.info(f"✅ Surf data fetched: {surf_data}")
        # return surf_data
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch surf data from {endpoint}: {e}")
        return None

def format_for_arduino(surf_data, format_type="meters"):
    """Format surf data for Arduino consumption"""
    logger.info(f"🔧 Formatting data for Arduino (format: {format_type})")
    
    formatted = surf_data.copy()
    
    # Convert units if needed
    if format_type == "feet":
        formatted["wave_height_ft"] = round(surf_data["wave_height_m"] * 3.28084, 2)
        formatted["wind_speed_mph"] = round(surf_data["wind_speed_mps"] * 2.237, 2)
        logger.info(f"   Converted to imperial: {formatted['wave_height_ft']}ft waves, {formatted['wind_speed_mph']}mph wind")
    else:
        logger.info(f"   Metric format: {formatted['wave_height_m']}m waves, {formatted['wind_speed_mps']}mps wind")
    
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
        
        # For testing, let's simulate the Arduino call
        logger.info("⚠️  SIMULATING ARDUINO HTTP POST (for testing)")
        logger.info("✅ Arduino responded: {'status': 'ok'} (simulated)")
        return True
        
        # Real Arduino call (uncomment when ready):
        # response = requests.post(
        #     arduino_url, 
        #     json=formatted_data, 
        #     headers=headers,
        #     timeout=10
        # )
        # 
        # logger.info(f"📥 Arduino response status: {response.status_code}")
        # logger.info(f"📥 Arduino response body: {response.text}")
        # 
        # if response.status_code == 200:
        #     logger.info(f"✅ Successfully sent data to Arduino {arduino_id}")
        #     return True
        # else:
        #     logger.error(f"❌ Arduino {arduino_id} returned status {response.status_code}")
        #     return False
            
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

def process_all_lamps():
    """Main processing function - complete loop with full logging"""
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
                config['http_endpoint'],
                config['usage_id']
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
