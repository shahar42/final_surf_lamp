# Background Processor Function Documentation

## Overview
Background service for Surf Lamp processing that fetches surf data from APIs using configurable field mappings and updates the database. Uses API-based processing to eliminate duplicate calls and prevent rate limiting.

## Function Signatures

### Data Extraction & Processing

#### `extract_field_value(data, field_path)`
```python
def extract_field_value(data, field_path):
    """
    Navigate nested JSON using field path like ['wind', 'speed'] or ['data', 0, 'value']

    Args:
        data: JSON data (dict or list)
        field_path: List of keys/indices to navigate

    Returns:
        Extracted value or None if not found
    """
```

#### `get_current_hour_index(time_array)`
```python
def get_current_hour_index(time_array):
    """
    Find the index in the hourly time array that corresponds to the current hour.

    Args:
        time_array: List of time strings like ["2025-09-13T00:00", "2025-09-13T01:00", ...]

    Returns:
        int: Index for current hour, or 0 if not found
    """
```

#### `apply_conversions(value, conversions, field_name)`
```python
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
```

#### `standardize_surf_data(raw_data, endpoint_url)`
```python
def standardize_surf_data(raw_data, endpoint_url):
    """
    Extract standardized fields using endpoint-specific configuration.
    Only returns fields that are actually found in the API response.

    Args:
        raw_data: Raw JSON response from API
        endpoint_url: The API endpoint URL

    Returns:
        Dict with standardized surf data fields or None if config not found
    """
```

### Arduino Communication & Failure Tracking

#### `should_skip_arduino(arduino_id)`
```python
def should_skip_arduino(arduino_id):
    """Check if Arduino should be skipped due to recent failures

    Args:
        arduino_id: Arduino device identifier

    Returns:
        bool: True if should skip, False if should proceed
    """
```

#### `record_arduino_result(arduino_id, success)`
```python
def record_arduino_result(arduino_id, success):
    """Record Arduino communication result

    Args:
        arduino_id: Arduino device identifier
        success: bool indicating if communication was successful
    """
```

#### `send_to_arduino(arduino_id, surf_data, format_type="meters", location=None)`
```python
def send_to_arduino(arduino_id, surf_data, format_type="meters", location=None):
    """Send surf data to Arduino device via configurable transport with failure tracking

    Args:
        arduino_id: Arduino device identifier
        surf_data: Dict containing standardized surf data
        format_type: "meters" or "feet" for unit preference (default: "meters")
        location: Location string for timezone conversion (optional)

    Returns:
        bool: True if successful, False if failed
    """
```

#### `format_for_arduino(surf_data, format_type="meters", location=None)`
```python
def format_for_arduino(surf_data, format_type="meters", location=None):
    """Format surf data for Arduino consumption with location-aware time

    Args:
        surf_data: Dict containing standardized surf data
        format_type: "meters" or "feet" for unit preference (default: "meters")
        location: Location string for timezone conversion (optional)

    Returns:
        Dict with Arduino-formatted data
    """
```

### Database Operations

#### `test_database_connection()`
```python
def test_database_connection():
    """Test database connection and show table info

    Returns:
        bool: True if connection successful, False otherwise
    """
```

#### `get_unique_api_configs()`
```python
def get_unique_api_configs():
    """Get unique API configurations to avoid redundant calls

    Returns:
        List[Dict]: List of unique API configuration dictionaries with keys:
            - usage_id: Unique identifier for this API configuration
            - website_url: Human-readable API source name
            - api_key: Authentication key for the API
            - http_endpoint: Full API URL to call
            - endpoint_priority: Priority order for multi-source processing
    """
```

#### `get_arduinos_for_api(usage_id)`
```python
def get_arduinos_for_api(usage_id):
    """Get all Arduino targets that need data from this API

    Args:
        usage_id: API configuration identifier

    Returns:
        List[Dict]: List of Arduino target dictionaries with keys:
            - arduino_id: Arduino device identifier
            - lamp_id: Database lamp identifier
            - location: Geographic location string
            - format: User's preferred unit format
            - last_updated: Last update timestamp
    """
```

#### `get_arduino_ip(arduino_id)`
```python
def get_arduino_ip(arduino_id):
    """Get Arduino IP address from database

    Args:
        arduino_id: Arduino device identifier

    Returns:
        str: IP address or None if not found
    """
```

#### `get_user_threshold_for_arduino(arduino_id)`
```python
def get_user_threshold_for_arduino(arduino_id):
    """Get user's wave threshold for this Arduino

    Args:
        arduino_id: Arduino device identifier

    Returns:
        float: Wave threshold in meters (default: 1.0)
    """
```

#### `get_user_wind_threshold_for_arduino(arduino_id)`
```python
def get_user_wind_threshold_for_arduino(arduino_id):
    """Get user's wind threshold for this Arduino

    Args:
        arduino_id: Arduino device identifier

    Returns:
        float: Wind threshold in knots (default: 22.0)
    """
```

#### `update_lamp_timestamp(lamp_id)`
```python
def update_lamp_timestamp(lamp_id):
    """Update lamp's last_updated timestamp

    Args:
        lamp_id: Database lamp identifier

    Returns:
        bool: True if successful, False if failed
    """
```

#### `update_current_conditions(lamp_id, surf_data)`
```python
def update_current_conditions(lamp_id, surf_data):
    """Update current_conditions table with latest surf data

    Args:
        lamp_id: Database lamp identifier
        surf_data: Dict containing standardized surf data with keys:
            - wave_height_m: Wave height in meters
            - wave_period_s: Wave period in seconds
            - wind_speed_mps: Wind speed in meters per second
            - wind_direction_deg: Wind direction in degrees

    Returns:
        bool: True if successful, False if failed
    """
```

### API Communication

#### `fetch_surf_data(api_key, endpoint)`
```python
def fetch_surf_data(api_key, endpoint):
    """Fetch surf data from external API and standardize using config

    Args:
        api_key: API authentication key (can be empty for public APIs)
        endpoint: Full API URL to fetch from

    Returns:
        Dict: Standardized surf data or None if failed

    Features:
        - Automatic retry logic for 429 rate limiting errors
        - Exponential backoff (60s → 120s → 240s)
        - 10-second delay between all API calls
        - JSON parsing and standardization
    """
```

### Main Processing Functions

#### `process_all_lamps()`
```python
def process_all_lamps():
    """Main processing function - API-based processing to eliminate duplicate calls

    Process Flow:
        1. Get unique API configurations (one per endpoint)
        2. For each API: fetch data once, update all lamps that need it
        3. Update database timestamps and current conditions

    Returns:
        bool: True if successful, False if failed

    Benefits:
        - ~70% reduction in API calls vs lamp-by-lamp processing
        - Eliminates duplicate requests to same endpoints
        - Prevents rate limiting from burst requests
        - Faster processing cycles
    """
```

#### `run_once()`
```python
def run_once():
    """Run processing once for testing

    Returns:
        bool: True if successful, False if failed
    """
```

#### `main()`
```python
def main():
    """Main function - choose test mode or continuous mode

    Environment Variables:
        TEST_MODE: Set to 'true' for single run, 'false' for continuous

    Continuous Mode:
        - Runs initial cycle immediately
        - Schedules processing every 20 minutes
        - Uses schedule library for timing
    """
```

## Global Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (required)
- `ARDUINO_TRANSPORT`: "http" for real devices, "mock" for testing
- `TEST_MODE`: "true" for single run, "false" for continuous operation

### Global Constants
- `ARDUINO_FAILURE_THRESHOLD = 3`: Skip Arduino after 3 consecutive failures
- `ARDUINO_RETRY_DELAY = 1800`: 30 minutes before retrying failed Arduino
- `LOCATION_TIMEZONES`: Mapping of locations to timezone strings

### Data Structures

#### Standardized Surf Data Format
```python
{
    "wave_height_m": float,      # Wave height in meters
    "wave_period_s": float,      # Wave period in seconds
    "wind_speed_mps": float,     # Wind speed in meters per second
    "wind_direction_deg": int,   # Wind direction in degrees (0-360)
    "timestamp": int,            # Unix timestamp
    "source_endpoint": str       # API endpoint URL
}
```

#### Arduino Formatted Data
```python
{
    "wave_height_cm": int,           # Wave height in centimeters
    "wave_period_s": float,          # Wave period in seconds
    "wind_speed_mps": int,           # Wind speed in m/s (rounded)
    "wind_direction_deg": int,       # Wind direction in degrees
    "wave_threshold_cm": int,        # User's wave alert threshold
    "wind_speed_threshold_knots": int, # User's wind alert threshold
    "local_time": str,               # Location-aware timestamp
    "timezone": str                  # Timezone identifier
}
```

## Processing Architecture

The system uses **API-based processing** instead of lamp-based processing:

1. **Get Unique APIs**: Query database for distinct API endpoints
2. **Process Each API**: Make one call per unique endpoint
3. **Update All Lamps**: Send data to all lamps that need it
4. **Database Updates**: Update timestamps and current conditions

This approach eliminates duplicate API calls, prevents rate limiting, and significantly improves processing efficiency.