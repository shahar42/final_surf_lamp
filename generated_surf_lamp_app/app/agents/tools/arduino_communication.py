```python
import asyncio
import json
from typing import Any, Dict, Optional

import aiohttp

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class ArduinoCommunicationTool:
    """Tool for handling communication with Arduino devices."""

    async def handle_lamp_config_request(self, lamp_id: str) -> Dict[str, Any]:
        """
        Handle a lamp configuration request for a specific lamp ID.

        Args:
            lamp_id (str): The ID of the lamp to configure.

        Returns:
            Dict[str, Any]: A dictionary formatted for Arduino response.
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{settings.ARDUINO_API_URL}/lamp/{lamp_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('registered'):
                            return self._create_registered_response(data)
                        else:
                            return self._create_unregistered_response()
                    elif response.status == 404:
                        return self._create_unregistered_response()
                    else:
                        return self._create_server_error_response()
        except Exception as e:
            logger.error(f"Error communicating with Arduino: {str(e)}")
            return self._create_server_error_response()

    def _create_registered_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a response for a registered lamp.

        Args:
            data (Dict[str, Any]): Data received from the Arduino.

        Returns:
            Dict[str, Any]: A dictionary formatted for Arduino response.
        """
        response = {
            "registered": True,
            "brightness": data.get('brightness', 0),
            "location_used": data.get('location_used', ""),
            "wave_height_m": data.get('wave_height_m'),
            "wave_period_s": data.get('wave_period_s'),
            "wind_speed_mps": data.get('wind_speed_mps'),
            "wind_deg": data.get('wind_deg'),
            "error": None
        }
        logger.info(f"Registered lamp response: {response}")
        return response

    def _create_unregistered_response(self) -> Dict[str, Any]:
        """
        Create a response for an unregistered lamp.

        Returns:
            Dict[str, Any]: A dictionary formatted for Arduino response.
        """
        response = {
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": None
        }
        logger.info("Unregistered lamp response")
        return response

    def _create_data_error_response(self) -> Dict[str, Any]:
        """
        Create a response for a data error.

        Returns:
            Dict[str, Any]: A dictionary formatted for Arduino response.
        """
        response = {
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": "Data error"
        }
        logger.error("Data error response")
        return response

    def _create_server_error_response(self) -> Dict[str, Any]:
        """
        Create a response for a server error.

        Returns:
            Dict[str, Any]: A dictionary formatted for Arduino response.
        """
        response = {
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": "Server error"
        }
        logger.error("Server error response")
        return response
```