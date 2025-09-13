# Surf Lamp System Documentation

## Overview
The Surf Lamp system displays real-time surf conditions using LED visualizations on Arduino-based devices. The system consists of a web dashboard, background data processor, and Arduino firmware that work together to fetch, process, and display surf data.

## Architecture

### Core Components

1. **Web Application** (`web_and_database/app.py`)
   - Flask-based dashboard and API server
   - User authentication and session management
   - Arduino data endpoint for pull-based architecture
   - Location-aware configuration system

2. **Background Processor** (`surf-lamp-processor/background_processor.py`)
   - Fetches data from external surf APIs every 30 minutes
   - Processes and stores data in database
   - Supports multi-source API configurations per location

3. **Arduino Firmware** (`arduino/arduinomain_lamp.ino`)
   - ESP32-based device that pulls data from server every 31 minutes
   - Controls LED strips for visual surf condition display
   - Implements threshold-based blinking alerts

4. **Database Schema** (defined in `web_and_database/data_base.py`)
   - PostgreSQL database with user accounts, lamps, and surf conditions
   - Dynamic location-to-API endpoint mapping

## Data Flow

```
External APIs → Background Processor → Database → Web API → Arduino → LED Display
     ↓                ↓                    ↓         ↓         ↓
   30min           Every 30min         Real-time   31min   Immediate
```

### Detailed Flow
1. **Background Processor** runs every 30 minutes (`PROCESS_INTERVAL = 30 minutes`)
2. Fetches data from location-specific APIs defined in `MULTI_SOURCE_LOCATIONS`
3. Stores processed data in `current_conditions` table
4. **Arduino** pulls data every 31 minutes (`FETCH_INTERVAL = 1860000ms`)
5. **Arduino** updates LED display immediately upon receiving data

## Location System (Dynamic)

**File:** `web_and_database/data_base.py:227-312`

The system uses a dynamic location mapping where each location has specific API endpoints with coordinates:

```python
MULTI_SOURCE_LOCATIONS = {
    "Tel Aviv, Israel": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": "https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818&hourly=wind_speed_10m,wind_direction_10m",
            "priority": 2,
            "type": "wind"
        }
    ],
    # ... other locations
}
```

### Location Change Process
**Function:** `update_user_location()` in `data_base.py:467-540`

When user changes location in dashboard:
1. Updates `users.location` field
2. Deletes existing `usage_lamps` records for the lamp
3. Creates new `usage_lamps` records with new location's API endpoints
4. Background processor automatically picks up new endpoints
5. Arduino receives new location data within 31 minutes

## Arduino LED System

### LED Configuration
**File:** `arduino/arduinomain_lamp.ino:16-26`
```cpp
#define LED_PIN_CENTER 4        // Wind speed + direction
#define LED_PIN_SIDE 2          // Wave height (right strip)
#define LED_PIN_SIDE_LEFT 5     // Wave period (left strip)

#define NUM_LEDS_RIGHT 9        // Wave height LEDs
#define NUM_LEDS_LEFT 9         // Wave period LEDs
#define NUM_LEDS_CENTER 12      // Wind speed + direction LEDs
```

### Wind Direction Colors
**Function:** `setWindDirection()` in `arduinomain_lamp.ino:235-248`
```cpp
// Wind direction color coding (based on LED 11 - the top LED)
if (windDirection < 45 || windDirection >= 315) {
    leds_center[northLED] = CRGB::Green;   // North - Green
} else if (windDirection >= 45 && windDirection < 135) {
    leds_center[northLED] = CRGB::Yellow;  // East - Yellow
} else if (windDirection >= 135 && windDirection < 225) {
    leds_center[northLED] = CRGB::Red;     // South - Red
} else if (windDirection >= 225 && windDirection < 315) {
    leds_center[northLED] = CRGB::Blue;    // West - Blue
}
```

### Threshold Alerts
**Functions:** `applyWindSpeedThreshold()` and `applyWaveHeightThreshold()` in `arduinomain_lamp.ino:212-233`

- **Wave Height Alert:** When `wave_height_cm >= wave_threshold_cm` → Blue LEDs blink
- **Wind Speed Alert:** When `wind_speed_knots >= wind_speed_threshold_knots` → White LEDs blink
- **Blinking:** Smooth sine wave pulsing (not harsh on/off)

### Data Processing
**Function:** `updateSurfDisplay()` in `arduinomain_lamp.ino:633-654`

LED calculations:
```cpp
int windSpeedLEDs = constrain(static_cast<int>(windSpeed * (1.94384 / 2.0)) + 1, 0, NUM_LEDS_CENTER - 2);
int waveHeightLEDs = constrain(static_cast<int>(waveHeight_cm / 25) + 1, 0, NUM_LEDS_RIGHT);
int wavePeriodLEDs = constrain(static_cast<int>(wavePeriod), 0, NUM_LEDS_LEFT);
```

## API Endpoints

### Arduino Data Endpoint
**Route:** `GET /api/arduino/<arduino_id>/data`
**File:** `web_and_database/app.py:762-817`

Returns surf data formatted for Arduino consumption:
```json
{
    "wave_height_cm": 40,
    "wave_period_s": 5.2,
    "wind_speed_mps": 3,
    "wind_direction_deg": 340,
    "wave_threshold_cm": 100,
    "wind_speed_threshold_knots": 22,
    "last_updated": "2025-09-13T16:48:53.253866",
    "data_available": true
}
```

### Key Features:
- Pulls user's personal thresholds from database
- Converts wave height from meters to centimeters
- Rounds wind speed to integers
- Returns safe defaults if no data available

## Database Schema

### Core Tables
**File:** `web_and_database/data_base.py:74-223`

```sql
-- Users table
users (
    user_id PRIMARY KEY,
    username UNIQUE,
    email UNIQUE,
    location,                    -- Dynamic location (e.g., "Tel Aviv, Israel")
    wave_threshold_m FLOAT,      -- User's wave height alert threshold
    wind_threshold_knots FLOAT   -- User's wind speed alert threshold
)

-- Lamps table
lamps (
    lamp_id PRIMARY KEY,
    user_id FOREIGN KEY,
    arduino_id UNIQUE,           -- Physical Arduino device ID
    arduino_ip                   -- Arduino's network IP address
)

-- Current surf conditions
current_conditions (
    lamp_id PRIMARY KEY,
    wave_height_m FLOAT,
    wave_period_s FLOAT,
    wind_speed_mps FLOAT,
    wind_direction_deg INTEGER,
    last_updated TIMESTAMP
)

-- API endpoint configurations (enables dynamic location system)
usage_lamps (
    usage_id,
    lamp_id,
    http_endpoint TEXT,          -- Full API URL with coordinates
    endpoint_priority INTEGER   -- 1=highest priority (wave data), 2=wind data
)
```

## Timing and Synchronization

### Update Intervals
- **Background Processor:** Every 30 minutes (defined in `background_processor.py:743`)
- **Arduino Fetch:** Every 31 minutes (`FETCH_INTERVAL = 1860000ms` in Arduino code)
- **Dashboard Updates:** Real-time (when user refreshes)

### Threshold Change Propagation
1. User changes threshold in dashboard → Database update (immediate)
2. Next Arduino fetch cycle → Sees new threshold (up to 31 minutes)
3. Arduino applies new threshold logic → LED behavior changes

## Configuration Files

### API Field Mappings
**File:** `surf-lamp-processor/endpoint_configs.py`

Defines how to extract data from different API responses:
```python
FIELD_MAPPINGS = {
    "marine-api.open-meteo.com": {
        "wave_height_m": ["hourly", "wave_height", 0],
        "wave_period_s": ["hourly", "wave_period", 0],
        "wave_direction_deg": ["hourly", "wave_direction", 0]
    },
    "api.open-meteo.com": {
        "wind_speed_mps": ["hourly", "wind_speed_10m", 0],
        "wind_direction_deg": ["hourly", "wind_direction_10m", 0]
    }
}
```

### Server Discovery
**File:** `arduino/ServerDiscovery.h`

Arduino uses discovery system to find API server:
1. Tries GitHub Pages config: `https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
2. Falls back to hardcoded servers
3. Caches discovered server for 24 hours

## Error Handling and Resilience

### Arduino Resilience
- **WiFi Connection:** Auto-reconnect every 30 seconds if disconnected
- **AP Mode:** Creates setup hotspot if WiFi fails (60-second timeout)
- **Data Fetch:** Continues with cached data if server unreachable

### Background Processor
- **Database Reconnection:** Tests connection before each cycle
- **API Failures:** Continues with other endpoints if one fails
- **Partial Data:** Stores whatever data was successfully fetched

### Web Application
- **Rate Limiting:** Prevents authentication abuse
- **Session Management:** Secure user sessions with timeout
- **Database Transactions:** Atomic operations for data consistency

## Development and Debugging

### Log Locations
- **Background Processor:** `surf-lamp-processor/lamp_processor.log`
- **Web Application:** Console/stdout (configured in app.py:25-27)
- **Arduino:** Serial Monitor (115200 baud)

### Debug Endpoints
- **Manual Fetch:** `GET http://<arduino_ip>/api/fetch` - Forces immediate data fetch
- **LED Test:** `GET http://<arduino_ip>/api/led-test` - Tests all LED strips
- **Status:** `GET http://<arduino_ip>/api/status` - Arduino health check

### Key Debug Information
Arduino Serial Output includes:
```
🐛 DEBUG: Wind direction = 340°
🎨 LEDs Updated - Wind: 3, Wave: 2, Period: 5, Direction: 340°
```

## Security Considerations

### Authentication
- **Password Hashing:** bcrypt with salt (implemented in app.py:56)
- **Session Security:** Flask sessions with SECRET_KEY
- **Rate Limiting:** Login attempts limited (app.py:64-71)

### Network Security
- **HTTPS:** Arduino uses TLS for API calls (`client.setInsecure()` - production should use proper certs)
- **API Keys:** Stored securely in database, not hardcoded
- **Input Validation:** Form validation on all user inputs

## Supported Locations

**Current Coverage:** (from `web_and_database/data_base.py:227-311`)
- Tel Aviv, Israel (32.0853, 34.7818)
- Hadera, Israel (32.4365, 34.9196)
- Ashdod, Israel (31.7939, 34.6328)
- Haifa, Israel (32.7940, 34.9896)
- Netanya, Israel (32.3215, 34.8532)
- Nahariya, Israel (33.006, 35.094)
- Ashkelon, Israel (31.6699, 34.5738)

**Adding New Locations:**
1. Add coordinates to `MULTI_SOURCE_LOCATIONS` in `data_base.py`
2. Add location name to `SURF_LOCATIONS` in `app.py:78-86`
3. System automatically configures API endpoints for new users

## Common Issues and Solutions

### Arduino Not Updating
1. **Check Arduino IP:** Ensure `arduino_ip` field in database is correct
2. **Check Background Processor:** Verify lamp_id is being processed in logs
3. **Manual Fetch:** Use `/api/fetch` endpoint to force immediate update

### Wrong Location Data
1. **Check API Endpoints:** Verify `usage_lamps` table has correct coordinates
2. **Location Change:** Use dashboard to change location (triggers endpoint update)
3. **Database Consistency:** Ensure `usage_lamps` matches user's location setting

### LED Colors Wrong
1. **Check Wind Direction:** Verify value received in Arduino serial debug
2. **Check Calculations:** Wind direction ranges in `setWindDirection()` function
3. **LED Indexing:** Ensure `NUM_LEDS_CENTER - 1` points to correct LED

This documentation reflects the actual implementation as found in the codebase and should prevent future architectural misunderstandings.