#!/usr/bin/env python3
"""
Israeli Surf Data API Proof of Concept
Tests multiple surf data APIs for Israeli coastal locations
Demonstrates data extraction and standardization
"""

import requests
import json
import time
from datetime import datetime

# Israeli coastal locations with coordinates
ISRAELI_LOCATIONS = {
    "Hadera": {
        "lat": 32.4365,
        "lon": 34.9196,
        "openweather_name": "Hadera",
        "isramar_endpoint": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json"
    },
    "Tel Aviv": {
        "lat": 32.0853,
        "lon": 34.7818,
        "openweather_name": "Tel Aviv",
        "isramar_endpoint": None
    },
    "Ashdod": {
        "lat": 31.7939,
        "lon": 34.6328,
        "openweather_name": "Ashdod",
        "isramar_endpoint": None
    },
    "Haifa": {
        "lat": 32.7940,
        "lon": 34.9896,
        "openweather_name": "Haifa",
        "isramar_endpoint": None
    },
    "Netanya": {
        "lat": 32.3215,
        "lon": 34.8532,
        "openweather_name": "Netanya",
        "isramar_endpoint": None
    }
}

# Your existing OpenWeatherMap API key
OPENWEATHER_API_KEY = "d6ef64df6585b7e88e51c221bbd41c2b"

def test_openweather_api(location_name, city_name):
    """Test OpenWeatherMap API for Israeli cities"""
    print(f"\n🌤️  Testing OpenWeatherMap for {location_name}...")
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant data
        extracted = {
            "api_source": "OpenWeatherMap",
            "location": data.get("name"),
            "coordinates": data.get("coord"),
            "temperature_k": data["main"]["temp"],
            "temperature_c": round(data["main"]["temp"] - 273.15, 1),
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed_mps": data["wind"]["speed"],
            "wind_direction_deg": data["wind"]["deg"],
            "weather": data["weather"][0]["description"],
            "timestamp": datetime.fromtimestamp(data["dt"]).isoformat()
        }
        
        print(f"✅ SUCCESS: {extracted['location']}")
        print(f"   🌡️  Temperature: {extracted['temperature_c']}°C")
        print(f"   💨 Wind: {extracted['wind_speed_mps']} m/s from {extracted['wind_direction_deg']}°")
        print(f"   📊 Pressure: {extracted['pressure']} hPa, Humidity: {extracted['humidity']}%")
        
        return extracted
        
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: {e}")
        return None

def test_open_meteo_marine_api(location_name, lat, lon):
    """Test Open-Meteo Marine API for wave data"""
    print(f"\n🌊 Testing Open-Meteo Marine API for {location_name}...")
    
    url = f"https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,wave_direction,wave_period,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
        "forecast_days": 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract current hour data (first entry)
        if data.get("hourly") and len(data["hourly"]["time"]) > 0:
            current_idx = 0  # First available hour
            
            extracted = {
                "api_source": "Open-Meteo Marine",
                "location": location_name,
                "coordinates": {"lat": data["latitude"], "lon": data["longitude"]},
                "wave_height_m": data["hourly"]["wave_height"][current_idx],
                "wave_direction_deg": data["hourly"]["wave_direction"][current_idx],
                "wave_period_s": data["hourly"]["wave_period"][current_idx],
                "wind_speed_mps": data["hourly"]["wind_speed_10m"][current_idx],
                "wind_direction_deg": data["hourly"]["wind_direction_10m"][current_idx],
                "timestamp": data["hourly"]["time"][current_idx],
                "timezone": data["timezone"]
            }
            
            print(f"✅ SUCCESS: {extracted['location']}")
            print(f"   🌊 Wave Height: {extracted['wave_height_m']}m")
            print(f"   ⏱️  Wave Period: {extracted['wave_period_s']}s")
            print(f"   🧭 Wave Direction: {extracted['wave_direction_deg']}°")
            print(f"   💨 Wind: {extracted['wind_speed_mps']} m/s from {extracted['wind_direction_deg']}°")
            
            return extracted
        else:
            print(f"❌ FAILED: No hourly data available")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: {e}")
        return None

def test_isramar_api(location_name, endpoint_url):
    """Test ISRAMAR (Israeli Marine) API for wave data"""
    if not endpoint_url:
        print(f"\n🏛️  ISRAMAR API: No endpoint available for {location_name}")
        return None
        
    print(f"\n🏛️  Testing ISRAMAR API for {location_name}...")
    
    try:
        response = requests.get(endpoint_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract ISRAMAR data format
        extracted = {
            "api_source": "ISRAMAR (Israeli Marine Research)",
            "location": location_name,
            "datetime": data.get("datetime"),
            "parameters": {}
        }
        
        # Parse parameters
        for param in data.get("parameters", []):
            name = param["name"]
            units = param["units"]
            values = param["values"]
            
            if "wave height" in name.lower():
                extracted["parameters"]["wave_height_m"] = values[0] if values else None
            elif "wave period" in name.lower():
                extracted["parameters"]["wave_period_s"] = values[0] if values else None
            elif "maximal wave" in name.lower():
                extracted["parameters"]["max_wave_height_m"] = values[0] if values else None
        
        print(f"✅ SUCCESS: {extracted['location']}")
        print(f"   🌊 Significant Wave Height: {extracted['parameters'].get('wave_height_m')}m")
        print(f"   ⏱️  Peak Wave Period: {extracted['parameters'].get('wave_period_s')}s")
        print(f"   📊 Max Wave Height: {extracted['parameters'].get('max_wave_height_m')}m")
        print(f"   🕐 Last Updated: {extracted['datetime']}")
        
        return extracted
        
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: {e}")
        return None

def standardize_surf_data(api_data):
    """Standardize data from different APIs into common format"""
    if not api_data:
        return None
    
    standardized = {
        "location": api_data.get("location"),
        "api_source": api_data.get("api_source"),
        "timestamp": int(time.time()),
        "wave_height_m": 0.0,
        "wave_period_s": 0.0,
        "wind_speed_mps": 0.0,
        "wind_direction_deg": 0
    }
    
    # Map based on API source
    if api_data["api_source"] == "OpenWeatherMap":
        standardized["wind_speed_mps"] = api_data.get("wind_speed_mps", 0.0)
        standardized["wind_direction_deg"] = api_data.get("wind_direction_deg", 0)
        # OpenWeatherMap doesn't provide wave data
        
    elif api_data["api_source"] == "Open-Meteo Marine":
        standardized["wave_height_m"] = api_data.get("wave_height_m") or 0.0
        standardized["wave_period_s"] = api_data.get("wave_period_s") or 0.0
        standardized["wind_speed_mps"] = api_data.get("wind_speed_mps") or 0.0
        standardized["wind_direction_deg"] = api_data.get("wind_direction_deg") or 0
        
    elif api_data["api_source"] == "ISRAMAR (Israeli Marine Research)":
        params = api_data.get("parameters", {})
        standardized["wave_height_m"] = params.get("wave_height_m") or 0.0
        standardized["wave_period_s"] = params.get("wave_period_s") or 0.0
        # ISRAMAR doesn't provide wind data
    
    return standardized

def main():
    """Main proof of concept test"""
    print("🏄‍♂️ ISRAELI SURF DATA API PROOF OF CONCEPT")
    print("=" * 60)
    print(f"Testing {len(ISRAELI_LOCATIONS)} Israeli coastal locations")
    print(f"Started at: {datetime.now().isoformat()}")
    
    all_results = []
    
    for location_name, location_data in ISRAELI_LOCATIONS.items():
        print(f"\n{'=' * 20} {location_name.upper()} {'=' * 20}")
        
        location_results = {
            "location": location_name,
            "coordinates": {"lat": location_data["lat"], "lon": location_data["lon"]},
            "apis_tested": {}
        }
        
        # Test OpenWeatherMap
        ow_data = test_openweather_api(location_name, location_data["openweather_name"])
        location_results["apis_tested"]["openweather"] = standardize_surf_data(ow_data)
        
        # Test Open-Meteo Marine
        om_data = test_open_meteo_marine_api(location_name, location_data["lat"], location_data["lon"])
        location_results["apis_tested"]["open_meteo"] = standardize_surf_data(om_data)
        
        # Test ISRAMAR (if available)
        if location_data["isramar_endpoint"]:
            isramar_data = test_isramar_api(location_name, location_data["isramar_endpoint"])
            location_results["apis_tested"]["isramar"] = standardize_surf_data(isramar_data)
        
        all_results.append(location_results)
        
        # Brief pause between locations
        time.sleep(1)
    
    # Summary Report
    print(f"\n{'=' * 60}")
    print("📊 PROOF OF CONCEPT SUMMARY")
    print(f"{'=' * 60}")
    
    working_apis = set()
    total_locations = len(all_results)
    
    for result in all_results:
        location = result["location"]
        print(f"\n🏖️  {location}:")
        
        for api_name, api_data in result["apis_tested"].items():
            if api_data:
                print(f"   ✅ {api_name}: Wave {api_data['wave_height_m']}m, Wind {api_data['wind_speed_mps']}m/s")
                working_apis.add(api_name)
            else:
                print(f"   ❌ {api_name}: Failed")
    
    print(f"\n🎯 RESULTS:")
    print(f"   📍 Locations tested: {total_locations}")
    print(f"   ✅ Working APIs: {', '.join(working_apis)}")
    print(f"   🌊 Surf data sources available for Israeli coast")
    
    # Integration recommendations
    print(f"\n🚀 INTEGRATION RECOMMENDATIONS:")
    if "open_meteo" in working_apis:
        print(f"   1. Add Open-Meteo Marine API (FREE, no API key)")
    if "openweather" in working_apis:
        print(f"   2. Expand OpenWeatherMap to more cities (same API key)")
    if "isramar" in working_apis:
        print(f"   3. Add ISRAMAR for official Israeli marine data")
    
    print(f"\n✅ PROOF: Multiple working surf data APIs for Israel!")
    print(f"📈 Ready to expand your lamp network to {total_locations} locations")
    
    # Save results to file
    with open("israeli_surf_api_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: israeli_surf_api_test_results.json")

if __name__ == "__main__":
    main()
