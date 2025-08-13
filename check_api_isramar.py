import requests
import json

def get_weather_and_wave_data():
    """
    Fetches weather and wave data from specified endpoints and prints the results.
    """
    weather_url = "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    wave_url = "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json"

    # --- Fetch Weather Data ---
    try:
        print("Fetching weather data for Hadera...")
        weather_response = requests.get(weather_url)
        # This will raise an exception if the request returned an error status code
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        print("\n--- Weather Data ---")
        print(json.dumps(weather_data, indent=4))

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching weather data: {e}")
    except json.JSONDecodeError:
        print("Failed to decode the JSON response from the weather API.")

    # --- Fetch Wave Data ---
    try:
        print("\nFetching wave data for Hadera...")
        wave_response = requests.get(wave_url)
        wave_response.raise_for_status()
        wave_data = wave_response.json()

        print("\n--- Wave Data ---")
        print(json.dumps(wave_data, indent=4))

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching wave data: {e}")
    except json.JSONDecodeError:
        print("Failed to decode the JSON response from the wave API.")

if __name__ == "__main__":
    get_weather_and_wave_data()
