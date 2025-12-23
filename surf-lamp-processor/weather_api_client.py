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


def fetch_surf_data(api_key, endpoint):
    """Fetch surf data from external API and standardize using config

    ⚠️  CRITICAL MAINTAINER NOTE: WIND SPEED UNITS ⚠️
    ==============================================
    ALL Open-Meteo wind APIs MUST include "&wind_speed_unit=ms" parameter!
    - Without this parameter, APIs return km/h instead of m/s
    - This causes incorrect wind speed calculations throughout the system
    - Arduino expects wind_speed_mps (meters per second) from database
    - ALWAYS verify new wind endpoints include "&wind_speed_unit=ms"

    Example correct URL:
    https://api.open-meteo.com/v1/forecast?lat=32.0&lon=34.0&hourly=wind_speed_10m&wind_speed_unit=ms
    """
    logger.info(f"🌊 Fetching surf data from: {endpoint}")

    # CRITICAL VALIDATION: Check wind speed unit parameter
    if "wind_speed_10m" in endpoint and "open-meteo.com" in endpoint:
        if "&wind_speed_unit=ms" not in endpoint:
            logger.error("❌ CRITICAL ERROR: Open-Meteo wind endpoint missing '&wind_speed_unit=ms' parameter!")
            logger.error(f"❌ Endpoint: {endpoint}")
            logger.error("❌ This will return km/h instead of m/s and break wind calculations!")
            return None

    try:
        # Build headers - only add Authorization if API key exists
        headers = {'User-Agent': 'SurfLamp-Agent/1.0'}

        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key}'
            logger.info("📤 Making API request with authentication")
        else:
            logger.info("📤 Making API request without authentication (public endpoint)")

        logger.info(f"📤 Headers: {headers}")

        # Make the API call with retry logic for rate limiting and timeouts
        max_retries = 3
        base_delay = 60  # Start with 60 seconds for rate limit retries

        # Use longer timeout for OpenWeatherMap as it can be slower than marine APIs
        timeout_seconds = 30 if "openweathermap.org" in endpoint else 15
        logger.info(f"📤 Using {timeout_seconds}s timeout for this API")

        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, headers=headers, timeout=timeout_seconds)
                response.raise_for_status()
                break  # Success, exit retry loop
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Request timeout ({timeout_seconds}s) for {endpoint}")
                if attempt < max_retries - 1:  # Not the last attempt
                    delay = 30  # Shorter delay for timeout retries
                    logger.warning(f"⚠️ Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ All timeout retry attempts failed for {endpoint}")
                    return None
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:  # Not the last attempt
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"⚠️ Rate limited (429). Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limited after {max_retries} attempts, giving up")
                        raise e
                else:
                    raise e  # Other HTTP errors, don't retry

        # Add 30 second delay between all API calls to avoid rate limiting
        time.sleep(30)

        logger.info(f"✅ API call successful: {response.status_code}")
        logger.debug(f"📥 Raw response: {response.text[:200]}...")

        # Parse JSON response
        raw_data = response.json()

        # Standardize using endpoint configuration
        surf_data = standardize_surf_data(raw_data, endpoint)

        if surf_data:
            logger.info("✅ Surf data standardized successfully")
            return surf_data
        else:
            logger.error("❌ Failed to standardize surf data")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ HTTP request failed for {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing failed for {endpoint}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching surf data from {endpoint}: {e}")
        return None
