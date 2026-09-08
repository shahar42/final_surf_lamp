import os
import sys
import redis
import logging
import random
from datetime import datetime, timezone

# Import shared configuration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared_config import DB_FALLBACK_COOLDOWN_SECONDS, DB_FALLBACK_SAMPLING_RATE

logger = logging.getLogger(__name__)

# Global Redis client
redis_client = None

# Fail-fast limits for every Redis round trip (connect + per-command).
# Well under the lamp's 15s HTTP timeout so a Redis outage degrades to the
# uncached/DB path instead of stalling the whole request.
REDIS_CONNECT_TIMEOUT_SECONDS = 2
REDIS_SOCKET_TIMEOUT_SECONDS = 2

# Fallback: In-memory rate limiter (only used when Redis is completely unavailable)
# Structure: {arduino_id: last_db_write_timestamp}
_db_write_history_fallback = {}

def get_redis_client():
    """Get Redis client singleton."""
    global redis_client
    if redis_client is None:
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            try:
                # Bounded timeouts: an unreachable Redis must fail fast so the
                # except-blocks around every Redis call actually get to run.
                # Without these, each lamp request hangs on the OS TCP timeout
                # (60s+), far past the lamp's 15s HTTP timeout, and a Redis
                # blip turns into a fleet-wide "server unreachable".
                redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
                    socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                )
                logger.info("✅ Redis client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Redis client: {e}")
                redis_client = None
        else:
            logger.warning("⚠️ REDIS_URL not set. Redis features will be disabled.")
    return redis_client

def can_write_to_db(arduino_id):
    """
    Check if Arduino can write to database (distributed rate limiting).

    Uses Redis for rate limiting across multiple web service instances.
    Falls back to probabilistic sampling if Redis is unavailable.

    Args:
        arduino_id: Arduino ID to check

    Returns:
        bool: True if write is allowed, False if rate limited
    """
    redis = get_redis_client()

    if redis:
        try:
            # Redis-based rate limiting (atomic, works across all instances)
            key = f"db_fallback_cooldown:{arduino_id}"

            # Try to set key with cooldown expiry (NX = only if not exists)
            if redis.set(key, "1", ex=DB_FALLBACK_COOLDOWN_SECONDS, nx=True):
                return True  # Key didn't exist, write allowed

            return False  # Key exists, rate limited

        except Exception as e:
            logger.warning(f"Redis rate limit check failed for Arduino {arduino_id}: {e}")
            # Fall through to fallback logic

    # Fallback: Redis unavailable - use probabilistic sampling + in-memory rate limiter
    # This prevents complete DB overload during worst-case outages

    # First, apply random sampling (10% of requests get through)
    if random.random() > DB_FALLBACK_SAMPLING_RATE:
        return False

    # Second, check in-memory rate limiter (per-instance, imperfect but better than nothing)
    now = datetime.now(timezone.utc)
    last_write = _db_write_history_fallback.get(arduino_id)

    if last_write is None:
        return True

    elapsed = (now - last_write).total_seconds()
    return elapsed >= DB_FALLBACK_COOLDOWN_SECONDS

def record_db_write(arduino_id):
    """
    Record that a DB write occurred for this Arduino.

    Updates both Redis (if available) and in-memory fallback.

    Args:
        arduino_id: Arduino ID that was written
    """
    # This function rebinds the module-level dict during cleanup below, so
    # without this declaration Python treats every reference as a local and
    # the first access raises UnboundLocalError.
    global _db_write_history_fallback

    redis = get_redis_client()

    if redis:
        try:
            # Update Redis rate limiter
            key = f"db_fallback_cooldown:{arduino_id}"
            redis.setex(key, DB_FALLBACK_COOLDOWN_SECONDS, "1")
        except Exception as e:
            logger.warning(f"Failed to record DB write in Redis for Arduino {arduino_id}: {e}")

    # Always update fallback (cheap operation)
    _db_write_history_fallback[arduino_id] = datetime.now(timezone.utc)

    # Cleanup old entries from fallback dict (prevent memory leak)
    # More aggressive: check at 1000 entries, cap at 5000 max
    if len(_db_write_history_fallback) > 1000:
        # Remove entries older than 10 minutes
        cutoff_timestamp = datetime.now(timezone.utc).timestamp() - 600
        _db_write_history_fallback = {
            k: v for k, v in _db_write_history_fallback.items()
            if v.timestamp() > cutoff_timestamp
        }

        # If still too large after cleanup, keep only the most recent 5000
        if len(_db_write_history_fallback) > 5000:
            sorted_items = sorted(
                _db_write_history_fallback.items(),
                key=lambda x: x[1],
                reverse=True
            )
            _db_write_history_fallback = dict(sorted_items[:5000])
            logger.warning(f"⚠️ Fallback dict capped at 5000 entries (was {len(sorted_items)})")

def record_redis_health(service_name, success, error_message=None):
    """Record Redis health status to database."""
    from data_base import SessionLocal, RedisHealth
    from sqlalchemy.sql import func

    db = SessionLocal()
    try:
        health = db.query(RedisHealth).filter(RedisHealth.service_name == service_name).first()
        if not health:
            # Column defaults only apply at flush; set them now so the
            # `+= 1` below works on the very first failure record.
            health = RedisHealth(service_name=service_name, consecutive_failures=0, total_failures_24h=0)
            db.add(health)

        if success:
            health.last_success_timestamp = func.now()
            health.consecutive_failures = 0
            health.is_healthy = True
        else:
            health.last_failure_timestamp = func.now()
            health.consecutive_failures += 1
            health.total_failures_24h += 1
            health.is_healthy = health.consecutive_failures < 3

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record Redis health: {e}")
    finally:
        db.close()
