```python
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from app.tools.arduino_communication import ArduinoCommunicationTool

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/v1/lamps/{lamp_id}/config", response_model=dict)
async def get_lamp_config(lamp_id: str) -> dict:
    """
    Retrieve the configuration for a specific lamp.

    This endpoint fetches the lamp configuration and surf data using the ArduinoCommunicationTool.
    It returns the data in the format expected by Arduino devices.

    Args:
        lamp_id (str): The unique identifier for the lamp.

    Returns:
        dict: A dictionary containing the lamp configuration and surf data in the format:
        {
            "registered": bool,
            "brightness": int,
            "location_used": str,
            "wave_height_m": float | None,
            "wave_period_s": float | None,
            "wind_speed_mps": float | None,
            "wind_deg": int | None,
            "error": str | None
        }

    Raises:
        HTTPException: If there's an error fetching the lamp configuration.
    """
    try:
        arduino_tool = ArduinoCommunicationTool()
        lamp_config = await arduino_tool.get_lamp_config(lamp_id)
        surf_data = await arduino_tool.get_surf_data(lamp_config["location_used"])

        response = {
            "registered": lamp_config["registered"],
            "brightness": lamp_config["brightness"],
            "location_used": lamp_config["location_used"],
            "wave_height_m": surf_data.get("wave_height_m"),
            "wave_period_s": surf_data.get("wave_period_s"),
            "wind_speed_mps": surf_data.get("wind_speed_mps"),
            "wind_deg": surf_data.get("wind_deg"),
            "error": None
        }

        logger.info(f"Successfully fetched configuration for lamp {lamp_id}")
        return response

    except Exception as e:
        error_message = f"Error fetching configuration for lamp {lamp_id}: {str(e)}"
        logger.error(error_message)
        return {
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": error_message
        }
```