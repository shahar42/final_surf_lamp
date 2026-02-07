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
    get_arduinos_for_location,
    update_location_conditions,
    update_processor_heartbeat
)
from weather_api_client import fetch_surf_data_with_fallback
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared_config import get_api_sources_for_location, get_wave_calculation_method, MULTI_SOURCE_LOCATIONS

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


def is_data_identical(old_data, new_data):
    """Check if surf data is essentially identical"""
    if not old_data:
        return False
        
    fields = ['wave_height_m', 'wave_period_s', 'wind_speed_mps', 'wind_direction_deg']
    for field in fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        
        # If both are None, they match
        if old_val is None and new_val is None:
            continue
        # If one is None, they don't match
        if old_val is None or new_val is None:
            return False
            
        # Float comparison with small tolerance
        try:
            if abs(float(old_val) - float(new_val)) > 0.001:
                return False
        except (ValueError, TypeError):
            return False
            
    return True


def process_all_lamps():
    """Main processing function - Location-based processing"""
    logger.info("🚀 Starting processing cycle")
    start_time = time.time()

    try:
        if not test_database_connection(engine):
            logger.error("❌ Database connection failed")
            return False

        # Get all locations with active arduinos (optimized for 10K+ scale)
        from lamp_repository import get_active_locations
        active_locations = get_active_locations(engine)

        if not active_locations:
            logger.error("❌ No active locations found")
            return False

        logger.info(f"📊 Processing {len(active_locations)} locations...")

        total_arduinos_updated = 0
        total_api_calls = 0

        for location in active_locations:
            logger.info(f"Processing Location: {location}")

            arduinos = get_arduinos_for_location(engine, location)
            if not arduinos:
                logger.warning(f"⚠️  No arduinos found for location: {location}")
                continue

            # Get API sources with priority fallback from shared config
            api_sources = get_api_sources_for_location(location)
            wave_calculation_method = get_wave_calculation_method(location)

            # Fetch data from APIs with fallback
            total_api_calls += 2
            wave_data = fetch_surf_data_with_fallback(None, api_sources['wave'], wave_calculation_method)

            # Only use wave_calculation_method for wind if location is explicitly set to 'formula' (Eilat only)
            use_wind_calculation = wave_calculation_method == 'formula'
            wind_data = fetch_surf_data_with_fallback(None, api_sources['wind'], wave_calculation_method='formula' if use_wind_calculation else 'api')

            # Combine data - for non-formula locations, wind-based wave calculation is NOT a fallback
            combined_surf_data = {}
            if wave_data:
                combined_surf_data.update(wave_data)
            if wind_data:
                # Only use wind data if it contains actual wind values or if location uses formula method
                if use_wind_calculation:
                    combined_surf_data.update(wind_data)
                else:
                    # For API-based locations, only keep wind values, never wind-calculated waves
                    combined_surf_data['wind_speed_mps'] = wind_data.get('wind_speed_mps')
                    combined_surf_data['wind_direction_deg'] = wind_data.get('wind_direction_deg')

            if not combined_surf_data or not wave_data:
                logger.error(f"❌ No wave data obtained for location {location} (all wave endpoints failed)")
                continue

            # Check for staleness - get current values from database
            from lamp_repository import get_current_location_values
            old_data = get_current_location_values(engine, location)
            current_consecutive = old_data.get('consecutive_identical_updates', 0) if old_data else 0
            
            is_identical = is_data_identical(old_data, combined_surf_data)
            
            new_consecutive = current_consecutive + 1 if is_identical else 0
            should_update_timestamp = not is_identical
            
            if is_identical:
                 logger.warning(f"⚠️  Data is identical to previous fetch (Count: {new_consecutive})")

            # Update location table
            location_updated = update_location_conditions(
                engine, 
                location, 
                combined_surf_data, 
                consecutive_identical_updates=new_consecutive, 
                update_timestamp=should_update_timestamp
            )

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


def sync_redis_to_database():
    """Sync Arduino timestamps from Redis to Database (every 5 minutes)."""
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_and_database'))

    try:
        from redis_manager import get_redis_client, record_redis_health
        redis = get_redis_client()

        if not redis:
            logger.warning("Redis unavailable for sync task")
            return False

        # Fetch all Arduino timestamps from Redis
        redis_timestamps = redis.hgetall('arduino:last_seen')

        if not redis_timestamps:
            logger.info("No Redis timestamps to sync")
            return True

        # Convert string timestamps to datetime objects
        arduino_timestamps = {}
        for arduino_id_str, timestamp_str in redis_timestamps.items():
            try:
                arduino_id = int(arduino_id_str)
                timestamp = datetime.fromtimestamp(float(timestamp_str), timezone.utc)
                arduino_timestamps[arduino_id] = timestamp
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid timestamp for Arduino {arduino_id_str}: {e}")

        if not arduino_timestamps:
            logger.info("No valid timestamps to sync")
            return True

        # Batch update database using bulk UPDATE
        from lamp_repository import SessionLocal
        from datetime import datetime, timezone
        from sqlalchemy import text

        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from shared_config import REDIS_SYNC_BATCH_SIZE

        db = SessionLocal()
        try:
            total_updated = 0

            # Process in batches to prevent memory issues with 10K+ Arduinos
            arduino_items = list(arduino_timestamps.items())
            batch_size = REDIS_SYNC_BATCH_SIZE

            for i in range(0, len(arduino_items), batch_size):
                batch = arduino_items[i:i + batch_size]

                # Build VALUES clause for bulk update
                # Format: (arduino_id, 'timestamp_iso')
                values = []
                for arduino_id, timestamp in batch:
                    # Escape single quotes in timestamp to prevent SQL injection
                    ts_iso = timestamp.isoformat().replace("'", "''")
                    values.append(f"({arduino_id}, '{ts_iso}')")

                if not values:
                    continue

                values_clause = ', '.join(values)

                # Single UPDATE query for entire batch
                # Only updates if new timestamp is newer than existing
                query = text(f"""
                    UPDATE arduinos AS a
                    SET last_poll_time = v.ts::timestamptz
                    FROM (VALUES {values_clause}) AS v(id, ts)
                    WHERE a.arduino_id = v.id::integer
                      AND (a.last_poll_time IS NULL OR v.ts::timestamptz > a.last_poll_time)
                """)

                result = db.execute(query)
                total_updated += result.rowcount
                db.commit()

                logger.debug(f"Batch {i//batch_size + 1}: Updated {result.rowcount}/{len(batch)} Arduinos")

            logger.info(f"✅ Synced {total_updated}/{len(arduino_timestamps)} Arduino timestamps to DB in {(len(arduino_items) + batch_size - 1) // batch_size} batches")
            record_redis_health('background-processor', success=True)
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Batch sync failed: {e}")
            record_redis_health('background-processor', success=False, error_message=str(e))
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Redis sync failed: {e}")
        try:
            from redis_manager import record_redis_health
            record_redis_health('background-processor', success=False, error_message=str(e))
        except:
            pass
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

        # WATCHDOG TEST: Simulate hang if env var is set
        simulate_hang = os.environ.get('SIMULATE_HANG', 'false').lower() == 'true'
        if simulate_hang:
            logger.warning("🧪 WATCHDOG TEST MODE: Will hang after first cycle")

        try:
            # Run once immediately
            process_all_lamps()

            # HANG BOMB: Simulate a deadlock/infinite loop for watchdog testing
            if simulate_hang:
                logger.error("💣 SIMULATING HANG: Entering infinite loop (process alive, heartbeat frozen)")
                logger.error("💣 Watchdog should detect this and restart the service in ~9 minutes")
                while True:
                    time.sleep(3600)  # Sleep forever, simulating a hung process

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
                    # Redis-to-DB sync every 5 minutes
                    logger.info("⏰ Running Redis-to-Database sync task")
                    sync_redis_to_database()

        finally:
            logger.info("Cleaning up database connections...")
            engine.dispose()


if __name__ == "__main__":
    main()