# Arduino Lamps - Technical Documentation

## 1. Overview

**What it does**: ESP32 microcontrollers with WS2812B addressable LED strips that visualize real-time surf conditions through color-coded lighting patterns, polling the web server every 13 minutes for location-based wave and wind data.

**Why it exists**: Provides ambient, glanceable surf condition awareness without requiring users to check phones or websites. The physical lamp translates complex surf metrics (wave height, period, wind speed, direction) into intuitive visual patterns that surfers can interpret instantly.

## 2. Technical Details

### What Would Break If This Disappeared?

- **User Experience Core**: The entire product value proposition disappears - no physical surf condition display
- **System Architecture**: The pull-based polling model that reduces backend complexity would be wasted (no clients pulling data)
- **ServerDiscovery System**: The GitHub-hosted config mechanism becomes pointless without devices consuming it
- **Database `lamps` Table**: Orphaned lamp records (arduino_id, arduino_ip) with no physical devices
- **Threshold Alert System**: Wave/wind threshold logic becomes purely theoretical without LED visualization

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
- LED strip lengths: Center=20 LEDs (19=wind direction, 1-18=wind speed, 0=status), Right=15 LEDs (wave height), Left=15 LEDs (wave period)
- FastLED library handles WS2812B timing requirements on ESP32
- Boot button (GPIO 0) can trigger config mode

**Environment Assumptions**:
- Each Arduino has unique `ARDUINO_ID` hardcoded (line 44: `const int ARDUINO_ID = 4433;`)
- Configuration mode AP password ("surf123456") is acceptably secure for setup
- Default WiFi credentials ("Sunrise" / "4085429360") are placeholder-only

### Where Complexity Hides

**Edge Cases**:
- **Quiet Hours Single LED Positioning**: `getQuietHoursLedIndex()` calculates which single LED lights up based on normal mode's LED count, but positioning logic assumes strip indexing from 0 - off-by-one errors lurk here (line 865-869)
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
- Git history shows LED scaling formulas changed multiple times (`3398fde "Improve wind speed LED scaling"`, `c315af3 "Fix wind speed unit bug"`) - indicates empirical tuning was required
- Theme system underwent major refactor (`a421ed3 "Simplify to 5 themes"`) suggesting original design was too complex

### Stories the Code Tells

**Git History Insights**:
- **Nighttime Behavior Evolution** (`7b8c882`, `2394580`): Multiple commits fixing quiet hours - original implementation didn't handle "show only top LED" correctly, indicates this was user-requested feature after initial deployment
- **Theme System Journey**: Started with many themes (`b804c39 "professional LED theme system"`), simplified to 5 (`a421ed3`), then reduced red colors (`0f53817`) - user feedback drove design evolution
- **Wind Speed Unit Bug** (`c315af3`, `8818a51`): Critical bug where wind speed units (m/s vs knots) were confused - added validation and maintainer docs to prevent recurrence
- **Location-Centric Refactor** (`cd0f5d1` "Restore API-based processing from 100 commits ago") - architecture thrashed between approaches before settling on current design

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

## 5. Troubleshooting & Failure Modes

### Common Issues

**Problem: LEDs Don't Update**
- **Symptoms**: LEDs frozen on old pattern, status LED breathing green (connected)
- **Detection**: Check serial output for "❌ HTTP error fetching surf data" or "❌ JSON parsing failed"
- **Causes**:
  - Server API endpoint changed format (broke JSON contract)
  - ServerDiscovery cache pointing to dead server (24h stale)
  - Network firewall blocking HTTPS on port 443
- **Recovery**:
  1. Trigger manual fetch: `GET http://{arduino_ip}/api/fetch`
  2. Check status endpoint: `GET http://{arduino_ip}/api/status` → examine `last_surf_data.last_update_ms`
  3. Force discovery: `GET http://{arduino_ip}/api/discovery-test`
  4. If all fail: Power cycle Arduino (forces fresh discovery attempt on boot)

**Problem: WiFi Won't Connect**
- **Symptoms**: Status LED blinking blue continuously, no IP address after 30 seconds
- **Detection**: Serial output shows "❌ WiFi connection failed" repeating
- **Causes**:
  - Wrong credentials in NVS
  - WiFi network changed password
  - Router MAC filtering blocking device
  - 2.4GHz network disabled (ESP32 doesn't support 5GHz)
- **Recovery**:
  1. Hold boot button during power-on → triggers config mode
  2. Connect phone to "SurfLamp-Setup" AP (password: surf123456)
  3. Navigate to `192.168.4.1`
  4. Enter new credentials
  5. Wait 20 seconds for connection attempt

**Problem: Threshold Alerts Not Blinking**
- **Symptoms**: LEDs solid even when conditions exceed thresholds
- **Detection**: Compare `GET /api/status` LED calculations with threshold values
- **Causes**:
  - Quiet hours active (server-side flag overrides thresholds)
  - Thresholds set too high in user preferences
  - Wind speed unit confusion (threshold in knots, but comparison broken)
  - Blinking animation disabled by race condition
- **Recovery**:
  1. Check `quiet_hours_active` in status endpoint
  2. Verify threshold comparison: `wind_speed_knots >= wind_speed_threshold_knots`
  3. Check user dashboard: update thresholds to realistic values
  4. Restart Arduino if race condition suspected

**Problem: Wrong Wind Direction Color**
- **Symptoms**: Top center LED showing wrong color for known wind direction
- **Detection**: Compare `wind_direction_deg` from status endpoint with LED color
- **Causes**:
  - Wind direction data inverted (some APIs report "from" vs "to" direction)
  - Compass calibration issue in API source
  - Color mapping logic has off-by-one error in degree ranges
- **Recovery**:
  1. Verify server API data: check background processor logs for raw API responses
  2. Cross-reference with third-party weather source
  3. Test with `setWindDirection()` function directly (modify code to test fixed values)

**Problem: Discovery Fails, Falls Back to Dead Server**
- **Symptoms**: Arduino never updates after deployment, status shows 404 errors
- **Detection**: Serial output: "⚠️ Discovery failed, using current: old-server.onrender.com"
- **Causes**:
  - GitHub Pages repo deleted or renamed
  - DNS resolution failing for GitHub domains
  - Arduino's NTP time wrong, causing TLS handshake failures
- **Recovery**:
  1. Verify GitHub repo exists: `curl https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
  2. Update fallback servers in code: change `fallback_servers[0]` to current production URL
  3. Reflash Arduino with updated fallback list
  4. Consider deploying local DNS/mDNS for discovery as GitHub bypass

### Diagnostic Log Patterns

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

## 6. Evolution & Future Considerations

### Technical Debt

**Hardcoded Configuration**:
- `ARDUINO_ID` must be manually changed per device before flashing - error-prone at scale
- **Solution**: Implement provisioning API where Arduino generates unique ID from chip MAC address, registers with server on first boot

**Insecure TLS**:
- `client.setInsecure()` disables certificate validation - vulnerable to MITM attacks
- **Solution**: Bundle root CA certificates in firmware or use ESP32's cert store with OTA updates

**Serial Output Spam**:
- Extensive `Serial.printf()` calls slow down execution if serial buffer fills
- **Solution**: Implement log levels (DEBUG/INFO/ERROR), disable verbose logs in production builds

**No OTA Updates**:
- Firmware updates require physical USB access to every device
- **Solution**: Implement ESP32 OTA update system pulling from GitHub releases or Render-hosted firmware binaries

**NVS Wear Concerns**:
- WiFi credentials stored in NVS rewritten on every config mode save - flash wear on frequently reconfigured devices
- **Solution**: Check if credentials changed before writing, implement wear leveling awareness

### What Would You Change with 20/20 Hindsight?

**1. Pull vs Push Architecture**:
- **Current**: Arduino polls every 13 minutes (simple but wasteful)
- **Better**: WebSocket persistent connection with server-initiated pushes when conditions change
- **Why**: Reduces unnecessary API calls when conditions static, enables <1 minute latency for alerts

**2. ServerDiscovery Complexity**:
- **Current**: GitHub-hosted JSON with 24-hour cache
- **Better**: mDNS/Bonjour local discovery + cloud fallback, or hardcode multiple production URLs with health checks
- **Why**: GitHub dependency is single point of failure for entire fleet

**3. Theme System**:
- **Current**: 5 hardcoded themes with server-selected name
- **Better**: Server sends RGB/HSV color values directly in API response
- **Why**: Enables per-user custom colors without firmware updates

**4. Status LED Overload**:
- **Current**: Bottom LED serves as status indicator (blue/green/red/yellow)
- **Better**: Separate dedicated status LED or use built-in ESP32 LED
- **Why**: Status LED competes with wind speed visualization, confusing when strip nearly full

**5. Threshold Alert Timing**:
- **Current**: Blinking animation requires conditions exceed threshold + not quiet hours
- **Better**: Audio alert option (buzzer), push notification to phone app, or configurable alert modes
- **Why**: Visual-only alerts easily missed if user not looking at lamp

**6. Wind Speed Unit Confusion**:
- **Current**: API sends m/s, Arduino converts to knots, user configures in knots
- **Better**: API sends both units, Arduino displays user's preferred unit system
- **Why**: Multiple unit conversions = multiple places for bugs (proven by git history)

### Scaling Concerns

**Network Bandwidth**:
- **Current Load**: 1 device = 110 requests/day (every 13 min) × ~500 bytes = ~55 KB/day
- **At Scale**: 10,000 devices = 1.1 million requests/day = ~550 MB/day bandwidth
- **Mitigation**: Implement request batching (single API call returns data for multiple arduinos), CDN caching with short TTLs

**ServerDiscovery GitHub Limits**:
- **Current**: Each device fetches config.json once per 24h
- **At Scale**: 10,000 devices staggered over 24h = ~7 requests/minute to GitHub
- **GitHub Pages Limits**: 100 GB bandwidth/month, soft quota
- **Mitigation**: Use CloudFlare CDN in front of GitHub Pages, or migrate to Render-hosted discovery endpoint

**Database Current_Conditions Table Growth**:
- **Current**: 1 row per lamp (upserted every 20 min by background processor)
- **At Scale**: 10,000 lamps = 10,000 rows, minimal growth
- **No Concern**: Primary key on lamp_id prevents unbounded growth

**Background Processor API Quota**:
- **Current**: Location-centric processing (2-6 API calls per 20-min cycle)
- **At Scale**: 10,000 lamps across 1,000 unique locations = 1,000 API calls every 20 min = 72,000 calls/day
- **OpenWeatherMap Free Tier**: 1,000 calls/day (EXCEEDED)
- **Mitigation**: Paid tier ($40/month for 100k calls/day), or cache weather data per location with 10-min TTL

**WiFi Network Saturation**:
- **Scenario**: Multiple lamps on same home WiFi network
- **Concern**: 5 lamps × 13-min polling = 5 concurrent HTTPS connections every 13 min (negligible)
- **No Action Needed**: Polling interval is conservative

**Flash Memory Exhaustion**:
- **Current Firmware Size**: ~1.2 MB (ESP32 has 4 MB flash typical)
- **With OTA**: Requires 2× firmware size for A/B partitions = 2.4 MB (fits)
- **Future Proofing**: Optimize binary size (remove unused libraries), consider ESP32-S3 with 8 MB flash

---

*Last Updated: 2025-09-30*
*Firmware Version: 1.0.0*
*Hardware: ESP32-D0WDQ6 + WS2812B LED strips*