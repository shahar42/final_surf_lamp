# endpoint_configs.py
"""
Field mapping configurations for different surf data API endpoints.
Maps API-specific field names to our standardized surf data format.
"""

FIELD_MAPPINGS = {
    # OpenWeatherMap API
    "openweathermap.org": {
        "wind_speed_mps": ["wind", "speed"],
        "wind_direction_deg": ["wind", "deg"], 
        "location": ["name"],
        "temperature_c": ["main", "temp"],
        "humidity_percent": ["main", "humidity"],
        "fallbacks": {
            "wave_height_m": 0.0,  # OpenWeatherMap doesn't provide wave data
            "wave_period_s": 0.0,
            "wind_speed_mps": 0.0,
            "wind_direction_deg": 0
        },
        "conversions": {
            "temperature_c": lambda x: x - 273.15  # Kelvin to Celsius
        }
    },
    
    # Israeli Marine Data (Isramar) - FIXED STRUCTURE
    "isramar.ocean.org.il": {
        # Custom extraction function for complex structure
        "custom_extraction": True,
        "fallbacks": {
            "wind_speed_mps": 0.0,  # Isramar focuses on wave data
            "wind_direction_deg": 0,
            "wave_height_m": 0.0,
            "wave_period_s": 0.0
        }
    },
    
    # Open-Meteo Marine API
    "open-meteo.com": {
        "wave_height_m": ["hourly", "wave_height", 0],
        "wave_period_s": ["hourly", "wave_period", 0], 
        "wave_direction_deg": ["hourly", "wave_direction", 0],
        "wind_speed_mps": 0.0,  # Fallback - Open-Meteo Marine doesn't provide wind in this config
        "wind_direction_deg": 0,  # Fallback
        "fallbacks": {
            "wind_speed_mps": 0.0,
            "wind_direction_deg": 0
        }
    },

    # ADD THIS NEW MAPPING:
    "api.open-meteo.com": {
        "wind_speed_mps": ["hourly", "wind_speed_10m", 0],
        "wind_direction_deg": ["hourly", "wind_direction_10m", 0],
        "fallbacks": {
            "wave_height_m": 0.0,
            "wave_period_s": 0.0,
            "wave_direction_deg": 0,
            "wind_speed_mps": 0.0,
            "wind_direction_deg": 0
        }
    },
}

def extract_isramar_data(raw_data):
    """
    Custom extraction function for Isramar's complex JSON structure.
    
    Expected structure:
    {
      "parameters": [
        {"name": "Significant wave height", "units": "m", "values": [0.41]},
        {"name": "Peak wave period", "units": "s", "values": [3.5]}
      ]
    }
    """
    extracted = {
        "wave_height_m": 0.0,
        "wave_period_s": 0.0,
        "wind_speed_mps": 0.0,
        "wind_direction_deg": 0
    }
    
    if "parameters" not in raw_data:
        return extracted
    
    for param in raw_data["parameters"]:
        name = param.get("name", "")
        values = param.get("values", [])
        
        if not values:  # Skip if no values
            continue
            
        # Extract wave height
        if "Significant wave height" in name:
            extracted["wave_height_m"] = float(values[0])
        
        # Extract wave period  
        elif "Peak wave period" in name:
            extracted["wave_period_s"] = float(values[0])
    
    return extracted

def get_endpoint_config(endpoint_url):
    """
    Get the field mapping configuration for a given endpoint URL.
    
    Args:
        endpoint_url (str): The API endpoint URL
        
    Returns:
        dict: Field mapping configuration or None if not found
    """
    for endpoint_key, config in FIELD_MAPPINGS.items():
        if endpoint_key in endpoint_url:
            return config
    return None

def list_supported_endpoints():
    """
    Get a list of all supported endpoint domains.
    
    Returns:
        list: List of supported endpoint domain strings
    """
    return list(FIELD_MAPPINGS.keys())

# Example usage and testing
if __name__ == "__main__":
    # Test endpoint matching
    test_urls = [
        "http://api.openweathermap.org/data/2.5/weather?q=Hadera",
        "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json",
        "https://unknown-api.com/data"
    ]
    
    for url in test_urls:
        config = get_endpoint_config(url)
        if config:
            print(f"✅ {url} -> Found config with {len(config)} mappings")
        else:
            print(f"❌ {url} -> No config found")
    
    # Test Isramar extraction
    test_data = {
        "datetime": "2025-08-14 17:00 UTC",
        "parameters": [
            {"name": "Significant wave height", "units": "m", "values": [0.41]},
            {"name": "Peak wave period", "units": "s", "values": [3.5]}
        ]
    }
    
    result = extract_isramar_data(test_data)
    print(f"\n✅ Isramar extraction test:")
    print(f"   Wave height: {result['wave_height_m']}m")
    print(f"   Wave period: {result['wave_period_s']}s")
