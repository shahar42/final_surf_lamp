"""
Surf Data Transformer
Pure data transformation functions with no side effects.

Responsibilities:
- Extract values from nested JSON structures
- Find current hour in time arrays
- Apply conversion functions to raw values
- Standardize API responses to common format

No dependencies on database or external APIs.
"""

import json
import time
import logging
from datetime import datetime
from endpoint_configs import get_endpoint_config

logger = logging.getLogger(__name__)


def extract_field_value(data, field_path):
    """
    Navigate nested JSON using field path like ['wind', 'speed'] or ['data', 0, 'value']

    Args:
        data: JSON data (dict or list)
        field_path: List of keys/indices to navigate

    Returns:
        Extracted value or None if not found
    """
    try:
        value = data
        for key in field_path:
            if isinstance(value, list) and isinstance(key, int):
                value = value[key]
            elif isinstance(value, dict):
                value = value[key]
            else:
                return None
        return value
    except (KeyError, TypeError, IndexError):
        return None


def get_current_hour_index(time_array):
    """
    Find the index in the hourly time array that corresponds to the current hour.

    Args:
        time_array: List of time strings like ["2025-09-13T00:00", "2025-09-13T01:00", ...]

    Returns:
        int: Index for current hour, or 0 if not found
    """
    try:
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        current_hour_str = current_hour.strftime("%Y-%m-%dT%H:%M")

        logger.info(f"🕐 Looking for current hour: {current_hour_str}")

        for i, time_str in enumerate(time_array):
            if time_str.startswith(current_hour_str):
                logger.info(f"✅ Found current hour at index {i}: {time_str}")
                return i

        logger.warning("⚠️  Current hour not found in time array, using index 0")
        return 0

    except Exception as e:
        logger.warning(f"⚠️  Error finding current hour index: {e}, using index 0")
        return 0


def apply_conversions(value, conversions, field_name):
    """
    Apply conversion functions to extracted field values.

    Args:
        value: Raw value from API
        conversions: Dict of conversion functions
        field_name: Name of the field being converted

    Returns:
        Converted value or original value if no conversion
    """
    if value is None or conversions is None:
        return value

    conversion_func = conversions.get(field_name)
    if conversion_func and callable(conversion_func):
        try:
            return conversion_func(value)
        except Exception as e:
            logger.warning(f"Conversion failed for {field_name}: {e}")
            return value

    return value


def standardize_surf_data(raw_data, endpoint_url):
    """
    Extract standardized fields using endpoint-specific configuration.
    Only returns fields that are actually found in the API response.
    """
    logger.info(f"🔧 Standardizing data from: {endpoint_url}")

    config = get_endpoint_config(endpoint_url)
    if not config:
        logger.error(f"❌ No field mapping config found for {endpoint_url}")
        return None

    logger.info(f"✅ Found config with {len(config)} field mappings")

    # Start with an empty dictionary
    standardized = {}

    if config.get('custom_extraction'):
        from endpoint_configs import extract_isramar_data
        standardized = extract_isramar_data(raw_data)
    else:
        conversions = config.get('conversions', {})

        # For Open-Meteo APIs, find the current hour index in the time array
        current_hour_index = 0
        if "open-meteo.com" in endpoint_url and "hourly" in raw_data:
            time_array = raw_data.get("hourly", {}).get("time", [])
            if time_array:
                current_hour_index = get_current_hour_index(time_array)

        for standard_field, field_path in config.items():
            if standard_field in ['fallbacks', 'conversions', 'custom_extraction']:
                continue

            # For Open-Meteo hourly data, replace hardcoded index with current hour index
            if ("open-meteo.com" in endpoint_url and
                len(field_path) == 3 and
                field_path[0] == "hourly" and
                isinstance(field_path[2], int)):

                logger.info(f"🕐 Using current hour index {current_hour_index} for {standard_field}")
                field_path = [field_path[0], field_path[1], current_hour_index]

            raw_value = extract_field_value(raw_data, field_path)

            # IMPORTANT: Only add the field if a value was actually found
            if raw_value is not None:
                converted_value = apply_conversions(raw_value, conversions, standard_field)
                standardized[standard_field] = converted_value

    # Only add metadata if some data was actually extracted
    if standardized:
        standardized['timestamp'] = int(time.time())
        standardized['source_endpoint'] = endpoint_url

    logger.info(f"✅ Standardized data: {json.dumps(standardized, indent=2)}")
    return standardized
