# Configuration for Background Processor
# Decoupled from web app dependencies

SURF_LOCATIONS = [
    "Hadera, Israel",
    "Tel Aviv, Israel", 
    "Ashdod, Israel",
    "Haifa, Israel",
    "Netanya, Israel",
    "Ashkelon, Israel",
    "Nahariya, Israel"
]

BRIGHTNESS_LEVELS = {
    'LOW': 0.05,
    'MID': 0.3,
    'HIGH': 1.0
}

# Threshold limits
THRESHOLD_LIMITS = {
    'WAVE_MIN': 0.0,
    'WAVE_MAX': 3.0,
    'WIND_MIN': 1.0,
    'WIND_MAX': 40.0
}
