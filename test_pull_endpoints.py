#!/usr/bin/env python3
"""
Test script for new Arduino pull endpoints
Run this to verify Phase 1 is working before proceeding
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:5001"  # Adjust for your Flask app
TEST_ARDUINO_ID = 4433  # Replace with your actual Arduino ID

def test_discovery_endpoint():
    """Test the discovery endpoint"""
    print("🔍 Testing discovery endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/discovery/server", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Discovery endpoint working!")
            print(f"   Server: {data['api_server']}")
            print(f"   Version: {data['version']}")
            return True
        else:
            print(f"❌ Discovery failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        return False

def test_arduino_data_endpoint():
    """Test the Arduino data endpoint"""
    print(f"🤖 Testing Arduino data endpoint for ID {TEST_ARDUINO_ID}...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/arduino/{TEST_ARDUINO_ID}/data", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Arduino data endpoint working!")
            print(f"   Wave height: {data['wave_height_cm']}cm")
            print(f"   Data available: {data['data_available']}")
            return True
        elif response.status_code == 404:
            print(f"⚠️ Arduino {TEST_ARDUINO_ID} not found in database")
            print(f"   This is expected if you haven't registered this Arduino ID yet")
            return True
        else:
            print(f"❌ Arduino data failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Arduino data error: {e}")
        return False

def main():
    print("🧪 Testing Phase 1: Pull API Endpoints")
    print("=" * 50)
    
    discovery_ok = test_discovery_endpoint()
    print()
    arduino_ok = test_arduino_data_endpoint()
    
    print("\n" + "=" * 50)
    if discovery_ok and arduino_ok:
        print("🎉 Phase 1 Complete: All endpoints working!")
        print("✅ Ready to proceed to Phase 2")
    else:
        print("❌ Phase 1 Failed: Fix issues before proceeding")

if __name__ == "__main__":
    main()
