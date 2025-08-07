```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging

from app.tools.user_input_processing import UserInputProcessingTool

logger = logging.getLogger(__name__)

router = APIRouter()

class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    lamp_id: str
    location: str

@router.post("/api/v1/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistration):
    """
    Register a new user with the provided data.

    Args:
        user_data (UserRegistration): The user registration data.

    Returns:
        dict: A dictionary containing a success message.

    Raises:
        HTTPException: If user registration fails.
    """
    try:
        processor = UserInputProcessingTool()
        result = await processor.process_user_registration(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password,
            lamp_id=user_data.lamp_id,
            location=user_data.location
        )
        
        if result["success"]:
            logger.info(f"User registered successfully: {user_data.email}")
            return {"message": "User registered successfully"}
        else:
            logger.error(f"User registration failed: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        logger.error(f"An error occurred during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )
```