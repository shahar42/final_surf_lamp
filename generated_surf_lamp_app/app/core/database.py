```python
import asyncpg
from fastapi import Depends, FastAPI
from typing import AsyncGenerator
import logging
from app.core import settings

logger = logging.getLogger(__name__)

async def init_db(app: FastAPI) -> None:
    """
    Initialize the database connection pool when the application starts.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    try:
        app.state.pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size
        )
        logger.info("Database connection pool initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database connection pool: {str(e)}")
        raise

async def get_db_pool(app: FastAPI = Depends(init_db)) -> AsyncGenerator[asyncpg.Pool, None]:
    """
    Dependency function to get the database connection pool.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        AsyncGenerator[asyncpg.Pool, None]: An async generator yielding the database connection pool.
    """
    try:
        yield app.state.pool
    except Exception as e:
        logger.error(f"Error occurred while using database connection pool: {str(e)}")
        raise

async def close_db(app: FastAPI) -> None:
    """
    Close the database connection pool when the application shuts down.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    try:
        await app.state.pool.close()
        logger.info("Database connection pool closed successfully.")
    except Exception as e:
        logger.error(f"Failed to close database connection pool: {str(e)}")

def setup_db(app: FastAPI) -> None:
    """
    Set up database event handlers for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    @app.on_event("startup")
    async def startup_event():
        await init_db(app)

    @app.on_event("shutdown")
    async def shutdown_event():
        await close_db(app)
```