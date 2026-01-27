#!/usr/bin/env python3
"""
Processor Watchdog Monitor
Monitors the background processor heartbeat and restarts it if hung.
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Watchdog Configuration
T_INTERVAL = 120  # Check every 2 minutes
MAX_MISSED_PINGS = 3  # Allow 3 missed heartbeats (6 minutes total)
MAX_REVIVES = 3  # Maximum restart attempts
SERVICE_NAME = 'surf-lamp-processor'

# Render API Configuration
RENDER_API_KEY = os.environ.get('RENDER_API_KEY')
RENDER_SERVICE_ID = os.environ.get('RENDER_PROCESSOR_SERVICE_ID')

# Database
DATABASE_URL = os.environ.get('DATABASE_URL')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_heartbeat_staleness(engine):
    """
    Check if processor heartbeat is stale.

    Returns:
        dict: {'is_stale': bool, 'last_alive': datetime, 'seconds_since': int, 'missed_count': int, 'revive_count': int}
    """
    query = text("""
        SELECT
            last_alive_timestamp,
            missed_count,
            revive_count,
            max_revives,
            EXTRACT(EPOCH FROM (NOW() - last_alive_timestamp))::INTEGER as seconds_since_last_alive
        FROM processor_heartbeat
        WHERE service_name = :service_name
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"service_name": SERVICE_NAME})
            row = result.fetchone()

            if not row:
                logger.error(f"❌ No heartbeat record found for {SERVICE_NAME}")
                return None

            # Processor writes heartbeat every 60s, we check every 120s
            # Stale if no update in last 180s (3 minutes)
            staleness_threshold = 180
            is_stale = row.seconds_since_last_alive > staleness_threshold

            return {
                'is_stale': is_stale,
                'last_alive': row.last_alive_timestamp,
                'seconds_since': row.seconds_since_last_alive,
                'missed_count': row.missed_count,
                'revive_count': row.revive_count,
                'max_revives': row.max_revives
            }
    except Exception as e:
        logger.error(f"❌ Failed to check heartbeat: {e}")
        return None


def increment_missed_count(engine):
    """Increment missed_count in database"""
    query = text("""
        UPDATE processor_heartbeat
        SET missed_count = missed_count + 1,
            updated_at = NOW()
        WHERE service_name = :service_name
        RETURNING missed_count
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"service_name": SERVICE_NAME})
            conn.commit()
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"❌ Failed to increment missed count: {e}")
        return None


def increment_revive_count(engine):
    """Increment revive_count after restart"""
    query = text("""
        UPDATE processor_heartbeat
        SET revive_count = revive_count + 1,
            updated_at = NOW()
        WHERE service_name = :service_name
        RETURNING revive_count
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"service_name": SERVICE_NAME})
            conn.commit()
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"❌ Failed to increment revive count: {e}")
        return None


def reset_missed_count(engine):
    """Reset missed_count after successful revival"""
    query = text("""
        UPDATE processor_heartbeat
        SET missed_count = 0,
            updated_at = NOW()
        WHERE service_name = :service_name
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {"service_name": SERVICE_NAME})
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to reset missed count: {e}")
        return False


def restart_processor_service():
    """
    Restart the processor via Render API

    Returns:
        bool: True if restart triggered successfully
    """
    if not RENDER_SERVICE_ID:
        logger.error("❌ RENDER_PROCESSOR_SERVICE_ID not set in environment")
        return False

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys"
    headers = {
        'Authorization': f'Bearer {RENDER_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {'clearCache': 'do_not_clear'}

    try:
        logger.warning(f"🔄 Triggering Render restart for service {RENDER_SERVICE_ID}...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code in [200, 201]:
            logger.info(f"✅ Restart triggered successfully: {response.json()}")
            return True
        else:
            logger.error(f"❌ Restart failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to trigger restart: {e}")
        return False


def watchdog_check_cycle(engine):
    """Single watchdog check cycle"""
    status = check_heartbeat_staleness(engine)

    if not status:
        logger.error("❌ Failed to check heartbeat status")
        return False

    logger.info(f"📊 Heartbeat check: last_alive={status['last_alive']}, "
                f"seconds_since={status['seconds_since']}, "
                f"missed={status['missed_count']}, "
                f"revives={status['revive_count']}/{status['max_revives']}")

    if status['is_stale']:
        logger.warning(f"⚠️  Processor heartbeat is STALE (>{status['seconds_since']}s)")

        missed_count = increment_missed_count(engine)

        if missed_count is None:
            return False

        logger.warning(f"⚠️  Missed heartbeats: {missed_count}/{MAX_MISSED_PINGS}")

        if missed_count > MAX_MISSED_PINGS:
            if status['revive_count'] >= status['max_revives']:
                logger.error(f"❌ Max revive attempts reached ({status['max_revives']}). STOPPING WATCHDOG.")
                logger.error("❌ Manual intervention required - check processor logs!")
                return False

            logger.warning(f"🚨 CRITICAL: Missed {missed_count} heartbeats. Triggering restart...")

            if restart_processor_service():
                new_revive_count = increment_revive_count(engine)
                logger.info(f"✅ Restart triggered. Revive count: {new_revive_count}/{status['max_revives']}")
                reset_missed_count(engine)
                return True
            else:
                logger.error("❌ Failed to trigger restart")
                return False
    else:
        logger.info("✅ Processor heartbeat is healthy")

    return True


def main():
    """Main watchdog monitoring loop"""
    logger.info("🐕 Starting Processor Watchdog Monitor...")
    logger.info(f"   T_INTERVAL: {T_INTERVAL}s")
    logger.info(f"   MAX_MISSED_PINGS: {MAX_MISSED_PINGS}")
    logger.info(f"   MAX_REVIVES: {MAX_REVIVES}")

    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not set")
        sys.exit(1)

    if not RENDER_SERVICE_ID:
        logger.error("❌ RENDER_PROCESSOR_SERVICE_ID not set in environment")
        sys.exit(1)

    try:
        engine = create_engine(DATABASE_URL)
        logger.info("✅ Database engine created")

        while True:
            success = watchdog_check_cycle(engine)

            if not success:
                logger.error("❌ Watchdog check failed or max revives reached")
                logger.error("   Stopping watchdog - manual intervention required")
                break

            time.sleep(T_INTERVAL)

    except KeyboardInterrupt:
        logger.info("🛑 Watchdog stopped by user")
    except Exception as e:
        logger.error(f"💥 Watchdog crashed: {e}")
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.dispose()
            logger.info("🧹 Database connections closed")


if __name__ == "__main__":
    main()
