# Adding a New Location to Surf Lamp System

## Required Changes (2 files only)

### 1. Update Location List
**File:** `web_and_database/app.py`

Add your new location to the `SURF_LOCATIONS` array:
```python
SURF_LOCATIONS = [
    "Hadera, Israel",
    "Tel Aviv, Israel", 
    "Ashdod, Israel",
    "Haifa, Israel",
    "Netanya, Israel",
    "Your New City, Country"  # Add here
]
```

### 2. Configure API Endpoints
**File:** `web_and_database/data_base.py`

Add API configuration to `MULTI_SOURCE_LOCATIONS`:
```python
MULTI_SOURCE_LOCATIONS = {
    # ... existing locations ...
    "Your New City, Country": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=LAT&longitude=LON&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": "https://api.open-meteo.com/v1/forecast?latitude=LAT&longitude=LON&hourly=wind_speed_10m,wind_direction_10m",
            "priority": 2,
            "type": "wind"
        }
    ]
}
```

**Replace LAT and LON with actual coordinates** (e.g., `32.0853` and `34.7818`)

## Getting Coordinates

Use any of these methods:
- **Google Maps:** Right-click location → coordinates
- **Wikipedia:** City pages usually list coordinates
- **GPS tools:** Any GPS app or website

## Example: Adding Barcelona, Spain
```python
# In app.py
SURF_LOCATIONS = [
    # ... existing cities ...
    "Barcelona, Spain"
]

# In data_base.py
"Barcelona, Spain": [
    {
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=41.3851&longitude=2.1734&hourly=wave_height,wave_period,wave_direction",
        "priority": 1,
        "type": "wave"
    },
    {
        "url": "https://api.open-meteo.com/v1/forecast?latitude=41.3851&longitude=2.1734&hourly=wind_speed_10m,wind_direction_10m",
        "priority": 2,
        "type": "wind"
    }
]
```

## That's It!

- **No database changes needed** - handled automatically
- **No Arduino changes needed** - same data format
- **No processor changes needed** - uses existing endpoint configs
- **Users can immediately** select the new location during registration

## Testing New Location

1. Deploy changes
2. Register a test account with the new location
3. Check background processor logs for API calls
4. Verify dashboard shows surf data

**Time required:** 5 minutes to add, 10 minutes to test
