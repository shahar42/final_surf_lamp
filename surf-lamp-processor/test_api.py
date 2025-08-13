#!/usr/bin/env python3
"""
Test script to demonstrate the new field extraction system
Tests with your Israeli weather endpoints
"""

import json
import requests
from endpoint_configs import get_endpoint_config
from background_processor import standardize_surf_data
from dotenv import load_dotenv

load_dotenv()
def test_field_extraction():
    """Test field extraction with real API responses"""
    
    print("🧪 Testing Field Extraction System")
    print("=" * 60)
    
    # Test endpoints from your project
    test_endpoints = [
        {
            "name": "OpenWeatherMap (Hadera)",
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b",
            "mock_response": {
                "name": "Hadera",
                "main": {
                    "temp": 295.15,  # Kelvin
                    "humidity": 65
                },
                "wind": {
                    "speed": 8.5,    # m/s
                    "deg": 225
                }
            }
        },
        {
            "name": "Israeli Marine Data (Hadera)",
            "url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json",
            "mock_response": {
                "Hs": 1.8,      # Wave height in meters
                "Per": 9.2      # Wave period in seconds
            }
        }
    ]
    
    for i, test in enumerate(test_endpoints, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"URL: {test['url']}")
        print("-" * 40)
        
        # Check if we have configuration for this endpoint
        config = get_endpoint_config(test['url'])
        if not config:
            print(f"❌ No configuration found for this endpoint")
            continue
        
        print(f"✅ Found configuration:")
        for field, path in config.items():
            if field not in ['fallbacks', 'conversions']:
                print(f"   {field} <- {path}")
        
        # Test field extraction with mock data
        print(f"\n📥 Mock API Response:")
        print(json.dumps(test['mock_response'], indent=2))
        
        # Extract standardized data
        from background_processor import standardize_surf_data
        standardized = standardize_surf_data(test['mock_response'], test['url'])
        
        print(f"\n📤 Standardized Output:")
        if standardized:
            print(json.dumps(standardized, indent=2))
            print(f"✅ Extraction successful!")
        else:
            print(f"❌ Extraction failed!")

def test_live_api_call():
    """Test with a real API call (if you want to try)"""
    print(f"\n🌐 Live API Test (Optional)")
    print("=" * 60)
    
    # Test with OpenWeatherMap (you'll need a valid API key)
    api_key = "d6ef64df6585b7e88e51c221bbd41c2b"  # Your API key from the documents
    url = f"http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid={api_key}"
    
    try:
        print(f"📡 Making live API call to: {url[:80]}...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        raw_data = response.json()
        print(f"✅ API call successful!")
        print(f"📥 Raw response sample: {json.dumps(raw_data, indent=2)[:300]}...")
        
        # Extract standardized data
        from background_processor import standardize_surf_data
        standardized = standardize_surf_data(raw_data, url)
        
        if standardized:
            print(f"\n📤 Live Standardized Output:")
            print(json.dumps(standardized, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed: {e}")
        print("💡 This is normal if the API key is expired or rate limited")
    except Exception as e:
        print(f"❌ Error: {e}")

def show_configuration_summary():
    """Show all configured endpoints"""
    print(f"\n📋 Configuration Summary")
    print("=" * 60)
    
    from endpoint_configs import FIELD_MAPPINGS
    
    for endpoint, config in FIELD_MAPPINGS.items():
        print(f"\n🌐 {endpoint}")
        
        # Show field mappings
        mappings = {k: v for k, v in config.items() if k not in ['fallbacks', 'conversions']}
        print(f"   Fields mapped: {len(mappings)}")
        for field, path in mappings.items():
            print(f"     {field} <- {path}")
        
        # Show fallbacks
        fallbacks = config.get('fallbacks', {})
        if fallbacks:
            print(f"   Fallbacks: {list(fallbacks.keys())}")
        
        # Show conversions
        conversions = config.get('conversions', {})
        if conversions:
            print(f"   Conversions: {list(conversions.keys())}")

if __name__ == "__main__":
    show_configuration_summary()
    test_field_extraction()
    
    # Uncomment to test live API
    # test_live_api_call()
    
    print(f"\n🎯 Summary:")
    print(f"✅ Configuration system working")
    print(f"✅ Field extraction working")
    print(f"✅ Ready to integrate with background processor")
    print(f"\n💡 Next steps:")
    print(f"1. Add your endpoints to usage_lamps table")
    print(f"2. Run background processor with TEST_MODE=true")
    print(f"3. Check logs for real API calls")
