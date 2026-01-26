# background_processor.py
"""
Background service for Surf Lamp processing
Fetches surf data from APIs and updates database with current surf conditions.
"""

import os
import sys
import signal
import time
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Import from refactored modules
from lamp_repository import (
    test_database_connection,
    get_location_api_configs,
    get_arduinos_for_location,
    update_location_conditions,
    update_processor_heartbeat
)
from weather_api_client import fetch_surf_data

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('lamp_processor.log', maxBytes=5*1024*1024, backupCount=1),
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
        pool_size=5,            
        max_overflow=5,         
        pool_pre_ping=True,     
        pool_recycle=1800,      
        echo=False              
    )
    logger.info("Database engine created")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    exit(1)


def cleanup_handler(sig, frame):
    """Signal handler for graceful shutdown"""
    logger.info(f"🛑 Received signal {sig}, shutting down...")
    engine.dispose()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, cleanup_handler)
signal.signal(signal.SIGINT, cleanup_handler)


def process_all_lamps():
    """Main processing function - Location-based processing"""
    logger.info("🚀 Starting processing cycle")
    start_time = time.time()

    try:
        if not test_database_connection(engine):
            logger.error("❌ Database connection failed")
            return False

        location_configs = get_location_api_configs(engine)
        if not location_configs:
            logger.error("❌ No location configurations found")
            return False

        logger.info(f"📊 Processing {len(location_configs)} locations...")

        total_arduinos_updated = 0
        total_api_calls = 0

        for location, config in location_configs.items():
            logger.info(f"Processing Location: {location}")

            arduinos = get_arduinos_for_location(engine, location)
            if not arduinos:
                logger.warning(f"⚠️  No arduinos found for location: {location}")
                continue

            # Fetch data from APIs
            total_api_calls += 2
            wave_data = fetch_surf_data(None, config['wave_api_url'])
            wind_data = fetch_surf_data(None, config['wind_api_url'], config['wave_calculation_method'])

            # Combine data
            combined_surf_data = {}
            if wave_data: combined_surf_data.update(wave_data)
            if wind_data: combined_surf_data.update(wind_data)

            if not combined_surf_data:
                logger.error(f"❌ No data obtained for location {location}")
                continue

            # Update location table
            location_updated = update_location_conditions(engine, location, combined_surf_data)

            if location_updated:
                total_arduinos_updated += len(arduinos)
                logger.info(f"✅ Location updated successfully - {len(arduinos)} arduinos updated")
            else:
                logger.error(f"❌ Failed to update location {location}")

        duration = round(time.time() - start_time, 2)
        logger.info(f"Cycle completed in {duration}s. Updated {total_arduinos_updated} arduinos.")
        return True

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        logger.error(f"💥 Critical error in processing cycle: {e}")
        return False


def main():
    """Main entry point"""
    logger.info("Starting Background Processor...")

    test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'

    if test_mode:
        logger.info("TEST MODE: Running once")
        success = process_all_lamps()
        exit(0 if success else 1)

    else:
        logger.info("PRODUCTION MODE: Running every 15 minutes")
        try:
            # Run once immediately
            process_all_lamps()

            import schedule
            schedule.every(15).minutes.do(process_all_lamps)

            heartbeat_counter = 0
            while True:
                schedule.run_pending()
                time.sleep(60)

                # Heartbeat every minute - write to database (Watchdog pattern)
                heartbeat_counter += 1
                update_processor_heartbeat(engine)
                if heartbeat_counter % 5 == 0:
                    logger.info(f"💓 Heartbeat: Process alive, waiting for next cycle...")

        finally:
            logger.info("Cleaning up database connections...")
            engine.dispose()


if __name__ == "__main__":
    main()