```python
import asyncio
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from logging.config import dictConfig
from app.api.v1 import api_router
from app.db import database
from app.services import surf_data_service

# Structured logging setup
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Surfboard Lamp Backend",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database connection and start background scheduler on application startup."""
    try:
        await database.connect()
        logger.info("Database connection established.")
        
        scheduler = AsyncIOScheduler()
        scheduler.add_job(surf_data_service.update_surf_data, 'interval', minutes=10)
        scheduler.start()
        logger.info("Background scheduler started.")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown the application, closing database connections."""
    try:
        await database.disconnect()
        logger.info("Database connection closed.")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint to verify the application is running."""
    return JSONResponse(content={"status": "healthy"}, status_code=status.HTTP_200_OK)
```