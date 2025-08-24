#!/usr/bin/env python3
"""
Test the discovery system without Arduino hardware
This simulates what the Arduino discovery module will do
"""

import requests
import json
import time

def test_static_discovery():
    """Test the discovery system using the local config file"""
    print("🔍 Testing discovery system with local config...")
    
    # Path to the local configuration file
    local_config_path = "discovery-config/config.json"
    
    print(f"   Trying local discovery file: {local_config_path}")
    
    try:
        with open(local_config_path, 'r') as f:
            config = json.load(f)
            server = config.get('api_server')
            if server:
                print(f"   ✅ Success! Server from local config: {server}")
                return server
            else:
                print("   ❌ 'api_server' not found in local config.")
                
    except FileNotFoundError:
        print(f"   ❌ Local config file not found at: {local_config_path}")
    except json.JSONDecodeError:
        print("   ❌ Error decoding JSON from local config file.")
    except Exception as e:
        print(f"   ❌ An error occurred: {e}")

    print("   🔄 Local discovery failed, using hardcoded fallback")
    return "final-surf-lamp.onrender.com"  # Hardcoded fallback with the correct server

def test_discovered_api(api_server):
    """Test the API server returned by discovery"""
    print(f"\n🧪 Testing discovered API server: {api_server}")
    
    # Test the discovery endpoint on the API server
    test_urls = [
        f"https://{api_server}/api/discovery/server",
        f"https://{api_server}/api/arduino/4433/data"  # Replace 4433 with your Arduino ID
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"   {url}: {response.status_code}")
            
            if response.status_code == 200:
                print(f"      ✅ Working")
            else:
                print(f"      ⚠️ Status {response.status_code}")
                
        except Exception as e:
            print(f"   {url}: ❌ {e}")

def main():
    print("🧪 Testing Discovery System (Arduino Simulation)")
    print("=" * 60)
    
    # Step 1: Test discovery
    api_server = test_static_discovery()
    
    # Step 2: Test discovered server
    test_discovered_api(api_server)
    
    print("\n" + "=" * 60)
    print("📋 Next Steps:")
    print("1. Set up GitHub Pages with discovery config")
    print("2. Update Arduino discovery URLs")  
    print("3. Flash Arduino with discovery code tomorrow")
    print("4. Test with real hardware")

if __name__ == "__main__":
    main()
