import requests
import json

API_ENDPOINTS = [
    {
        "city": "Hadera",
        "name": "Isramar - Hadera Wave Data",
        "url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json"
    },
    {
        "city": "Tel Aviv",
        "name": "Open-Meteo - Tel Aviv Wave Data",
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction"
    },
    {
        "city": "Tel Aviv",
        "name": "Open-Meteo - Tel Aviv Wind Data",
        "url": "https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818&hourly=wind_speed_10m,wind_direction_10m"
    },
    {
        "city": "Hadera",
        "name": "OpenWeatherMap - Hadera Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
    {
        "city": "Tel Aviv",
        "name": "OpenWeatherMap - Tel Aviv Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Tel+Aviv&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
    {
        "city": "Ashdod",
        "name": "OpenWeatherMap - Ashdod Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
    {
        "city": "Ashdod",
        "name": "Open-Meteo - Ashdod Wave Data",
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.7939&longitude=34.6328&hourly=wave_height,wave_period,wave_direction"
    },
    {
        "city": "Netanya",
        "name": "Open-Meteo - Netanya Wave Data",
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.321457&longitude=34.853195&hourly=wave_height,wave_period,wave_direction"
    },
    {
        "city": "Netanya",
        "name": "Open-Meteo - Netanya Wind Data",
        "url": "https://api.open-meteo.com/v1/forecast?latitude=32.321457&longitude=34.853195&hourly=wind_speed_10m,wind_direction_10m"
    },
    {
        "city": "Netanya",
        "name": "OpenWeatherMap - Netanya Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Netanya&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
    {
        "city": "Haifa",
        "name": "Open-Meteo - Haifa Wave Data",
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.794044&longitude=34.989571&hourly=wave_height,wave_period,wave_direction"
    },
    {
        "city": "Haifa",
        "name": "Open-Meteo - Haifa Wind Data",
        "url": "https://api.open-meteo.com/v1/forecast?latitude=32.794044&longitude=34.989571&hourly=wind_speed_10m,wind_direction_10m"
    },
    {
        "city": "Haifa",
        "name": "OpenWeatherMap - Haifa Weather",
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Haifa&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    },
]

def get_surf_conditions():
    """
    Fetches and displays surf and wind conditions for multiple cities from various APIs.
    """
    print("🏄‍♂️ Fetching Surf and Wind Conditions 🏄‍♀️")
    print("=" * 50)

    city_data = {}

    for endpoint in API_ENDPOINTS:
        city = endpoint["city"]
        if city not in city_data:
            city_data[city] = {}

        try:
            response = requests.get(endpoint['url'], timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()

            if "Isramar" in endpoint["name"]:
                for param in data.get("parameters", []):
                    if param.get("name") == "Significant wave height":
                        city_data[city]["wave_height"] = param.get("values", [None])[0]
                    elif param.get("name") == "Peak wave period":
                        city_data[city]["wave_period"] = param.get("values", [None])[0]
            elif "Open-Meteo" in endpoint["name"] and "Wave" in endpoint["name"]:
                hourly_data = data.get("hourly", {})
                city_data[city]["wave_height"] = hourly_data.get("wave_height", [None])[0]
                city_data[city]["wave_period"] = hourly_data.get("wave_period", [None])[0]
                city_data[city]["wave_direction"] = hourly_data.get("wave_direction", [None])[0]
            elif "Open-Meteo" in endpoint["name"] and "Wind" in endpoint["name"]:
                hourly_data = data.get("hourly", {})
                city_data[city]["wind_speed"] = hourly_data.get("wind_speed_10m", [None])[0]
                city_data[city]["wind_direction"] = hourly_data.get("wind_direction_10m", [None])[0]
            elif "OpenWeatherMap" in endpoint["name"]:
                wind_data = data.get("wind", {})
                city_data[city]["wind_speed"] = wind_data.get("speed")
                city_data[city]["wind_direction"] = wind_data.get("deg")

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data for {endpoint['name']}: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing data for {endpoint['name']}: {e}")

    for city, data in city_data.items():
        print(f"\n--- {city} ---")
        print(f"  Wave Height: {data.get('wave_height', 'N/A')} m")
        print(f"  Wave Period: {data.get('wave_period', 'N/A')} s")
        print(f"  Wave Direction: {data.get('wave_direction', 'N/A')} °")
        print(f"  Wind Speed: {data.get('wind_speed', 'N/A')} m/s")
        print(f"  Wind Direction: {data.get('wind_direction', 'N/A')} °")

    print("\n" + "=" * 50)
    print("🏁 All conditions fetched! 🏁")


if __name__ == "__main__":
    get_surf_conditions()