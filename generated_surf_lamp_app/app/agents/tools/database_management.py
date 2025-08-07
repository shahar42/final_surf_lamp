```python
import asyncio
from typing import Dict, Any, List, Optional
from aiopg import create_pool, Cursor
import json
import logging

logger = logging.getLogger(__name__)

class DatabaseManagementTool:
    """
    A tool for managing database operations related to lamp configurations and user registration.
    """

    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize the DatabaseManagementTool with database configuration.

        :param db_config: A dictionary containing database connection details.
        """
        self.db_config = db_config
        self.pool: Optional[asyncio.Pool] = None

    async def initialize(self):
        """
        Initialize the database connection pool.
        """
        try:
            self.pool = await create_pool(**self.db_config)
            logger.info("Database connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {str(e)}")
            raise

    async def close(self):
        """
        Close the database connection pool.
        """
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Database connection pool closed.")

    async def _execute_query(self, query: str, params: tuple = (), fetch: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a database query with transaction handling.

        :param query: SQL query to execute.
        :param params: Parameters for the query.
        :param fetch: Whether to fetch results.
        :return: List of dictionaries if fetch is True, None otherwise.
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, params)
                    if fetch:
                        return await cur.fetchall()
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Database query failed: {str(e)}")
                    raise

    async def get_lamp_configuration(self, lamp_id: int) -> Dict[str, Any]:
        """
        Retrieve the configuration for a specific lamp.

        :param lamp_id: The ID of the lamp.
        :return: A dictionary containing the lamp configuration.
        """
        query = "SELECT * FROM lamps WHERE id = %s"
        try:
            result = await self._execute_query(query, (lamp_id,), fetch=True)
            if result:
                return dict(result[0])
            else:
                logger.warning(f"No configuration found for lamp ID: {lamp_id}")
                return {}
        except Exception as e:
            logger.error(f"Failed to get lamp configuration for ID {lamp_id}: {str(e)}")
            raise

    async def register_new_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Register a new user in the database.

        :param user_data: A dictionary containing user data.
        :return: True if registration was successful, False otherwise.
        """
        query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
        params = (user_data['username'], user_data['email'], user_data['password'])
        try:
            await self._execute_query(query, params)
            logger.info(f"User {user_data['username']} registered successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to register user {user_data['username']}: {str(e)}")
            return False

    async def get_all_active_lamps(self) -> List[Dict[str, Any]]:
        """
        Retrieve all active lamps from the database.

        :return: A list of dictionaries containing active lamp data.
        """
        query = "SELECT * FROM lamps WHERE status = 'active'"
        try:
            result = await self._execute_query(query, fetch=True)
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Failed to get all active lamps: {str(e)}")
            raise

    async def get_lamp_status(self, lamp_id: int) -> str:
        """
        Retrieve the status of a specific lamp.

        :param lamp_id: The ID of the lamp.
        :return: The status of the lamp as a string.
        """
        query = "SELECT status FROM lamps WHERE id = %s"
        try:
            result = await self._execute_query(query, (lamp_id,), fetch=True)
            if result:
                return result[0]['status']
            else:
                logger.warning(f"No status found for lamp ID: {lamp_id}")
                return "unknown"
        except Exception as e:
            logger.error(f"Failed to get lamp status for ID {lamp_id}: {str(e)}")
            raise
```