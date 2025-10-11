# Arduino Lamps - Technical Documentation

## 1. Overview

**What it does**: ESP32 microcontrollers with WS2812B addressable LED strips that visualize real-time surf conditions through color-coded lighting patterns, polling the web server every 13 minutes for location-based wave and wind data.


## 2. Technical Details

### Critical Assumptions

**API Assumptions**:
- `/api/arduino/{ARDUINO_ID}/data` endpoint returns JSON with exact keys: `wave_height_cm`, `wave_period_s`, `wind_speed_mps`, `wind_direction_deg`, `wave_threshold_cm`, `wind_speed_threshold_knots`, `quiet_hours_active`, `led_theme`
- Server responds within 15 seconds (HTTP_TIMEOUT_MS)
- HTTPS endpoints work with `client.setInsecure()` (certificate validation disabled)

**Network Assumptions**:
- WiFi credentials stored in NVS (non-volatile storage) persist across reboots
- WiFi reconnects automatically after disconnections (30-second retry interval)
- ServerDiscovery GitHub URLs remain accessible (GitHub Pages, raw.githubusercontent.com)
- 13-minute polling interval won't be blocked by network firewalls

**Timing Assumptions**:
- Background processor updates database every 20 minutes → Arduino polls every 13 minutes = worst-case 33-minute data staleness acceptable
- 24-hour ServerDiscovery cache refresh is frequent enough for production deployments
- Blinking animation updates every 1.5 seconds for threshold alerts

**Hardware Assumptions**:
- LED strip lengths: Can vaey depending on the lamp version
- FastLED library handles WS2812B timing requirements on ESP32
- Boot button (GPIO 0) can trigger config mode

**Environment Assumptions**:
- Each Arduino has unique `ARDUINO_ID` hardcoded (`const int ARDUINO_ID = unique id;`)
- Configuration mode AP password ("surf123456") is acceptably secure for setup
- Default WiFi credentials ("Sunrise" / "4085429360") are placeholder-only

### Where Complexity Hides

- **Wind Direction LED Conflict**: Top LED (index 19) reserved for wind direction can conflict with wind speed calculation if wind speed maxes out (constrained to NUM_LEDS_CENTER - 2 = 18 LEDs max)
- **Theme Color Fallback**: If server sends unknown theme, defaults to "classic_surf" silently (line 159-161) - no user notification
- **JSON Parsing Failure**: Returns false but doesn't clear old LED state - stale data persists on screen
- **Discovery Failure Loop**: If all discovery URLs fail AND fallback servers fail, Arduino keeps using last known server forever (no exponential backoff)

**Race Conditions**:
- **Blinking Phase Updates**: `blinkPhase` updated in `updateBlinkingAnimation()` every 20ms, but `updateSurfDisplay()` may be called mid-animation, causing visual stuttering
- **WiFi Status Checks**: `loop()` checks WiFi status with 30-second retry, but `fetchSurfDataFromServer()` may attempt HTTP during reconnection window
- **Status LED Breathing**: `blinkStatusLED()` updates LED 0 independently from surf display logic - concurrent writes to `leds_center[0]` not mutex-protected

**Rate Limiting Concerns**:
- **GitHub Discovery URLs**: No rate limiting on GitHub Pages/raw.githubusercontent.com fetches (attempts every 24h + boot), but could hit GitHub abuse detection with many devices
- **Server API Polling**: 13-minute interval per device means 110 requests/day - acceptable for single device, but 1000 devices = 110k requests/day could overwhelm backend
- **Serial Output Spam**: Extensive `Serial.printf()` calls could fill buffers if USB serial monitor disconnected

**Commented-Out Code & Workarounds**:
- Line 338: `// if (lastSurfData.quietHoursActive) return;` - commented out because quiet hours logic moved into display functions instead of short-circuiting animation updates

**Design Philosophy**:
- **Magic Numbers Elimination** (`533f6bd`): Converted hardcoded values to #define constants - maintainability improvement after initial prototype phase
- **Status LED as Health Indicator**: Bottom LED breathes different colors (blue=connecting, green=operational, red=error, yellow=config mode) - silent monitoring without serial output
- **Pull vs Push Architecture**: Arduino polls server instead of server pushing - simpler backend, resilient to network issues, but introduces data staleness

## 3. Architecture & Implementation

### Data Flow

```
[Boot] → [Load WiFi Creds from NVS] → [Connect to WiFi]
          ↓ (if failed)
       [Config Mode AP] → [Web UI for WiFi Setup] → [Save to NVS] → [Reconnect]

[Every 13 minutes]:
  [ServerDiscovery.getApiServer()] → [Check 24h cache]
          ↓ (if expired)
       [Fetch GitHub config.json] → [Extract api_server] → [Cache for 24h]
          ↓
  [HTTP GET https://{server}/api/arduino/{ID}/data]
          ↓
  [Parse JSON] → [Store in lastSurfData struct]
          ↓
  [updateSurfDisplay()] → [Calculate LED counts] → [Apply theme colors]
          ↓
  [Threshold Check] → [Normal mode: solid colors | Alert mode: blinking animation]
          ↓
  [Quiet Hours Check] → [Show only single LED per strip] → [Wind direction always visible]
          ↓
  [FastLED.show()] → [Physical LEDs update]

[Continuously in loop()]:
  [updateBlinkingAnimation()] → [Increment blinkPhase] → [Smooth wave effect for alerts]
  [Status LED breathing] → [Visual health indicator]
```

### Key Functions & Classes

**ServerDiscovery Class** (`ServerDiscovery.h`):
- `getApiServer()`: Main entry point - returns cached server or attempts discovery if 24h expired
- `attemptDiscovery()`: Tries both GitHub URLs in sequence with 1-second delays between attempts
- `fetchDiscoveryConfig()`: HTTP GET with 10-second timeout, parses JSON response
- `parseDiscoveryResponse()`: Extracts `api_server` from JSON, strips protocol prefixes, validates format
- Fallback servers: `["final-surf-lamp.onrender.com", "backup-api.herokuapp.com", "localhost:5001"]`

**LED Control Functions**:
- `updateSurfDisplay()`: Master orchestrator - calculates LED counts, applies theme, handles quiet hours, calls threshold functions
- `applyWindSpeedThreshold()`: Converts m/s to knots, compares to threshold, triggers blinking if exceeded
- `applyWaveHeightThreshold()`: Compares wave height (cm) to threshold, triggers blinking if exceeded
- `updateBlinkingLEDs()`: Creates traveling wave animation effect from bottom to top of strip
- `updateBlinkingCenterLEDs()`: Special variant for center strip (skips status LED at index 0)
- `setWindDirection()`: Maps degrees to colors - North=Green, East=Yellow, South=Red, West=Blue

**Theme System**:
- `getThemeColors()`: Returns `{wave_color, wind_color, period_color}` HSV tuples for 5 themes: classic_surf, vibrant_mix, tropical_paradise, ocean_sunset, electric_vibes
- Themes avoid red to prevent alarm associations (`0f53817` commit)

**WiFi Management**:
- `connectToWiFi()`: Loads credentials from NVS, attempts connection with 30-second timeout
- `startConfigMode()`: Creates AP "SurfLamp-Setup", serves HTML form at `/` for credential input
- `handleAPTimeout()`: 60-second timeout for config mode, then retries normal WiFi connection

**HTTP Endpoints** (ESP32 web server):
- `POST /api/update`: Receives pushed surf data (rarely used - polling is primary mode)
- `GET /api/status`: Returns comprehensive JSON with surf data, LED calculations, WiFi info, uptime
- `GET /api/test`: Simple connectivity test
- `GET /api/led-test`: Rainbow animation test for hardware validation
- `GET /api/fetch`: Manually trigger surf data fetch (debugging)
- `GET /api/discovery-test`: Force ServerDiscovery attempt (testing)

### Configuration

**Compile-Time Configuration** (must reflash Arduino):
```cpp
#define ARDUINO_ID 4433           // Unique device identifier (CRITICAL - must be unique per device)
#define NUM_LEDS_RIGHT 15         // Wave height strip length
#define NUM_LEDS_LEFT 15          // Wave period strip length
#define NUM_LEDS_CENTER 20        // Wind speed + direction strip length
#define BRIGHTNESS 100            // Global brightness (0-255)
#define FETCH_INTERVAL 780000     // 13 minutes in milliseconds
```

**Runtime Configuration** (via NVS storage):
- WiFi SSID/Password (set via config mode web UI)
- Theme selection (received from server API)
- Quiet hours active flag (server-calculated based on timezone)

**ServerDiscovery Configuration** (external - no reflash needed):
- GitHub-hosted `config.json` at `https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
- Format: `{"api_server": "final-surf-lamp.onrender.com"}`

## 4. Integration Points

### What Calls This Component

**User Interactions**:
- Physical boot button (GPIO 0) → triggers config mode if held during boot
- Web browser → accesses config mode web UI at `192.168.4.1` when in AP mode
- HTTP requests to ESP32 web server endpoints (status checks, manual fetch triggers)

**External Services**:
- GitHub Pages/raw.githubusercontent.com → serves ServerDiscovery config.json (24-hour pull)
- No other services directly call Arduino - it's a polling client only

### What This Component Calls

**Web Server API**:
- `GET https://{server}/api/arduino/{ARDUINO_ID}/data` - every 13 minutes
- Expected response: `{"wave_height_cm": 150, "wave_period_s": 8.0, "wind_speed_mps": 5, "wind_direction_deg": 180, "wave_threshold_cm": 100, "wind_speed_threshold_knots": 15, "quiet_hours_active": false, "led_theme": "classic_surf"}`

**ServerDiscovery Endpoints**:
- `GET https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
- `GET https://raw.githubusercontent.com/shahar42/final_surf_lamp/master/discovery-config/config.json`

**Libraries**:
- FastLED: LED strip control (blocking calls during `show()` - ~30μs per LED)
- ArduinoJson: JSON parsing (1024-byte document capacity)
- HTTPClient: HTTPS requests (15-second timeout)
- WiFiClientSecure: TLS connections (insecure mode - no cert validation)
- Preferences: NVS storage for WiFi credentials

### Data Contracts

**API Response Contract** (server → Arduino):
```json
{
  "wave_height_cm": 150,          // Integer - wave height in centimeters (0-500 typical)
  "wave_period_s": 8.0,           // Float - wave period in seconds (3-20 typical)
  "wind_speed_mps": 5,            // Integer - wind speed in meters per second (0-20 typical)
  "wind_direction_deg": 180,      // Integer - wind direction in degrees (0-360)
  "wave_threshold_cm": 100,       // Integer - user's wave height alert threshold
  "wind_speed_threshold_knots": 15, // Integer - user's wind speed alert threshold
  "quiet_hours_active": false,    // Boolean - server-calculated from user timezone
  "led_theme": "classic_surf"     // String - one of 5 theme names
}
```

**ServerDiscovery Response Contract** (GitHub → Arduino):
```json
{
  "api_server": "final-surf-lamp.onrender.com"  // String - domain without protocol
}
```

**Status Endpoint Response** (Arduino → monitoring tools):
```json
{
  "arduino_id": 4433,
  "status": "online",
  "wifi_connected": true,
  "ip_address": "192.168.1.42",
  "ssid": "MyWiFi",
  "signal_strength": -45,
  "uptime_ms": 3600000,
  "free_heap": 120000,
  "chip_model": "ESP32-D0WDQ6",
  "firmware_version": "1.0.0",
  "last_surf_data": { /* surf data fields */ },
  "fetch_info": {
    "last_fetch_ms": 3000000,
    "fetch_interval_ms": 780000,
    "time_since_last_fetch_ms": 600000,
    "time_until_next_fetch_ms": 180000
  },
  "led_calculations": {
    "wind_speed_leds": 5,
    "wave_height_leds": 6,
    "wave_period_leds": 8,
    "wind_speed_knots": 9.72,
    "wind_threshold_exceeded": false
  }
}
```

**Healthy Operation**:
```
🔄 Time to fetch new surf data...
🌐 Fetching surf data from: https://final-surf-lamp.onrender.com/api/arduino/4433/data
📥 Received surf data from server
🌊 Surf Data Received:
   Wave Height: 150 cm
   Wind Speed: 5 m/s
✅ Surf data fetch successful
🎨 LEDs Updated - Wind: 5, Wave: 6, Period: 8, Direction: 180°
```

**Discovery Working**:
```
🔍 Attempting server discovery...
   Trying discovery URL 1: https://shahar42.github.io/.../config.json
   ✅ Discovery successful from URL 1
📡 Discovery successful: final-surf-lamp.onrender.com
```

**Network Issues**:
```
❌ HTTP error fetching surf data: -1 (connection refused)
⚠️ Initial surf data fetch failed, will retry later
🔄 Attempting WiFi reconnection...
```

**JSON Parsing Failures**:
```
❌ JSON parsing failed: InvalidInput
```
*Last Updated: 2025-09-30*
*Firmware Version: 1.0.0*
*Hardware: ESP32-D0WDQ6 + WS2812B LED strips*
