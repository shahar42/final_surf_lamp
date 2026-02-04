import os
import redis
import logging

logger = logging.getLogger(__name__)

# Global Redis client
redis_client = None

def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            try:
                redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("✅ Redis client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Redis client: {e}")
                redis_client = None
        else:
            logger.warning("⚠️ REDIS_URL not set. Redis features will be disabled.")
    return redis_client
