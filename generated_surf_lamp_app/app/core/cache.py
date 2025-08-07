```python
import json
from typing import Any, Dict, Optional

import redis.asyncio as redis
from loguru import logger

class CacheManager:
    """Manages caching operations using Redis for surf data."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize the CacheManager with a Redis client.

        Args:
            redis_client (redis.Redis): An instance of the Redis client.
        """
        self.redis_client = redis_client

    async def get_surf_data_cache(self, location_index: str) -> Optional[Dict[str, Any]]:
        """Retrieve surf data from the cache.

        Args:
            location_index (str): The index of the location to retrieve data for.

        Returns:
            Optional[Dict[str, Any]]: The cached surf data if found, None otherwise.
        """
        cache_key = f"surf_data:{location_index}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for location: {location_index}")
            return json.loads(cached_data)
        else:
            logger.info(f"Cache miss for location: {location_index}")
            return None

    async def set_surf_data_cache(self, location_index: str, data: Dict[str, Any]) -> None:
        """Set surf data in the cache with a TTL of 30 minutes.

        Args:
            location_index (str): The index of the location to cache data for.
            data (Dict[str, Any]): The surf data to cache.
        """
        cache_key = f"surf_data:{location_index}"
        try:
            await self.redis_client.set(cache_key, json.dumps(data), ex=1800)
            logger.info(f"Cached surf data for location: {location_index}")
        except Exception as e:
            logger.error(f"Failed to cache surf data for location {location_index}: {str(e)}")
```