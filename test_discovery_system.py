#!/usr/bin/env python3
"""
Test the discovery system without Arduino hardware
This simulates what the Arduino discovery module will do
"""

import requests
import json
import time

def test_static_discovery():
    """Test the static discovery file (GitHub Pages)"""
    print("🔍 Testing static discovery system...")
    
    # These are the URLs your Arduino will use
    discovery_urls = [
        "https://shahar42.github.io/surflamp-discovery/config.json",
        "https://raw.githubusercontent.com/shahar42/surflamp-discovery/main/config.json"
    ]
    
    for i, url in enumerate(discovery_urls):
        print(f"   Trying discovery URL {i+1}: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                config = response.json()
                print(f"   ✅ Success! Server: {config.get('api_server')}")
                return config.get('api_server')
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    print("   🔄 All discovery URLs failed, would use hardcoded fallback")
    return "surf-lamp-api.render.com"  # Hardcoded fallback

def test_discovered_api(api_server):
    """Test the API server returned by discovery"""
    print(f"\n🧪 Testing discovered API server: {api_server}")
    
    # Test the discovery endpoint on the API server
    test_urls = [
        f"http://{api_server}/api/discovery/server",
        f"http://{api_server}/api/arduino/4433/data"  # Replace 4433 with your Arduino ID
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
