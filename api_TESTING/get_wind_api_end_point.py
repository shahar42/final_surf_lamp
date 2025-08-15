#!/usr/bin/env python3
"""
Wind Speed Endpoint Tester for Israeli Coastal Cities
Tests all wind data endpoints and shows current wind conditions

This script verifies that wind data is available for all supported cities
and displays current wind speed and direction for each location.
"""

import requests
import json
from datetime import datetime

# Wind data endpoints for all supported Israeli cities
WIND_ENDPOINTS = {
    "Tel Aviv, Israel": {
        "coordinates": {"lat": 32.0853, "lon": 34.7818},
        "endpoint": "https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818&hourly=wind_speed_10m,wind_direction_10m"
    },
    "Hadera, Israel": {
        "coordinates": {"lat": 32.4365, "lon": 34.9196},
        "endpoint": "https://api.open-meteo.com/v1/forecast?latitude=32.4365&longitude=34.9196&hourly=wind_speed_10m,wind_direction_10m"
    },
    "Ashdod, Israel": {
        "coordinates": {"lat": 31.7939, "lon": 34.6328},
        "endpoint": "https://api.open-meteo.com/v1/forecast?latitude=31.7939&longitude=34.6328&hourly=wind_speed_10m,wind_direction_10m"
    },
    "Haifa, Israel": {
        "coordinates": {"lat": 32.7940, "lon": 34.9896},
        "endpoint": "https://api.open-meteo.com/v1/forecast?latitude=32.7940&longitude=34.9896&hourly=wind_speed_10m,wind_direction_10m"
    },
    "Netanya, Israel": {
        "coordinates": {"lat": 32.3215, "lon": 34.8532},
        "endpoint": "https://api.open-meteo.com/v1/forecast?latitude=32.3215&longitude=34.8532&hourly=wind_speed_10m,wind_direction_10m"
    }
}

def test_wind_endpoint(city_name, endpoint_data):
    """
    Test a single wind data endpoint and extract current wind conditions.
    
    Args:
        city_name (str): Name of the city
        endpoint_data (dict): Contains coordinates and endpoint URL
        
    Returns:
        dict: Wind data or None if failed
    """
    print(f"\n🌪️  Testing {city_name}...")
    print(f"   📍 Coordinates: {endpoint_data['coordinates']['lat']}, {endpoint_data['coordinates']['lon']}")
    print(f"   🔗 Endpoint: {endpoint_data['endpoint']}")
    
    try:
        # Make API request with timeout
        response = requests.get(endpoint_data['endpoint'], timeout=10)
        print(f"   📊 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract current wind conditions (first hour of data)
            if 'hourly' in data and 'wind_speed_10m' in data['hourly']:
                wind_speed = data['hourly']['wind_speed_10m'][0] if data['hourly']['wind_speed_10m'] else 0
                wind_direction = data['hourly']['wind_direction_10m'][0] if data['hourly']['wind_direction_10m'] else 0
                timestamp = data['hourly']['time'][0] if data['hourly']['time'] else 'Unknown'
                
                result = {
                    'city': city_name,
                    'wind_speed_mps': wind_speed,
                    'wind_direction_deg': wind_direction,
                    'timestamp': timestamp,
                    'status': 'success'
                }
                
                print(f"   ✅ SUCCESS: Wind {wind_speed} m/s from {wind_direction}°")
                print(f"   ⏰ Data time: {timestamp}")
                
                return result
            else:
                print(f"   ❌ ERROR: No wind data in response")
                return None
                
        else:
            print(f"   ❌ ERROR: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"   ❌ ERROR: Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ❌ ERROR: Request failed - {e}")
        return None
    except json.JSONDecodeError:
        print(f"   ❌ ERROR: Invalid JSON response")
        return None
    except Exception as e:
        print(f"   ❌ ERROR: Unexpected error - {e}")
        return None

def convert_wind_direction(degrees):
    """Convert wind direction from degrees to compass direction"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

def main():
    """Main function to test all wind endpoints"""
    print("🌊 WIND SPEED ENDPOINT TESTER")
    print("=" * 60)
    print(f"Testing wind data availability for {len(WIND_ENDPOINTS)} Israeli coastal cities")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test each endpoint
    successful_cities = []
    failed_cities = []
    wind_data = []
    
    for city_name, endpoint_data in WIND_ENDPOINTS.items():
        result = test_wind_endpoint(city_name, endpoint_data)
        
        if result:
            successful_cities.append(city_name)
            wind_data.append(result)
        else:
            failed_cities.append(city_name)
    
    # Summary Report
    print(f"\n{'=' * 60}")
    print("📊 WIND DATA SUMMARY REPORT")
    print(f"{'=' * 60}")
    
    print(f"\n✅ Successful Cities: {len(successful_cities)}/{len(WIND_ENDPOINTS)}")
    for city in successful_cities:
        print(f"   • {city}")
    
    if failed_cities:
        print(f"\n❌ Failed Cities: {len(failed_cities)}")
        for city in failed_cities:
            print(f"   • {city}")
    
    # Current Wind Conditions Table
    if wind_data:
        print(f"\n🌪️  CURRENT WIND CONDITIONS")
        print("-" * 60)
        print(f"{'City':<20} {'Speed (m/s)':<12} {'Direction':<12} {'Compass':<8}")
        print("-" * 60)
        
        for data in wind_data:
            city_short = data['city'].replace(', Israel', '')
            compass = convert_wind_direction(data['wind_direction_deg'])
            print(f"{city_short:<20} {data['wind_speed_mps']:<12.1f} {data['wind_direction_deg']:<12}° {compass:<8}")
    
    # Endpoint Configuration for Code
    print(f"\n🔧 ENDPOINT CONFIGURATION (For Code)")
    print("-" * 60)
    print("These are the working wind endpoints for your background processor:")
    print()
    
    for city_name, endpoint_data in WIND_ENDPOINTS.items():
        if city_name in successful_cities:
            print(f'"{city_name}": {{')
            print(f'    "url": "{endpoint_data["endpoint"]}",')
            print(f'    "priority": 2,')
            print(f'    "type": "wind"')
            print(f'}},')
    
    # Final Status
    print(f"\n🎯 FINAL STATUS:")
    if len(successful_cities) == len(WIND_ENDPOINTS):
        print("✅ ALL ENDPOINTS WORKING - Wind data available for all cities!")
        print("✅ Your multi-source API system is ready for deployment!")
    elif len(successful_cities) > 0:
        print(f"⚠️  PARTIAL SUCCESS - {len(successful_cities)} of {len(WIND_ENDPOINTS)} cities working")
        print("⚠️  Some wind endpoints may need investigation")
    else:
        print("❌ ALL ENDPOINTS FAILED - Check internet connection or API service")
    
    print(f"\n📈 Wind Speed Range: {min([d['wind_speed_mps'] for d in wind_data]):.1f} - {max([d['wind_speed_mps'] for d in wind_data]):.1f} m/s")
    print(f"🧭 Wind directions vary from {min([d['wind_direction_deg'] for d in wind_data])}° to {max([d['wind_direction_deg'] for d in wind_data])}°")
    
    print(f"\n{'=' * 60}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
