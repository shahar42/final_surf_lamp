#!/usr/bin/env python3
"""
Find the optimal parameter combination for Open-Meteo Marine API
Based on successful debug results, find maximum working parameters
"""

import requests
import json

def test_parameter_additions():
    """Gradually add parameters to find the maximum working combination"""
    print("🎯 FINDING OPTIMAL OPEN-METEO MARINE PARAMETERS")
    print("=" * 60)
    
    base_url = "https://marine-api.open-meteo.com/v1/marine"
    lat, lon = 32.0853, 34.7818  # Tel Aviv coordinates
    
    # Build parameters incrementally
    parameter_tests = [
        {
            "name": "1. Wave height only",
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height"}
        },
        {
            "name": "2. Add wave period", 
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period"}
        },
        {
            "name": "3. Add wave direction",
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period,wave_direction"}
        },
        {
            "name": "4. Add wind speed",
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period,wave_direction,wind_speed_10m"}
        },
        {
            "name": "5. Add wind direction",
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period,wave_direction,wind_speed_10m,wind_direction_10m"}
        },
        {
            "name": "6. Add timezone auto",
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period,wave_direction,wind_speed_10m,wind_direction_10m", "timezone": "auto"}
        },
        {
            "name": "7. Add forecast_days=1", 
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period,wave_direction,wind_speed_10m,wind_direction_10m", "timezone": "auto", "forecast_days": 1}
        },
        {
            "name": "8. Try forecast_days=7",
            "params": {"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period,wave_direction,wind_speed_10m,wind_direction_10m", "timezone": "auto", "forecast_days": 7}
        }
    ]
    
    last_working_params = None
    
    for test in parameter_tests:
        print(f"\n{test['name']}")
        print(f"   Parameters: {test['params']['hourly']}")
        if 'timezone' in test['params']:
            print(f"   Timezone: {test['params']['timezone']}")
        if 'forecast_days' in test['params']:
            print(f"   Forecast days: {test['params']['forecast_days']}")
        
        try:
            response = requests.get(base_url, params=test['params'], timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract and display sample data
                if 'hourly' in data:
                    sample_data = {}
                    for key, values in data['hourly'].items():
                        if key != 'time' and values:
                            sample_data[key] = values[0]  # First value
                    
                    print(f"   ✅ SUCCESS! Sample data: {sample_data}")
                    last_working_params = test['params'].copy()
                else:
                    print(f"   ⚠️  No hourly data in response")
                    
            else:
                print(f"   ❌ FAILED: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('reason', 'Unknown error')}")
                    break  # Stop at first failure
                except:
                    print(f"   Error text: {response.text[:100]}")
                    break
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            break
    
    return last_working_params

def test_all_israeli_cities(working_params):
    """Test the optimal parameters with all Israeli cities"""
    print(f"\n🌍 TESTING OPTIMAL PARAMETERS WITH ALL ISRAELI CITIES")
    print("=" * 60)
    
    israeli_cities = {
        "Tel Aviv": {"lat": 32.0853, "lon": 34.7818},
        "Hadera": {"lat": 32.4365, "lon": 34.9196}, 
        "Ashdod": {"lat": 31.7939, "lon": 34.6328},
        "Haifa": {"lat": 32.7940, "lon": 34.9896},
        "Netanya": {"lat": 32.3215, "lon": 34.8532}
    }
    
    base_url = "https://marine-api.open-meteo.com/v1/marine"
    successful_cities = []
    
    for city_name, coords in israeli_cities.items():
        print(f"\n🏖️  Testing {city_name}...")
        
        params = working_params.copy()
        params['latitude'] = coords['lat']
        params['longitude'] = coords['lon']
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'hourly' in data:
                    # Extract current surf conditions
                    surf_data = {}
                    for key, values in data['hourly'].items():
                        if key != 'time' and values and values[0] is not None:
                            surf_data[key] = values[0]
                    
                    print(f"   ✅ SUCCESS! Current conditions:")
                    if 'wave_height' in surf_data:
                        print(f"      🌊 Wave height: {surf_data['wave_height']}m")
                    if 'wave_period' in surf_data:
                        print(f"      ⏱️  Wave period: {surf_data['wave_period']}s")
                    if 'wind_speed_10m' in surf_data:
                        print(f"      💨 Wind speed: {surf_data['wind_speed_10m']} m/s")
                    
                    successful_cities.append(city_name)
                else:
                    print(f"   ⚠️  No hourly data")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    return successful_cities

def generate_integration_code(optimal_params, successful_cities):
    """Generate the code needed to integrate this into the main project"""
    print(f"\n🚀 INTEGRATION CODE GENERATION")
    print("=" * 60)
    
    print("✅ OPTIMAL PARAMETERS FOUND:")
    print(json.dumps(optimal_params, indent=2))
    
    print(f"\n✅ WORKING CITIES: {', '.join(successful_cities)}")
    
    print(f"\n📝 CODE TO ADD TO YOUR PROJECT:")
    print("=" * 40)
    
    # Generate the LOCATION_API_MAPPING update
    print("# Add to LOCATION_API_MAPPING in data_base.py:")
    print("WAVE_DATA_MAPPING = {")
    
    coordinates = {
        "Tel Aviv": {"lat": 32.0853, "lon": 34.7818},
        "Hadera": {"lat": 32.4365, "lon": 34.9196},
        "Ashdod": {"lat": 31.7939, "lon": 34.6328},
        "Haifa": {"lat": 32.7940, "lon": 34.9896},
        "Netanya": {"lat": 32.3215, "lon": 34.8532}
    }
    
    for city in successful_cities:
        if city in coordinates:
            coord = coordinates[city]
            
            # Build the URL with optimal parameters
            url = f"https://marine-api.open-meteo.com/v1/marine?latitude={coord['lat']}&longitude={coord['lon']}"
            url += f"&hourly={optimal_params['hourly']}"
            
            if 'timezone' in optimal_params:
                url += f"&timezone={optimal_params['timezone']}"
            if 'forecast_days' in optimal_params:
                url += f"&forecast_days={optimal_params['forecast_days']}"
                
            print(f'    "{city}, Israel": "{url}",')
    
    print("}")
    
    print(f"\n# Update endpoint_configs.py to handle Open-Meteo Marine format")
    print('# Add this to FIELD_MAPPINGS:')
    print('"open-meteo.com": {')
    print('    "wave_height_m": ["hourly", "wave_height", 0],')
    print('    "wave_period_s": ["hourly", "wave_period", 0],')
    print('    "wind_speed_mps": ["hourly", "wind_speed_10m", 0],')
    print('    "wind_direction_deg": ["hourly", "wind_direction_10m", 0]')
    print('}')

def main():
    """Main function to find optimal Open-Meteo Marine parameters"""
    
    # Step 1: Find optimal parameter combination
    optimal_params = test_parameter_additions()
    
    if optimal_params:
        print(f"\n🎯 OPTIMAL PARAMETERS FOUND!")
        print(json.dumps(optimal_params, indent=2))
        
        # Step 2: Test with all Israeli cities
        successful_cities = test_all_israeli_cities(optimal_params)
        
        # Step 3: Generate integration code
        generate_integration_code(optimal_params, successful_cities)
        
        print(f"\n🎉 CONCLUSION:")
        print(f"✅ Open-Meteo Marine API works for {len(successful_cities)} Israeli cities!")
        print(f"✅ Free wave data available for all coastal locations!")
        print(f"✅ Ready to integrate into your surf lamp system!")
        
    else:
        print(f"\n❌ No working parameters found")

if __name__ == "__main__":
    main()
