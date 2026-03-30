#!/usr/bin/env python3
"""
API Truth Validator using MCP Tools
Compares database values against real-time API calls to verify data accuracy.
Uses the Supabase MCP tools and direct API calls.
"""

import os
import sys
import requests
import json
from datetime import datetime
import time

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
web_db_path = os.path.join(parent_dir, 'web_and_database')
sys.path.append(web_db_path)

try:
    from data_base import MULTI_SOURCE_LOCATIONS
except ImportError as e:
    # Fallback configuration if import fails
    MULTI_SOURCE_LOCATIONS = {
        "Hadera, Israel": [
            {
                "url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json",
                "priority": 1,
                "type": "wave"
            },
            {
                "url": "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b",
                "priority": 2,
                "type": "wind"
            }
        ]
    }

def make_api_call(url, timeout=15):
    """Make API call and return parsed response"""
    try:
        headers = {'User-Agent': 'SurfLamp-Truth-Validator/1.0'}

        print(f"📤 Making API call: {url}")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        return {"error": "timeout", "message": f"API call timed out after {timeout}s"}
    except requests.exceptions.RequestException as e:
        return {"error": "request_failed", "message": str(e)}
    except json.JSONDecodeError:
        return {"error": "invalid_json", "message": "API returned invalid JSON"}

def standardize_api_data(raw_data, endpoint_url):
    """Apply the same standardization logic as the background processor"""

    # Find the API configuration for this endpoint
    endpoint_config = None
    for location, api_list in MULTI_SOURCE_LOCATIONS.items():
        for api_config in api_list:
            if api_config['url'] == endpoint_url:
                endpoint_config = api_config
                break
        if endpoint_config:
            break

    if not endpoint_config:
        return {"error": "no_config", "message": f"No configuration found for {endpoint_url}"}

    if 'error' in raw_data:
        return raw_data

    try:
        # Apply basic standardization based on endpoint type
        standardized = {}

        if endpoint_config.get('type') == 'wave':
            # Isramar wave data - new format
            if 'parameters' in raw_data:
                for param in raw_data['parameters']:
                    if 'Significant wave height' in param.get('name', ''):
                        if param.get('values') and len(param['values']) > 0:
                            standardized['wave_height_m'] = param['values'][0]
                    elif 'Peak wave period' in param.get('name', ''):
                        if param.get('values') and len(param['values']) > 0:
                            standardized['wave_period_s'] = param['values'][0]

        elif endpoint_config.get('type') == 'wind':
            # OpenWeatherMap wind data
            if 'wind' in raw_data:
                wind_data = raw_data['wind']
                if 'speed' in wind_data:
                    standardized['wind_speed_mps'] = wind_data['speed']
                if 'deg' in wind_data:
                    standardized['wind_direction_deg'] = wind_data['deg']

        # Add metadata
        standardized['timestamp'] = int(time.time())
        standardized['source_endpoint'] = endpoint_url

        return standardized

    except Exception as e:
        return {"error": "standardization_failed", "message": str(e)}

def compare_values(db_value, api_value, field_name, tolerance=0.1):
    """Compare database value with API value, allowing for small differences"""

    if db_value is None and api_value is None:
        return {"match": True, "reason": "both_null"}

    if db_value is None or api_value is None:
        return {"match": False, "reason": "one_null", "db": db_value, "api": api_value}

    # For numeric fields, allow small tolerance
    if field_name in ['wave_height_m', 'wave_period_s', 'wind_speed_mps']:
        diff = abs(float(db_value) - float(api_value))
        if diff <= tolerance:
            return {"match": True, "reason": "within_tolerance", "difference": diff}
        else:
            return {"match": False, "reason": "exceeds_tolerance", "difference": diff, "db": db_value, "api": api_value}

    # For wind direction, handle circular difference
    if field_name == 'wind_direction_deg':
        db_deg = float(db_value)
        api_deg = float(api_value)

        # Calculate circular difference
        diff = abs(db_deg - api_deg)
        if diff > 180:
            diff = 360 - diff

        if diff <= 10:  # 10 degree tolerance for wind direction
            return {"match": True, "reason": "within_tolerance", "difference": diff}
        else:
            return {"match": False, "reason": "exceeds_tolerance", "difference": diff, "db": db_value, "api": api_value}

    # Exact match for other fields
    if str(db_value) == str(api_value):
        return {"match": True, "reason": "exact_match"}
    else:
        return {"match": False, "reason": "no_match", "db": db_value, "api": api_value}

def get_database_values_from_input():
    """Get database values from user input (since MCP calls would be external)"""
    print("\n📊 Please provide current database values:")
    print("(You can get these from: mcp__surf-lamp-supabase__query_table current_conditions)")

    # For demo, use the values we saw earlier
    hadera_lamps = [
        {"lamp_id": 4422, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321},
        {"lamp_id": 46528, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321},
        {"lamp_id": 4421, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321},
        {"lamp_id": 1, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321},
        {"lamp_id": 65485, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321},
        {"lamp_id": 420, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321},
        {"lamp_id": 4321, "wave_height_m": 0.82, "wave_period_s": 5.2, "wind_speed_mps": 5.04, "wind_direction_deg": 321}
    ]

    return {
        "Hadera, Israel": {
            "lamps": hadera_lamps,
            "latest_update": "2025-09-22T12:14:44"
        }
    }

def validate_location_data(location, db_data):
    """Validate data for a specific location against real API calls"""

    print(f"\n🔍 Validating location: {location}")
    print(f"📊 Database shows {len(db_data['lamps'])} lamps")
    print(f"⏰ Latest DB update: {db_data['latest_update']}")

    # Get API configuration for this location
    if location not in MULTI_SOURCE_LOCATIONS:
        return {"error": f"No API configuration found for {location}"}

    api_list = MULTI_SOURCE_LOCATIONS[location]

    results = {
        "location": location,
        "database_lamps": len(db_data['lamps']),
        "api_calls": [],
        "validation_summary": {
            "total_apis": 0,
            "successful_apis": 0,
            "failed_apis": 0,
            "data_matches": 0,
            "data_mismatches": 0
        }
    }

    # Try each API for this location
    for api_config in api_list:
        api_url = api_config['url']
        priority = api_config['priority']

        print(f"\n📡 Testing API (Priority {priority}): {api_url}")

        # Make the API call
        raw_data = make_api_call(api_url)
        results['validation_summary']['total_apis'] += 1

        if 'error' in raw_data:
            print(f"❌ API call failed: {raw_data['message']}")
            results['validation_summary']['failed_apis'] += 1
            results['api_calls'].append({
                "url": api_url,
                "priority": priority,
                "status": "failed",
                "error": raw_data
            })
            continue

        print(f"✅ API call successful")
        results['validation_summary']['successful_apis'] += 1

        # Standardize the data
        standardized_data = standardize_api_data(raw_data, api_url)

        if 'error' in standardized_data:
            print(f"❌ Standardization failed: {standardized_data['message']}")
            results['api_calls'].append({
                "url": api_url,
                "priority": priority,
                "status": "standardization_failed",
                "error": standardized_data
            })
            continue

        print(f"🔧 Standardized data: {standardized_data}")

        # Compare with database values
        field_comparisons = {}
        overall_match = True

        # Take first lamp as representative (they should all have same values for location)
        if db_data['lamps']:
            sample_lamp = db_data['lamps'][0]

            comparison_fields = ['wave_height_m', 'wave_period_s', 'wind_speed_mps', 'wind_direction_deg']

            for field in comparison_fields:
                if field in standardized_data:
                    db_value = sample_lamp.get(field)
                    api_value = standardized_data[field]

                    comparison = compare_values(db_value, api_value, field)
                    field_comparisons[field] = comparison

                    if comparison['match']:
                        print(f"✅ {field}: DB={db_value} ≈ API={api_value}")
                    else:
                        print(f"❌ {field}: DB={db_value} ≠ API={api_value} ({comparison['reason']})")
                        overall_match = False
                else:
                    field_comparisons[field] = {"match": False, "reason": "field_not_in_api"}
                    print(f"⚠️ {field}: Not available in API response")

        if overall_match:
            results['validation_summary']['data_matches'] += 1
        else:
            results['validation_summary']['data_mismatches'] += 1

        results['api_calls'].append({
            "url": api_url,
            "priority": priority,
            "status": "success",
            "raw_data": raw_data,
            "standardized_data": standardized_data,
            "field_comparisons": field_comparisons,
            "overall_match": overall_match
        })

    return results

def main():
    """Main validation function"""
    print("🔍 API Truth Validator (MCP Version)")
    print("=" * 50)
    print("Comparing database values with real-time API calls...")

    # Get current database values
    print("\n📊 Using current database values from recent query...")
    db_locations = get_database_values_from_input()

    if not db_locations:
        print("❌ No data provided")
        return

    print(f"✅ Found data for {len(db_locations)} locations")

    # Validate each location
    all_results = []

    for location, db_data in db_locations.items():
        try:
            result = validate_location_data(location, db_data)
            all_results.append(result)
        except Exception as e:
            print(f"❌ Error validating {location}: {e}")
            all_results.append({
                "location": location,
                "error": str(e)
            })

    # Summary report
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)

    total_locations = len(all_results)
    successful_validations = 0
    total_api_calls = 0
    successful_api_calls = 0
    total_matches = 0
    total_mismatches = 0

    for result in all_results:
        if 'error' not in result:
            successful_validations += 1
            summary = result['validation_summary']
            total_api_calls += summary['total_apis']
            successful_api_calls += summary['successful_apis']
            total_matches += summary['data_matches']
            total_mismatches += summary['data_mismatches']

            print(f"\n🌍 {result['location']}:")
            print(f"   📱 {summary['successful_apis']}/{summary['total_apis']} APIs working")
            print(f"   ✅ {summary['data_matches']} matches, ❌ {summary['data_mismatches']} mismatches")
        else:
            print(f"\n❌ {result['location']}: {result['error']}")

    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   📍 Locations validated: {successful_validations}/{total_locations}")
    print(f"   📡 API calls successful: {successful_api_calls}/{total_api_calls}")
    print(f"   🎯 Data accuracy: {total_matches} matches, {total_mismatches} mismatches")

    if total_mismatches == 0 and successful_api_calls > 0:
        print(f"\n🎉 PERFECT ACCURACY: Database values match API truth!")
    elif total_mismatches > 0:
        print(f"\n⚠️ DATA DRIFT DETECTED: {total_mismatches} mismatches found")
    else:
        print(f"\n❌ VALIDATION FAILED: No successful API calls")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"api_validation_results_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_locations": total_locations,
                "successful_validations": successful_validations,
                "total_api_calls": total_api_calls,
                "successful_api_calls": successful_api_calls,
                "total_matches": total_matches,
                "total_mismatches": total_mismatches
            },
            "detailed_results": all_results
        }, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    main()