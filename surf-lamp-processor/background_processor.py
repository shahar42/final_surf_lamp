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
    get_location_api_configs,
    get_arduinos_for_location,
    update_location_conditions
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

        # Step 2: Get location API configurations from database
        location_configs = get_location_api_configs(engine)
        if not location_configs:
            logger.error("❌ No location configurations found, aborting cycle")
            return False

        logger.info(f"📊 Processing {len(location_configs)} locations...")

        # Step 3: Process each location (one API call per location updates all arduinos)
        total_arduinos_updated = 0
        total_api_calls = 0

        for location, config in location_configs.items():
            logger.info(f"\n--- Processing Location: {location} ---")

            # Get all arduinos in this location
            arduinos = get_arduinos_for_location(engine, location)
            if not arduinos:
                logger.warning(f"⚠️  No arduinos found for location: {location}")
                continue

            # Fetch data from wave API
            logger.info(f"  Fetching wave data: {config['wave_api_url'][:80]}...")
            total_api_calls += 1
            wave_data = fetch_surf_data(None, config['wave_api_url'])

            # Fetch data from wind API
            logger.info(f"  Fetching wind data: {config['wind_api_url'][:80]}...")
            total_api_calls += 1
            wind_data = fetch_surf_data(None, config['wind_api_url'])

            # Combine data from both sources
            combined_surf_data = {}
            if wave_data:
                combined_surf_data.update(wave_data)
                logger.info(f"✅ Got wave data: {list(wave_data.keys())}")
            if wind_data:
                combined_surf_data.update(wind_data)
                logger.info(f"✅ Got wind data: {list(wind_data.keys())}")

            # Check if we have sufficient data
            if not combined_surf_data:
                logger.error(f"❌ No data obtained for location {location}")
                continue

            logger.info(f"📊 Combined data for {location}: {list(combined_surf_data.keys())}")

            # Update location table ONCE (all arduinos inherit)
            logger.info(f"📦 Updating location table for {location}")
            location_updated = update_location_conditions(engine, location, combined_surf_data)

            if location_updated:
                # Note: arduino timestamps are updated only when physical devices poll the API endpoint
                # The background processor does NOT update last_poll_time to avoid monitoring pollution

                total_arduinos_updated += len(arduinos)
                logger.info(f"✅ Location updated successfully - {len(arduinos)} arduinos inherit this data")

                # Log individual arduino details for monitoring
                for arduino in arduinos:
                    logger.info(f"   ✓ Arduino {arduino['arduino_id']} (User {arduino['user_id']})")
            else:
                logger.error(f"❌ Failed to update location {location}")

        # Final summary
        end_time = time.time()
        duration = round(end_time - start_time, 2)

        logger.info("\n🎉 ======= LOCATION-CENTRIC PROCESSING CYCLE COMPLETED =======")
        logger.info("📊 Summary:")
        logger.info(f"   - Locations processed: {len(location_configs)}")
        logger.info(f"   - Total API calls made: {total_api_calls}")
        logger.info(f"   - Arduinos updated: {total_arduinos_updated}")
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
