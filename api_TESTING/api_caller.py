
import sys
import os
import requests
import json

# Add the project root to the Python path to allow importing from other directories
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Now we can import from web_and_database
from web_and_database.data_base import MULTI_SOURCE_LOCATIONS
from datetime import datetime

def get_compass_direction(degrees):
    """Convert degrees to compass direction"""
    if degrees == 'N/A' or degrees is None:
        return 'N/A'

    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = round(degrees / 22.5) % 16
    return directions[index]

def get_wave_height_description(height):
    """Get descriptive text for wave height"""
    if height < 0.3:
        return "Calm"
    elif height < 0.6:
        return "Small"
    elif height < 1.0:
        return "Moderate"
    elif height < 1.5:
        return "Large"
    elif height < 2.0:
        return "Very Large"
    else:
        return "Huge"

def format_time(time_str):
    """Format time string to be more readable"""
    if time_str == 'N/A' or not time_str:
        return 'N/A'

    try:
        # Extract hour from ISO format like "2025-09-23T14:00"
        time_part = time_str.split('T')[1] if 'T' in time_str else time_str
        hour = time_part.split(':')[0]
        return f"{hour}:00"
    except:
        return time_str

def print_wind_data(data):
    """Extract and display relevant wind data from OpenWeatherMap response"""
    print("    🌬️  WIND CONDITIONS")
    print("    " + "="*50)

    if 'wind' in data:
        wind = data['wind']
        speed = wind.get('speed', 0)
        direction = wind.get('deg', 'N/A')

        # Convert wind direction to compass
        compass_dir = get_compass_direction(direction) if direction != 'N/A' else 'N/A'

        print(f"    │ Speed:     {speed} m/s ({speed * 3.6:.1f} km/h)")
        print(f"    │ Direction: {direction}° ({compass_dir})")

        if 'gust' in wind:
            gust = wind.get('gust')
            print(f"    │ Gust:      {gust} m/s ({gust * 3.6:.1f} km/h)")

    if 'weather' in data and len(data['weather']) > 0:
        weather = data['weather'][0]
        print(f"    │ Conditions: {weather.get('description', 'N/A').title()}")

    if 'main' in data:
        main = data['main']
        temp_k = main.get('temp', 0)
        temp_c = temp_k - 273.15 if temp_k else 0
        print(f"    │ Temperature: {temp_c:.1f}°C ({temp_k}K)")
        print(f"    │ Pressure:   {main.get('pressure', 'N/A')} hPa")
        print(f"    │ Humidity:   {main.get('humidity', 'N/A')}%")

    print("    " + "="*50)

def print_wave_data(data):
    """Extract and display current wave data from Open-Meteo marine response"""
    print("    🌊  WAVE CONDITIONS")
    print("    " + "="*50)

    if 'hourly' not in data:
        print("    │ ❌ No wave data available")
        print("    " + "="*50)
        return

    hourly = data['hourly']
    times = hourly.get('time', [])
    if not times:
        print("    │ ❌ No time data available")
        print("    " + "="*50)
        return

    # Get current hour data (first entry is usually current)
    current_idx = 0
    current_time_str = times[current_idx] if times else "N/A"

    wave_heights = hourly.get('wave_height', [])
    wave_periods = hourly.get('wave_period', [])
    wave_directions = hourly.get('wave_direction', [])

    # Current conditions
    print(f"    │ Current Time: {format_time(current_time_str)}")

    if wave_heights and current_idx < len(wave_heights):
        height = wave_heights[current_idx]
        height_desc = get_wave_height_description(height)
        print(f"    │ Height:  {height} m ({height_desc})")

    if wave_periods and current_idx < len(wave_periods):
        period = wave_periods[current_idx]
        print(f"    │ Period:  {period} s")

    if wave_directions and current_idx < len(wave_directions):
        direction = wave_directions[current_idx]
        compass_dir = get_compass_direction(direction)
        print(f"    │ Direction: {direction}° ({compass_dir})")

    print("    │")
    print("    │ 📊 Next 6 Hours Forecast:")
    print("    │ ┌─────────────┬────────┐")
    print("    │ │    Time     │ Height │")
    print("    │ ├─────────────┼────────┤")

    for i in range(1, min(7, len(times))):
        if i < len(wave_heights):
            time_str = format_time(times[i]) if i < len(times) else "N/A"
            height = wave_heights[i] if i < len(wave_heights) else "N/A"
            print(f"    │ │ {time_str:11} │ {height:4} m │")

    print("    │ └─────────────┴────────┘")
    print("    " + "="*50)

def call_all_apis():
    """
    Iterates through MULTI_SOURCE_LOCATIONS, calls each API endpoint,
    and prints the response.
    """
    print("\n" + "🌊" * 20 + " SURF LAMP API TESTING " + "🌊" * 20)
    print("=" * 80)

    for location, sources in MULTI_SOURCE_LOCATIONS.items():
        print(f"\n📍 LOCATION: {location.upper()}")
        print("=" * 80)

        # Group sources by type for better organization
        wind_sources = [s for s in sources if s.get('type') == 'wind']
        wave_sources = [s for s in sources if s.get('type') == 'wave']
        other_sources = [s for s in sources if s.get('type') not in ['wind', 'wave']]

        # Process wind sources first
        for source in wind_sources:
            url = source.get("url")
            if not url:
                print(f"    ⚠️  Skipping wind source with no URL")
                continue

            print(f"    🌐 API Endpoint: {url}")
            process_api_call(source, url)

        # Then wave sources
        for source in wave_sources:
            url = source.get("url")
            if not url:
                print(f"    ⚠️  Skipping wave source with no URL")
                continue

            print(f"    🌐 API Endpoint: {url}")
            process_api_call(source, url)

        # Finally other sources
        for source in other_sources:
            url = source.get("url")
            if not url:
                print(f"    ⚠️  Skipping {source.get('type', 'unknown')} source with no URL")
                continue

            print(f"    🌐 API Endpoint ({source.get('type', 'N/A')}): {url}")
            process_api_call(source, url)

    print("\n" + "=" * 80)
    print("✅ API Testing Complete!")
    print("=" * 80)

def process_api_call(source, url):
    """Process a single API call and display formatted results"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        try:
            data = response.json()
            source_type = source.get('type', 'unknown')

            if source_type == 'wind':
                print_wind_data(data)
            elif source_type == 'wave':
                print_wave_data(data)
            else:
                print("    📄 Raw JSON Response:")
                print("    " + "="*50)
                print(json.dumps(data, indent=4))
                print("    " + "="*50)

        except json.JSONDecodeError:
            print("    📄 Non-JSON Response:")
            print("    " + "="*50)
            print(response.text)
            print("    " + "="*50)

    except requests.exceptions.RequestException as e:
        print("    ❌ API ERROR")
        print("    " + "="*50)
        print(f"    │ Could not retrieve data: {e}")
        print("    " + "="*50)

    print()

if __name__ == "__main__":
    call_all_apis()
