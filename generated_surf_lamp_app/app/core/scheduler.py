```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import List
import asyncio

from app.core.database import DatabaseManagementTool
from app.core.api import APIDataRetrievalTool
from app.core.cache import CacheManager
from app.logging import logger


class SurfDataScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db_tool = DatabaseManagementTool()
        self.api_tool = APIDataRetrievalTool()
        self.cache_manager = CacheManager()

    async def start(self):
        """Start the scheduler."""
        self.scheduler.add_job(
            self._update_cache_for_all_locations,
            'interval',
            minutes=30,
            max_instances=1,
            coalesce=True
        )
        self.scheduler.start()
        logger.info("SurfDataScheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("SurfDataScheduler stopped")

    async def _update_cache_for_all_locations(self):
        """Update cache for all active locations every 30 minutes."""
        try:
            active_locations: List[str] = await self.db_tool.get_active_locations()
            for location in active_locations:
                surf_data = await self.api_tool.fetch_surf_data(location)
                await self.cache_manager.update_cache(location, surf_data)
                logger.info(f"Updated cache for location: {location}")
        except Exception as e:
            logger.error(f"Error updating cache for all locations: {str(e)}")


async def main():
    scheduler = SurfDataScheduler()
    await scheduler.start()
    # Keep the event loop running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
```