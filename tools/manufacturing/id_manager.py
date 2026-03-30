"""
Manufacturing ID Manager for Surf Lamp Production

Handles Arduino ID allocation and tracking using the production database.
"""

import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IDManager:
    """Manages Arduino ID allocation for manufacturing"""

    def __init__(self):
        """Initialize database connection"""
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        # For Supabase, explicitly require SSL
        connect_args = {}
        if "supabase.com" in self.database_url:
            connect_args["sslmode"] = "require"

        self.engine = create_engine(self.database_url, connect_args=connect_args)
        logger.info("ID Manager initialized with database connection")

    def get_next_available_id(self):
        """
        Query database for the next available Arduino ID.

        Returns:
            int: Next available ID (starting from 1)
        """
        try:
            with self.engine.connect() as conn:
                # Get the highest arduino_id currently in use
                result = conn.execute(text(
                    "SELECT MAX(arduino_id) as max_id FROM lamps WHERE arduino_id IS NOT NULL"
                ))
                row = result.fetchone()

                if row and row[0] is not None:
                    next_id = row[0] + 1
                    logger.info(f"Current max ID: {row[0]}, next available: {next_id}")
                else:
                    next_id = 1
                    logger.info("No IDs in database yet, starting from 1")

                return next_id

        except Exception as e:
            logger.error(f"Error getting next available ID: {e}")
            raise

    def get_used_ids(self, limit=100):
        """
        Get list of currently used Arduino IDs.

        Args:
            limit (int): Maximum number of IDs to return

        Returns:
            list: List of used Arduino IDs
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    f"SELECT arduino_id FROM lamps WHERE arduino_id IS NOT NULL "
                    f"ORDER BY arduino_id DESC LIMIT {limit}"
                ))
                ids = [row[0] for row in result.fetchall()]
                logger.info(f"Retrieved {len(ids)} used Arduino IDs")
                return ids

        except Exception as e:
            logger.error(f"Error getting used IDs: {e}")
            raise

    def is_id_available(self, arduino_id):
        """
        Check if a specific Arduino ID is available.

        Args:
            arduino_id (int): ID to check

        Returns:
            bool: True if available, False if already used
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM lamps WHERE arduino_id = :id"
                ), {"id": arduino_id})
                count = result.fetchone()[0]

                is_available = count == 0
                logger.info(f"Arduino ID {arduino_id} availability: {is_available}")
                return is_available

        except Exception as e:
            logger.error(f"Error checking ID availability: {e}")
            raise

    def get_id_statistics(self):
        """
        Get statistics about Arduino ID usage.

        Returns:
            dict: Statistics including total used, next available, etc.
        """
        try:
            with self.engine.connect() as conn:
                # Total lamps with IDs
                total_result = conn.execute(text(
                    "SELECT COUNT(*) FROM lamps WHERE arduino_id IS NOT NULL"
                ))
                total_used = total_result.fetchone()[0]

                # Highest ID
                max_result = conn.execute(text(
                    "SELECT MAX(arduino_id) FROM lamps WHERE arduino_id IS NOT NULL"
                ))
                max_id = max_result.fetchone()[0] or 0

                # Next available
                next_id = max_id + 1 if max_id else 1

                stats = {
                    "total_ids_used": total_used,
                    "highest_id": max_id,
                    "next_available_id": next_id,
                    "gaps_exist": total_used < max_id  # True if there are gaps in sequence
                }

                logger.info(f"ID Statistics: {stats}")
                return stats

        except Exception as e:
            logger.error(f"Error getting ID statistics: {e}")
            raise


if __name__ == "__main__":
    # Quick test
    manager = IDManager()
    print(f"Next available ID: {manager.get_next_available_id()}")
    print(f"Statistics: {manager.get_id_statistics()}")
