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

    def _legacy_numeric_ids(self):
        """Every lamp identifier that is a plain number, newest first.

        LEGACY ONLY. Lamps made since the MAC change are identified by their
        MAC address (12 hex digits), which has no sequence and needs no
        allocation. arduino_id is a text column, so the numeric ones are
        picked out and ordered in Python; sorting them in SQL would order
        them lexically ("9" > "14") and hand out a wrong "next" ID.
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT arduino_id FROM arduinos WHERE arduino_id IS NOT NULL"
            )).fetchall()
        numeric = [int(r[0]) for r in rows if str(r[0]).isdigit()]
        return sorted(numeric, reverse=True)

    def get_next_available_id(self):
        """
        Next free legacy sequential ID (highest numeric ID + 1).

        Returns:
            int: Next available ID (starting from 1)
        """
        try:
            used = self._legacy_numeric_ids()
            next_id = (used[0] + 1) if used else 1
            logger.info(f"Highest legacy numeric ID: {used[0] if used else None}, next available: {next_id}")
            return next_id
        except Exception as e:
            logger.error(f"Error getting next available ID: {e}")
            raise

    def get_used_ids(self, limit=100):
        """
        Legacy numeric lamp IDs currently in use, highest first.

        Args:
            limit (int): Maximum number of IDs to return

        Returns:
            list: List of used Arduino IDs
        """
        try:
            ids = self._legacy_numeric_ids()[:limit]
            logger.info(f"Retrieved {len(ids)} used legacy Arduino IDs")
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
                    "SELECT COUNT(*) FROM arduinos WHERE arduino_id = :id"
                ), {"id": str(arduino_id)})
                count = result.fetchone()[0]

                is_available = count == 0
                logger.info(f"Arduino ID {arduino_id} availability: {is_available}")
                return is_available

        except Exception as e:
            logger.error(f"Error checking ID availability: {e}")
            raise

    def get_id_statistics(self):
        """
        Statistics about LEGACY numeric ID usage. MAC-identified lamps are
        not counted: they have no sequence and are never allocated.

        Returns:
            dict: Statistics including total used, next available, etc.
        """
        try:
            used = self._legacy_numeric_ids()
            max_id = used[0] if used else 0
            return {
                "total_ids_used": len(used),
                "highest_id": max_id,
                "next_available_id": max_id + 1 if max_id else 1,
                "gaps_exist": len(used) < max_id,
            }
        except Exception as e:
            logger.error(f"Error getting ID statistics: {e}")
            raise
