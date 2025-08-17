import requests
import os
import json
from datetime import datetime

# List of coastal California cities with lat/lon and Spitcast counties
cities = {
    "San Francisco": {"lat": 37.7749, "lon": -122.4194, "spitcast_county": "san-francisco"},
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "spitcast_county": "los-angeles"},
    "San Diego": {"lat": 32.7157, "lon": -117.1611, "spitcast_county": "san-diego"},
    "Santa Barbara": {"lat": 34.4208, "lon": -119.6982, "spitcast_county": "santa-barbara"},
    "Monterey": {"lat": 36.6002, "lon": -121.8947, "spitcast_county": "monterey"},
    "Santa Cruz": {"lat": 36.9741, "lon": -122.0308, "spitcast_county": "santa-cruz"},
    "Long Beach": {"lat": 33.7701, "lon": -118.1937, "spitcast_county": "los-angeles"},
    "Huntington Beach": {"lat": 33.6603, "lon": -117.9992, "spitcast_county": "orange-county"},
    "Newport Beach": {"lat": 33.6189, "lon": -117.9298, "spitcast_county": "orange-county"},
    "Laguna Beach": {"lat": 33.5422, "lon": -117.7831, "spitcast_county": "orange-county"},
    "Malibu": {"lat": 34.0259, "lon": -118.7798, "spitcast_county": "los-angeles"},
    "Ventura": {"lat": 34.2805, "lon": -119.2932, "spitcast_county": "ventura"},
    "Oceanside": {"lat": 33.1959, "lon": -117.3795, "spitcast_county": "san-diego"},
    "Carlsbad": {"lat": 33.1581, "lon": -117.3506, "spitcast_county": "san-diego"},
    "Encinitas": {"lat": 33.0370, "lon": -117.2920, "spitcast_county": "san-diego"},
}

# API configs (JSON-only endpoints)
apis = {
    "open_meteo": {
        "marine_endpoint": lambda city: f"https://marine-api.open-meteo.com/v1/marine?latitude={city['lat']}&longitude={city['lon']}&hourly=wave_height,wave_period",
        "forecast_endpoint": lambda city: f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&hourly=wind_speed_10m,wind_direction_10m",
        "params": ["wave_height", "wave_period", "wind_speed_10m", "wind_direction_10m"],
    },
    "spitcast": {
        "surf_endpoint": lambda city: f"https://api.spitcast.com/api/county/spots/{city['spitcast_county']}/",
        "wind_endpoint": lambda city: f"https://api.spitcast.com/api/county/wind/{city['spitcast_county']}/",
        "params": ["height", "period", "speed", "direction_text"],
    },
    "stormglass": {
        "endpoint": lambda city: f"https://api.stormglass.io/v2/weather/point?lat={city['lat']}&lng={city['lon']}&params=waveHeight,wavePeriod,windSpeed,windDirection&source=noaa",
        "params": ["waveHeight", "wavePeriod", "windSpeed", "windDirection"],
        "key": os.getenv("STORMGLASS_KEY"),
    },
    "xweather": {
        "endpoint": lambda city: f"https://data.api.xweather.com/maritime/point?lat={city['lat']}&lon={city['lon']}&client_id={os.getenv('XWEATHER_ID')}&client_secret={os.getenv('XWEATHER_SECRET')}",
        "params": ["significantWaveHeightM", "primaryWavePeriod", "wind_speed", "wind_dir"],
        "key": os.getenv("XWEATHER_ID"),
    }
}

def fetch_data(endpoint, retries=1):
    for _ in range(retries + 1):
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching {endpoint}: {e}")
            continue
    return None

def check_params(data, required_params, api_name):
    if not data:
        return set(), {}
    found = set()
    sample_data = {}
    if api_name == "open_meteo":
        if "hourly" in data and all(p in data["hourly"] for p in required_params):
            if all(data["hourly"][p] and any(v for v in data["hourly"][p]) for p in required_params):
                found = set(required_params)
                sample_data = {p: data["hourly"][p][0] for p in required_params if data["hourly"][p]}
    elif api_name == "spitcast":
        if isinstance(data, list) and data:
            for item in data:
                for param in required_params:
                    if param in item and item[param] not in [None, "", 0]:
                        found.add(param)
                        sample_data[param] = item[param]
    elif api_name in ["stormglass", "xweather"]:
        if isinstance(data, dict) and "hours" in data and data["hours"]:
            latest = data["hours"][0]
            for param in required_params:
                if param in latest and latest[param] not in [None, "", 0]:
                    found.add(param)
                    sample_data[param] = latest[param]
    return found, sample_data

def test_api(city, api_name, api_config):
    sample_data = {}
    if api_name == "open_meteo":
        marine_data = fetch_data(api_config["marine_endpoint"](city))
        forecast_data = fetch_data(api_config["forecast_endpoint"](city))
        combined_data = {"hourly": {**marine_data.get("hourly", {}), **forecast_data.get("hourly", {})}} if marine_data and forecast_data else {}
        found, sample = check_params(combined_data, api_config["params"], api_name)
        endpoint = [api_config["marine_endpoint"](city), api_config["forecast_endpoint"](city)]
        if found:
            sample_data = {
                "wave_height": sample.get("wave_height"),
                "wave_period": sample.get("wave_period"),
                "wind_speed": sample.get("wind_speed_10m"),
                "wind_direction": sample.get("wind_direction_10m")
            }
    elif api_name == "spitcast":
        spots_data = fetch_data(api_config["surf_endpoint"](city))
        if not spots_data or not isinstance(spots_data, list) or not spots_data:
            print(f"Spitcast failed for {city['spitcast_county']}: No spots found")
            return set(), [], {}
        spot_id = spots_data[0].get("spot_id")
        spot_name = spots_data[0].get("spot_name", "Unknown")
        forecast_endpoint = f"https://api.spitcast.com/api/spot/forecast/{spot_id}/"
        forecast_data = fetch_data(forecast_endpoint)
        wind_data = fetch_data(api_config["wind_endpoint"](city))
        combined_data = (forecast_data or []) + (wind_data or [])
        found, sample = check_params(combined_data, api_config["params"], api_name)
        endpoint = [forecast_endpoint, api_config["wind_endpoint"](city)]
        if found:
            sample_data = {
                "wave_height": sample.get("height"),
                "wave_period": sample.get("period"),
                "wind_speed": sample.get("speed"),
                "wind_direction": sample.get("direction_text"),
                "spot_name": spot_name
            }
    else:
        if "key" in api_config and not api_config["key"]:
            print(f"Skipping {api_name}: No API key provided")
            return set(), [], {}
        endpoint = api_config["endpoint"](city)
        data = fetch_data(endpoint)
        found, sample = check_params(data, api_config["params"], api_name)
        endpoint = [endpoint]
        if found:
            sample_data = {
                "wave_height": sample.get("waveHeight" if api_name == "stormglass" else "significantWaveHeightM"),
                "wave_period": sample.get("wavePeriod" if api_name == "stormglass" else "primaryWavePeriod"),
                "wind_speed": sample.get("windSpeed" if api_name == "stormglass" else "wind_speed"),
                "wind_direction": sample.get("windDirection" if api_name == "stormglass" else "wind_dir")
            }
    return found, endpoint, sample_data

def main():
    output_file = "successful_cities.json"
    results = []
    
    # Prompt for API keys if not set
    if not os.getenv("STORMGLASS_KEY"):
        os.environ["STORMGLASS_KEY"] = input("Enter Stormglass API key (or leave blank to skip): ")
    if not os.getenv("XWEATHER_ID"):
        os.environ["XWEATHER_ID"] = input("Enter Xweather client ID (or leave blank to skip): ")
        os.environ["XWEATHER_SECRET"] = input("Enter Xweather client secret (or leave blank to skip): ")

    for city_name, city_data in cities.items():
        print(f"Testing {city_name}...")
        all_params = {"wave_height", "wave_period", "wind_speed", "wind_direction"}
        successful_combos = []

        # Test all APIs, not stopping at first success
        for api_name in ["spitcast", "open_meteo", "stormglass", "xweather"]:
            api_config = apis[api_name]
            found, endpoints, sample_data = test_api(city_data, api_name, api_config)
            if found == set(api_config["params"]):
                successful_combos.append({
                    "apis": endpoints,
                    "parameters_covered": list(all_params),
                    "sample_data": {k: v for k, v in sample_data.items() if v is not None}
                })

        # Test pairs if fewer than 2 successes
        if len(successful_combos) < 2:
            api_list = list(apis.keys())
            for i in range(len(api_list)):
                for j in range(i + 1, len(api_list)):
                    api1, api2 = api_list[i], api_list[j]
                    found1, ep1, sample1 = test_api(city_data, api1, apis[api1])
                    found2, ep2, sample2 = test_api(city_data, api2, apis[api2])
                    combined_found = found1.union(found2)
                    if len(combined_found) >= len(all_params):
                        combined_sample = {**sample1, **sample2}
                        successful_combos.append({
                            "apis": ep1 + ep2,
                            "parameters_covered": list(all_params),
                            "sample_data": {k: v for k, v in combined_sample.items() if v is not None}
                        })

        # Add all successful combos (up to 2) to results
        results.extend(successful_combos[:2])

    # Write to JSON file
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()
