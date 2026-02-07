#!/usr/bin/env python3
"""
Location Endpoints Validator
Tests each API endpoint and reports which surf parameters are retrieved.

Usage:
    python3 check_location_endpoints.py [location_name]

Examples:
    python3 check_location_endpoints.py                    # Test all locations
    python3 check_location_endpoints.py "Hadera, Israel"   # Test specific location
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime

# Add surf-lamp-processor to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'surf-lamp-processor'))
from surf_data_transformer import standardize_surf_data


# Relevant surf parameters for the system (stored in DB and sent to Arduinos)
RELEVANT_PARAMS = {
    'wave_height_m': 'Wave Height (meters)',
    'wave_period_s': 'Wave Period (seconds)',
    'wind_speed_mps': 'Wind Speed (m/s)',
    'wind_direction_deg': 'Wind Direction (degrees)',
}

# Parameters fetched from APIs but IGNORED by the system (not stored, not sent to lamps)
IGNORED_PARAMS = {
    'wave_direction_deg': 'Wave Direction (degrees) - IGNORED',
}


def load_location_endpoints():
    """
    Load location endpoints dynamically from beaches.py (single source of truth).

    Fallback to JSON file if beaches.py import fails (backward compatibility).
    """
    # PRIMARY: Generate from beaches.py
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'web_and_database'))
        from locations import get_all_beaches
        from locations.beach_service import get_api_urls_for_beach

        config = {}
        for beach in get_all_beaches():
            name = beach['english_name']
            urls = get_api_urls_for_beach(name)
            if urls:
                wave_url, wind_url = urls
                config[name] = [
                    {"url": wave_url, "priority": 1, "type": "wave"},
                    {"url": wind_url, "priority": 2, "type": "wind"}
                ]

        if config:
            print(f"✅ Loaded {len(config)} locations from beaches.py (single source of truth)")
            return config
    except Exception as e:
        print(f"⚠️ Failed to load from beaches.py: {e}, trying JSON fallback...")

    # FALLBACK: JSON file (deprecated)
    json_path = Path(__file__).parent / 'location_endpoints.json'
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            print(f"⚠️ Loaded {len(config)} locations from JSON fallback")
            return config

    print(f"❌ Error: Could not load locations from beaches.py or JSON")
    sys.exit(1)


def fetch_endpoint_data(endpoint_url, timeout=15):
    """
    Fetch data from endpoint and return raw response.

    Args:
        endpoint_url: API endpoint URL
        timeout: Request timeout in seconds

    Returns:
        tuple: (raw_data dict, error str or None)
    """
    try:
        headers = {'User-Agent': 'SurfLamp-Validator/1.0'}
        response = requests.get(endpoint_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}"
    except Exception as e:
        return None, str(e)


def test_endpoint(endpoint_url, endpoint_type, wave_calc_method='api'):
    """
    Test a single endpoint and return extracted parameters.

    Args:
        endpoint_url: API endpoint URL
        endpoint_type: 'wave' or 'wind'
        wave_calc_method: 'api' or 'formula'

    Returns:
        dict: Test results with extracted parameters
    """
    result = {
        'url': endpoint_url[:80] + '...' if len(endpoint_url) > 80 else endpoint_url,
        'type': endpoint_type,
        'status': 'unknown',
        'extracted': {},
        'error': None
    }

    # Fetch raw data
    raw_data, error = fetch_endpoint_data(endpoint_url)

    if error:
        result['status'] = 'failed'
        result['error'] = error
        return result

    # Standardize data using existing transformer logic
    standardized = standardize_surf_data(raw_data, endpoint_url, wave_calc_method)

    if not standardized:
        result['status'] = 'failed'
        result['error'] = 'Failed to parse response'
        return result

    result['status'] = 'success'

    # Extract relevant parameters (stored in DB + sent to Arduinos)
    for param_key, param_name in RELEVANT_PARAMS.items():
        if param_key in standardized:
            value = standardized[param_key]
            if value is not None:
                result['extracted'][param_name] = value

    # Track ignored parameters (fetched but not used by system)
    result['ignored'] = {}
    for param_key, param_name in IGNORED_PARAMS.items():
        if param_key in standardized:
            value = standardized[param_key]
            if value is not None:
                result['ignored'][param_name] = value

    return result


def format_value(value):
    """Format parameter value for display."""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def test_location(location_name, endpoints, wave_calc_method='api'):
    """
    Test all endpoints for a location.

    Args:
        location_name: Location name
        endpoints: List of endpoint configs
        wave_calc_method: Wave calculation method for this location
    """
    print(f"\n{'='*80}")
    print(f"📍 Location: {location_name}")
    print(f"   Wave Calculation: {wave_calc_method.upper()}")
    print(f"   Endpoints: {len(endpoints)}")
    print(f"{'='*80}\n")

    for idx, endpoint_config in enumerate(endpoints, 1):
        url = endpoint_config['url']
        priority = endpoint_config['priority']
        endpoint_type = endpoint_config['type']

        print(f"[{idx}/{len(endpoints)}] Priority {priority} | Type: {endpoint_type.upper()}")
        print(f"     URL: {url[:70]}...")

        result = test_endpoint(url, endpoint_type, wave_calc_method)

        if result['status'] == 'success':
            print(f"     ✅ Status: SUCCESS")
            if result['extracted']:
                print(f"     📊 Retrieved Parameters (Used by System):")
                for param_name, value in result['extracted'].items():
                    print(f"        • {param_name}: {format_value(value)}")
            else:
                print(f"     ⚠️  No relevant parameters extracted")

            if result.get('ignored'):
                print(f"     🗑️  Ignored Parameters (Not Used):")
                for param_name, value in result['ignored'].items():
                    print(f"        • {param_name}: {format_value(value)}")
        else:
            print(f"     ❌ Status: FAILED")
            print(f"     💥 Error: {result['error']}")

        print()


def determine_wave_calc_method(endpoints):
    """Determine wave calculation method based on endpoint types."""
    has_wave_source = any(e['type'] == 'wave' for e in endpoints)
    return 'api' if has_wave_source else 'formula'


def main():
    """Main entry point."""
    print("\n🌊 Surf Lamp Location Endpoints Validator")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load configuration (dynamically from beaches.py)
    locations = load_location_endpoints()
    print()

    # Check if user specified a location
    target_location = sys.argv[1] if len(sys.argv) > 1 else None

    if target_location:
        if target_location not in locations:
            print(f"❌ Error: Location '{target_location}' not found in configuration")
            print(f"\n📍 Available locations:")
            for loc in sorted(locations.keys()):
                print(f"   • {loc}")
            sys.exit(1)

        locations = {target_location: locations[target_location]}

    # Test each location
    total_endpoints = 0
    success_count = 0
    failed_count = 0

    for location_name, endpoints in locations.items():
        wave_calc_method = determine_wave_calc_method(endpoints)
        test_location(location_name, endpoints, wave_calc_method)

        # Count results (rough estimation for summary)
        total_endpoints += len(endpoints)

    print(f"\n{'='*80}")
    print(f"📊 Summary")
    print(f"{'='*80}")
    print(f"Total Locations: {len(locations)}")
    print(f"Total Endpoints: {total_endpoints}")
    print(f"\n✅ Validation complete")


if __name__ == '__main__':
    main()
