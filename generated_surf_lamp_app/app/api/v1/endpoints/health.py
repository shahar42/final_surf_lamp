```python
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", status_code=200)
async def health_check() -> dict:
    """
    Endpoint to check the health status of the application.

    Returns:
        dict: A dictionary containing the health status.
    """
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

@router.get("/ready", status_code=200)
async def readiness_check() -> dict:
    """
    Endpoint to check if the application is ready to receive requests.
    This includes checking the database connection.

    Returns:
        dict: A dictionary containing the readiness status.

    Raises:
        HTTPException: If the database connection fails.
    """
    logger.info("Readiness check endpoint called")
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection successful")
        return {"status": "ready"}
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")
```