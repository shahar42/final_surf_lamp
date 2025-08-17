import requests

# Basic directory of coastal cities in Israel with lat/lon
COASTAL_CITIES = {
    "Hadera": (32.2719, 34.9182),
    "Tel Aviv": (32.0853, 34.7818),
    "Ashdod": (31.8014, 34.6435),
    "Netanya": (32.3215, 34.8532),
    "Haifa": (32.7940, 34.9896),
    "Nahariya": (33.006, 35.094),  # Example coords
    "Eilat": (29.5581, 34.9482),
    "Ashkelon": (31.6699, 34.5738),
    # Add more coastal cities as desired!
}

# Customize these URLs per dataset
MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_marine(city, lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,wave_period,wave_direction"
    }
    r = requests.get(MARINE_API_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("hourly", {})

def fetch_wind(city, lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m"
    }
    r = requests.get(FORECAST_API_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("hourly", {})

def get_surf_conditions():
    print("Fetching surf and wind conditions:\n" + "=" * 50)
    for city, (lat, lon) in COASTAL_CITIES.items():
        print(f"\n--- {city} (lat {lat}, lon {lon}) ---")
        try:
            marine = fetch_marine(city, lat, lon)
            wind = fetch_wind(city, lat, lon)
            print(f" Wave Height: {marine.get('wave_height', [None])[0]} m")
            print(f" Wave Period: {marine.get('wave_period', [None])[0]} s")
            print(f" Wave Direction: {marine.get('wave_direction', [None])[0]} °")
            print(f" Wind Speed: {wind.get('wind_speed_10m', [None])[0]} m/s")
            print(f" Wind Direction: {wind.get('wind_direction_10m', [None])[0]} °")
        except Exception as e:
            print(f"  Error fetching data for {city}: {e}")
    print("\n" + "=" * 50 + "\nAll conditions fetched! 🏁")

if __name__ == "__main__":
    get_surf_conditions()
