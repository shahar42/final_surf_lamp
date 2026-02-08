"""
Weather API Client
External API communication with retry logic and rate limiting.

Responsibilities:
- Fetch surf/weather data from external APIs
- Handle HTTP errors, timeouts, and rate limiting
- Retry logic with exponential backoff
- Validate endpoint parameters (e.g., wind speed units)

Dependencies: requests, surf_data_transformer
"""

import time
import json
import logging
import requests
from surf_data_transformer import standardize_surf_data

logger = logging.getLogger(__name__)


def fetch_surf_data_with_fallback(api_key, endpoints, wave_calculation_method='api'):
    """
    Fetch surf data from multiple endpoints with priority-based fallback.
    Scott Meyers pattern: Smart abstraction over naive single-URL fetch.

    Args:
        api_key: Optional API key for authentication
        endpoints: List of URLs in priority order (try first to last)
        wave_calculation_method: 'api' (default) or 'formula' for wind-based wave calculation

    Returns:
        Standardized surf data dict or None if all endpoints fail
    """
    if not endpoints:
        logger.error("❌ No endpoints provided")
        return None

    for idx, endpoint in enumerate(endpoints, 1):
        priority = f"[{idx}/{len(endpoints)}]"
        logger.info(f"📡 Trying endpoint {priority}: {endpoint[:70]}...")

        result = fetch_surf_data(api_key, endpoint, wave_calculation_method)
        if result:
            if idx > 1:
                logger.info(f"✅ Fallback successful - used endpoint {priority}")
            return result
        else:
            if idx < len(endpoints):
                logger.warning(f"⚠️ Endpoint {priority} failed, trying next...")
            else:
                logger.error(f"❌ All {len(endpoints)} endpoints failed")

    return None


def fetch_surf_data(api_key, endpoint, wave_calculation_method='api'):
    """
    Fetch surf data from external API and standardize using config.

    Args:
        api_key: Optional API key for authentication
        endpoint: API endpoint URL
        wave_calculation_method: 'api' (default) or 'formula' for wind-based wave calculation
    """
    logger.info(f"🌊 Fetching surf data from: {endpoint} (method: {wave_calculation_method})")

    # Validate Open-Meteo wind unit (must be m/s)
    if "wind_speed_10m" in endpoint and "open-meteo.com" in endpoint:
        if "&wind_speed_unit=ms" not in endpoint:
            logger.error("❌ ERROR: Open-Meteo wind endpoint missing '&wind_speed_unit=ms'!")
            return None

    try:
        headers = {'User-Agent': 'SurfLamp-Agent/1.0'}

        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key}'

        max_retries = 3
        base_delay = 60
        timeout_seconds = 30 if "openweathermap.org" in endpoint else 15

        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, headers=headers, timeout=timeout_seconds)
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    # Exponential backoff for timeouts: 30s, 60s, 120s
                    delay = 30 * (2 ** attempt)
                    logger.warning(f"⚠️ Timeout for {endpoint}, retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ All timeout retry attempts failed for {endpoint}")
                    return None
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ Rate limited. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                raise e

        # No artificial delay - APIs don't require it between different calls

        raw_data = response.json()
        surf_data = standardize_surf_data(raw_data, endpoint, wave_calculation_method)

        if surf_data:
            return surf_data
        else:
            logger.error("❌ Failed to standardize surf data")
            return None

    except Exception as e:
        logger.error(f"❌ Error fetching surf data from {endpoint}: {e}")
        return None