# Location Endpoints Configuration

## Overview
`location_endpoints.json` is the **single source of truth** for surf data API endpoints.

**Performance:** Loaded once at startup, cached in memory forever. Scales to 10,000+ locations with zero overhead.

## File Structure

```json
{
  "Location Name": [
    {
      "url": "https://api-endpoint.com/...",
      "priority": 1,
      "type": "wave"
    },
    {
      "url": "https://fallback-endpoint.com/...",
      "priority": 2,
      "type": "wind"
    }
  ]
}
```

## Fields

- **url**: Full API endpoint URL (must include all query parameters)
- **priority**: Lower number = higher priority (1 = try first, 2 = fallback, etc.)
- **type**: Either `"wave"` or `"wind"`

## Priority-Based Fallback

The system tries sources in priority order until one succeeds:

```
Hadera, Israel:
1. Isramar wave API (priority 1) → Try first
2. Open-Meteo wave API (priority 2) → Fallback if Isramar fails
3. Open-Meteo wind API (priority 3) → Always fetch for wind data
```

## Wave Calculation Methods

**API Method (default):**
- Location has `"type": "wave"` sources
- Uses real wave data from marine APIs
- Example: Tel Aviv, Hadera

**Formula Method:**
- Location has NO wave sources (only wind)
- Calculates wave height from wind speed using formula
- Example: Eilat (Red Sea - limited wave data)

## Adding New Locations

### Step 1: Get Coordinates
Find latitude/longitude for the location (use Google Maps).

### Step 2: Construct API URLs

**Wave API (Open-Meteo Marine):**
```
https://marine-api.open-meteo.com/v1/marine?latitude=LAT&longitude=LON&hourly=wave_height,wave_period,wave_direction
```

**Wind API (Open-Meteo Forecast):**
```
https://api.open-meteo.com/v1/forecast?latitude=LAT&longitude=LON&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms
```

⚠️ **CRITICAL:** Always include `&wind_speed_unit=ms` for wind APIs!

### Step 3: Add to JSON

```json
{
  "New Beach, Country": [
    {
      "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0&longitude=34.0&hourly=wave_height,wave_period,wave_direction",
      "priority": 1,
      "type": "wave"
    },
    {
      "url": "https://api.open-meteo.com/v1/forecast?latitude=32.0&longitude=34.0&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms",
      "priority": 2,
      "type": "wind"
    }
  ]
}
```

### Step 4: Test & Deploy

```bash
# Test JSON is valid
python3 -c "import json; json.load(open('location_endpoints.json'))"

# Test loading works
python3 -c "import shared_config; print(shared_config.MULTI_SOURCE_LOCATIONS.keys())"

# Commit and push
git add location_endpoints.json
git commit -m "feat: add [Location Name] to supported locations"
git push
```

## Deployment

- **Web Service**: Auto-restarts on push (reads new config)
- **Background Processor**: Auto-restarts on push (reads new config)
- **No database migration needed** - pure configuration change

## Fallback Safety

If `location_endpoints.json` is missing or corrupt, `shared_config.py` falls back to hardcoded configuration in `_FALLBACK_MULTI_SOURCE_LOCATIONS`.

## API Endpoint Field Mappings

See `surf-lamp-processor/endpoint_configs.py` for how each API's response format is parsed.

Supported APIs:
- `marine-api.open-meteo.com` - Wave height, period, direction
- `api.open-meteo.com` - Wind speed/direction (10m height)
- `isramar.ocean.org.il` - Israeli Marine Data Center (Hadera only)

## Examples

### Coastal Location (API waves)
```json
"Netanya, Israel": [
  {"url": "https://marine-api.open-meteo.com/...", "priority": 1, "type": "wave"},
  {"url": "https://api.open-meteo.com/...", "priority": 2, "type": "wind"}
]
```

### Inland/Red Sea (Formula waves)
```json
"Eilat, Israel": [
  {"url": "https://api.open-meteo.com/...", "priority": 1, "type": "wind"}
]
```
(No wave source = automatic wind-to-wave formula calculation)

### High Reliability (Multiple Fallbacks)
```json
"Hadera, Israel": [
  {"url": "https://isramar.ocean.org.il/...", "priority": 1, "type": "wave"},
  {"url": "https://marine-api.open-meteo.com/...", "priority": 2, "type": "wave"},
  {"url": "https://api.open-meteo.com/...", "priority": 3, "type": "wind"}
]
```

## Future: Admin UI

Planned feature: Web-based admin panel to edit `location_endpoints.json` via UI (no manual JSON editing required).
