```python
import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class APIDataRetrievalTool:
    """
    A tool for retrieving surf data from external APIs.

    This class handles the fetching and standardization of surf data from various API providers.
    """

    async def fetch_surf_data(self, website_url: str, api_key: str, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch surf data from the specified API.

        Args:
            website_url (str): The URL of the API endpoint.
            api_key (str): The API key for authentication.
            location_data (Dict[str, Any]): Location data to be used in the API request.

        Returns:
            Dict[str, Any]: Standardized surf data.

        Raises:
            aiohttp.ClientError: If there's an error with the HTTP request.
            ValueError: If the API response cannot be processed.
        """
        headers = {"Authorization": f"Bearer {api_key}"}
        params = location_data

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(website_url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._standardize_surf_data(data)
                    else:
                        error_message = f"API request failed with status code: {response.status}"
                        logger.error(error_message)
                        raise aiohttp.ClientResponseError(response.request_info, response.history, status=response.status, message=error_message)
        except asyncio.TimeoutError:
            logger.error("API request timed out")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Client error occurred: {str(e)}")
            raise

    def _standardize_surf_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize the surf data from different API providers.

        Args:
            data (Dict[str, Any]): Raw data from the API.

        Returns:
            Dict[str, Any]: Standardized surf data.

        Raises:
            ValueError: If the data cannot be standardized.
        """
        try:
            standardized_data = {
                "wave_height_m": data.get("wave_height", None),
                "wave_period_s": data.get("wave_period", None),
                "wind_speed_mps": data.get("wind_speed", None),
                "wind_deg": data.get("wind_direction", None)
            }

            # Convert units if necessary (example: from knots to m/s for wind speed)
            if standardized_data["wind_speed_mps"] is not None:
                standardized_data["wind_speed_mps"] = standardized_data["wind_speed_mps"] * 0.514444  # knots to m/s

            # Ensure all values are of the correct type
            for key, value in standardized_data.items():
                if value is not None:
                    if key in ["wave_height_m", "wave_period_s", "wind_speed_mps"]:
                        standardized_data[key] = float(value)
                    elif key == "wind_deg":
                        standardized_data[key] = int(value)

            return standardized_data
        except Exception as e:
            logger.error(f"Error standardizing surf data: {str(e)}")
            raise ValueError("Unable to standardize surf data") from e
```