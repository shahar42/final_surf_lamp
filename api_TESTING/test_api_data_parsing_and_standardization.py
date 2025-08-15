#!/usr/bin/env python3
"""
Test script to demonstrate the new field extraction system
Tests with your Israeli weather endpoints
"""

import json
import requests
from endpoint_configs import get_endpoint_config, FIELD_MAPPINGS
from background_processor import standardize_surf_data
from dotenv import load_dotenv

# Load environment variables (if any are needed, though this script is self-contained)
load_dotenv()

def test_field_extraction():
    """Test field extraction with mock API responses"""
    
    print("🧪 Testing Field Extraction System")
    print("=" * 60)
    
    # Define test cases with mock data matching real API structures
    test_cases = [
        {
            "name": "Isramar - Hadera Wave Data",
            "url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json",
            "mock_response": {
                "datetime": "2025-08-15 13:00 UTC",
                "parameters": [
                    {"name": "Significant wave height", "units": "m", "values": [0.65]},
                    {"name": "Peak wave period", "units": "s", "values": [5.0]}
                ]
            }
        },
        {
            "name": "Open-Meteo - Wave Data",
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818",
            "mock_response": {
                "hourly": {
                    "time": ["2025-08-15T13:00"],
                    "wave_height": [0.72],
                    "wave_period": [5.3],
                    "wave_direction": [280]
                }
            }
        },
        {
            "name": "Open-Meteo - Wind Data",
            "url": "https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818",
            "mock_response": {
                "hourly": {
                    "time": ["2025-08-15T13:00"],
                    "wind_speed_10m": [7.5],
                    "wind_direction_10m": [315]
                }
            }
        },
        {
            "name": "OpenWeatherMap - Weather Data",
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b",
            "mock_response": {
                "name": "Hadera",
                "main": {"temp": 306.53, "humidity": 45}, # Temp in Kelvin
                "wind": {"speed": 6.2, "deg": 313}
            }
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test['name']} ---")
        print(f"URL: {test['url']}")
        
        # 1. Verify a configuration exists for this endpoint
        config = get_endpoint_config(test['url'])
        if not config:
            print(f"❌ FAILED: No configuration found in endpoint_configs.py for this URL.")
            continue
        
        print(f"✅ Configuration Found.")
        
        # 2. Show the mock data
        print(f"\n📥 Mock API Response:")
        print(json.dumps(test['mock_response'], indent=2))
        
        # 3. Process the data using your project's function
        standardized = standardize_surf_data(test['mock_response'], test['url'])
        
        # 4. Show the result
        print(f"\n📤 Standardized Output:")
        if standardized:
            print(json.dumps(standardized, indent=2))
            print(f"✅ SUCCESS: Data parsed correctly.")
        else:
            print(f"❌ FAILED: The standardize_surf_data function returned None.")

def show_configuration_summary():
    """Displays a summary of all loaded API configurations."""
    print(f"\n📋 Loaded API Configuration Summary")
    print("=" * 60)
    
    for endpoint_key, config in FIELD_MAPPINGS.items():
        print(f"\n🌐 Endpoint Key: '{endpoint_key}'")
        
        # Show field mappings
        mappings = {k: v for k, v in config.items() if k not in ['fallbacks', 'conversions', 'custom_extraction']}
        print(f"   - Fields Mapped: {len(mappings)}")
        for field, path in mappings.items():
            print(f"     '{field}' <-- {path}")
        
        if config.get('custom_extraction'):
            print("   - Uses Custom Extraction Function: Yes")
            
        if config.get('fallbacks'):
            print(f"   - Fallbacks Configured: {list(config.get('fallbacks').keys())}")
            
        if config.get('conversions'):
            print(f"   - Conversions Configured: {list(config.get('conversions').keys())}")

if __name__ == "__main__":
    # Run the configuration summary first
    show_configuration_summary()
    
    # Run the extraction tests
    test_field_extraction()
    
    print("\n" + "="*60)
    print("🎯 Summary:")
    print("✅ This script tests your project's actual data parsing logic.")
    print("✅ If the 'Standardized Output' looks correct for all tests, your parsing is working.")
    print("\n💡 Next Steps:")
    print("   - If a test fails, check the corresponding mapping in 'endpoint_configs.py'.")

    print("   - Ensure all your API URLs in the database correctly match the 'Endpoint Key' shown above.")
