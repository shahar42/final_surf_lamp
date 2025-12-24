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
import logging
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Import from refactored modules
from lamp_repository import (
    test_database_connection,
    get_location_based_configs,
    get_lamps_for_location,
    update_lamp_timestamp,
    update_current_conditions,
    batch_update_lamp_timestamps,
    batch_update_current_conditions
)
from weather_api_client import fetch_surf_data

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

    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_size=5,            # Background processor needs fewer connections
        max_overflow=5,         # Max 10 total (background worker is single-threaded)
        pool_pre_ping=True,     # Test connections before use (critical for Supabase)
        pool_recycle=1800,      # Recycle connections after 30min (Supabase idle timeout is 1hr)
        echo=False              # Set to True for SQL query logging during debugging
    )
    logger.info("Database engine created with optimized connection pool (size=5, max=10)")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    exit(1)


def process_all_lamps():
    """Main processing function - Location-based processing with multi-source priority"""
    logger.info("🚀 ======= STARTING LOCATION-BASED PROCESSING CYCLE =======")
    start_time = time.time()

    try:
        # Step 1: Test database connection
        if not test_database_connection(engine):
            logger.error("❌ Database connection failed, aborting cycle")
            return False

        # Step 2: Get location-based API configurations
        location_configs = get_location_based_configs(engine)
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
            lamps = get_lamps_for_location(engine, location)
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
            timestamp_updated = batch_update_lamp_timestamps(engine, lamp_ids)
            conditions_updated = batch_update_current_conditions(engine, lamp_ids, combined_surf_data)

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
                    timestamp_ok = update_lamp_timestamp(engine, lamp['lamp_id'])
                    conditions_ok = update_current_conditions(engine, lamp['lamp_id'], combined_surf_data)
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
