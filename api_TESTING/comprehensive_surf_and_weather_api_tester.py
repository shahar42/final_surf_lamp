import requests
import json

# A list of all unique API endpoints used in your project
API_ENDPOINTS = [
    {
        "name": "Isramar - Hadera Wave Data",
        "url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json"
    },
    {
        "name": "Open-Meteo - Tel Aviv Wave Data",
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction"
    },
    {
        "name": "Open-Meteo - Tel Aviv Wind Data",
        "url": "https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818&hourly=wind_speed_10m,wind_direction_10m"
    },
    {
        "name": "OpenWeatherMap - Hadera Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
    {
        "name": "OpenWeatherMap - Tel Aviv Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Tel+Aviv&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
    {
        "name": "OpenWeatherMap - Ashdod Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
]

def test_api_endpoints():
    """
    Iterates through the list of API endpoints, tests each one,
    and prints the results to the console.
    """
    print("🌊 Starting Surf Lamp API Endpoint Test 🌊")
    print("=" * 50)

    for i, endpoint in enumerate(API_ENDPOINTS, 1):
        print(f"\n({i}/{len(API_ENDPOINTS)}) Testing: {endpoint['name']}...")
        
        try:
            # Make the HTTP GET request with a 10-second timeout
            response = requests.get(endpoint['url'], timeout=10)

            # Check the HTTP status code
            if response.status_code == 200:
                print(f"✅ SUCCESS (Status: {response.status_code})")
                
                # Try to parse the JSON to confirm it's valid
                try:
                    data = response.json()
                    # Convert the first 200 characters of the JSON data to a string for preview
                    json_preview = json.dumps(data, indent=2)[:200]
                    print(f"   Response Preview: \n{json_preview}...")
                except json.JSONDecodeError:
                    print("   ⚠️  Warning: Response is not valid JSON.")

            else:
                print(f"❌ FAILED (Status: {response.status_code})")
                print(f"   Response Text: {response.text[:150]}")

        except requests.exceptions.RequestException as e:
            print(f"❌ FAILED (Error)")
            print(f"   An error occurred: {e}")
        
        print("-" * 40)

    print("\n🏁 Test Complete! 🏁")


if __name__ == "__main__":
    test_api_endpoints()
