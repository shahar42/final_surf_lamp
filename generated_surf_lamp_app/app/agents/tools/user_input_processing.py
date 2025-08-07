```python
import re
from typing import Dict, Any
import logging

from app.agents.tools.password_hasher import PasswordHasher
from app.agents.tools.database_management import DatabaseManagementTool

logger = logging.getLogger(__name__)

class UserInputProcessingTool:
    """
    A tool for processing user input, particularly for registration purposes.
    It validates input data, hashes passwords, and prepares data for database storage.
    """

    @staticmethod
    async def process_registration(registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user registration data.

        Args:
            registration_data (Dict[str, Any]): A dictionary containing user registration data.

        Returns:
            Dict[str, Any]: Processed and validated user data ready for database insertion.

        Raises:
            ValueError: If the input data fails validation.
        """
        try:
            # Validate email format
            email = registration_data.get('email')
            if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                raise ValueError("Invalid email format")

            # Validate password strength
            password = registration_data.get('password')
            if not password or len(password) < 8 or not re.search(r"\d", password):
                raise ValueError("Password must be at least 8 characters long and contain a number")

            # Hash the password
            hashed_password = await PasswordHasher.hash_password(password)

            # Convert location to index
            location = registration_data.get('location')
            location_index = await UserInputProcessingTool._convert_location_to_index(location)

            # Prepare data for database
            processed_data = {
                'email': email,
                'password': hashed_password,
                'location': location_index,
                'username': registration_data.get('username', '')
            }

            # Delegate database operations
            db_tool = DatabaseManagementTool()
            await db_tool.insert_user(processed_data)

            logger.info("User registration processed successfully")
            return processed_data

        except ValueError as ve:
            logger.error(f"Validation error during registration: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during registration processing: {str(e)}")
            raise

    @staticmethod
    async def _convert_location_to_index(location: str) -> int:
        """
        Convert a location name to its corresponding index.

        Args:
            location (str): The name of the location.

        Returns:
            int: The index corresponding to the location.

        Raises:
            ValueError: If the location is not recognized.
        """
        location_map = {
            'New York': 0,
            'Los Angeles': 1,
            'Chicago': 2,
            'Houston': 3,
            'Phoenix': 4
        }
        if location not in location_map:
            raise ValueError(f"Unrecognized location: {location}")
        return location_map[location]
```