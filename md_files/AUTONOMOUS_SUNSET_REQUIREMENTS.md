# Autonomous Sunset Feature - Technical Requirements

**Design Philosophy**: "Calculate Locally, Sync Globally"
**Migration Strategy**: Dual-Mode Server (v2 API for new devices, legacy API preserved)

---

## 1. Architecture Overview

### Current State (Server-Calculated)
- Server uses `astral` library to calculate sunset for each user's location
- Sends boolean `sunset_trigger` flag every 13 minutes
- Arduino passively reacts to flag
- Single point of failure: server downtime = no sunset feature

### Target State (Edge-Calculated)
- Arduino stores lat/lon/timezone in flash memory
- Arduino extracts time from HTTP Date headers (RFC 2822 format)
- Arduino calculates sunset locally using Dusk2Dawn library
- Server downtime does NOT break sunset feature
- Dual-core ESP32 separation: Core 0 (network I/O) + Core 1 (real-time LED display)

---

## 2. Server-Side Requirements

### 2.1 New API Endpoint

**Route**: `GET /api/arduino/v2/<int:arduino_id>/data`
**File**: `web_and_database/blueprints/api_arduino.py`

**Response Schema (New Fields)**:
```json
{
  "latitude": 32.0853,
  "longitude": 34.7818,
  "tz_offset": 2,

  "wave_height_cm": 150,
  "wave_period_s": 8.5,
  "wind_speed_mps": 5,
  "wind_direction_deg": 270,
  "wave_threshold_cm": 100,
  "wind_speed_threshold_knots": 15,
  "quiet_hours_active": false,
  "off_hours_active": false,
  "brightness_multiplier": 0.6,
  "led_theme": "classic_surf",
  "last_updated": "2025-12-20T22:00:00Z",
  "data_available": true
}
```

**Removed Fields** (no longer needed for v2):
- `sunset_animation` ❌
- `day_of_year` ❌

**New Field Definitions**:
- `latitude`: User's location latitude in decimal degrees (e.g., `32.0853` for Tel Aviv)
- `longitude`: User's location longitude in decimal degrees (e.g., `34.7818` for Tel Aviv)
- `tz_offset`: **Current** timezone offset in hours from UTC (e.g., `2` for IST winter, `3` for IDT summer)

**Data Sources**:
- `latitude`/`longitude`: From `LOCATION_COORDS` dict in `surf-lamp-processor/data_base.py`
- `tz_offset`: Calculate dynamically using `pytz` library (handles DST automatically)

**Implementation Notes**:
- Always include lat/lon/tz_offset in every response (stateless design, ~20 extra bytes)
- Server recalculates `tz_offset` on every request (handles DST transitions automatically)
- No "coordinates changed" flag needed - Arduino compares and only writes to flash if different

### 2.2 Legacy API Preservation

**Route**: `GET /api/arduino/<int:arduino_id>/data` (unchanged)
**Behavior**: Keep exact current implementation
**Purpose**: Support already-deployed devices without OTA capability

**NO CHANGES** to legacy endpoint - it must continue working exactly as it does now.

### 2.3 Database Schema Changes

**No database changes required.** All data comes from existing sources:
- User table: `location` column → lookup in `LOCATION_COORDS`
- Timezone calculation: Dynamic using `pytz.timezone(location).utcoffset(datetime.now())`

---

## 3. Arduino Firmware Requirements

### 3.1 New Dependencies

**Library**: `Dusk2Dawn` by dmkishi
**Installation**: Arduino Library Manager or `lib_deps = dmkishi/Dusk2Dawn` (PlatformIO)
**Verified Compatible**: ESP32, ESP8266, STM32

### 3.2 Flash Storage (Non-Volatile Memory)

**Storage Mechanism**: ESP32 Preferences library (NVS - Non-Volatile Storage)

**Keys**:
- `latitude` (float) - Decimal degrees
- `longitude` (float) - Decimal degrees
- `tz_offset` (int8_t) - Hours from UTC (-12 to +14)

**Write Strategy**:
```cpp
bool isLocationDifferent(float new_lat, float new_lon, int8_t new_tz) {
    float old_lat = preferences.getFloat("latitude", 0.0);
    float old_lon = preferences.getFloat("longitude", 0.0);
    int8_t old_tz = preferences.getChar("tz_offset", 0);

    // Only write if ANY value changed (prevents flash wear)
    return (abs(new_lat - old_lat) > 0.0001 ||
            abs(new_lon - old_lon) > 0.0001 ||
            new_tz != old_tz);
}
```

**Flash Wear Prevention**: ESP32 NVS supports 100,000 write cycles per sector - with write-on-change logic, this equals ~1,500 years at one location change per week.

### 3.3 Time Synchronization

**Source**: HTTP Date header from server response
**Format**: `Date: Sat, 20 Dec 2025 22:09:22 GMT` (RFC 2822)
**Parser**: Use existing Arduino HTTP library parsing or custom parser

**Parsing Implementation**:
```cpp
// Extract Date header from HTTP response
String dateHeader = http.header("Date");

// Parse RFC 2822 format: "Sat, 20 Dec 2025 22:09:22 GMT"
// Extract: day, month, year, hour, minute, second
// Libraries: TimeLib.h or custom parser
```

**Time Struct**:
```cpp
struct DateTime {
    int year;
    int month;
    int day;
    int hour;
    int minute;
    int second;
};
```

**Clock Drift Strategy**:
- ESP32 RTC drift: ~30-50 seconds/day typical
- Re-sync every 13 minutes from HTTP Date header
- Max drift between syncs: ~10 seconds (acceptable for sunset ±15 min window)

### 3.4 Sunset Calculation Logic

**Initialization** (on boot):
```cpp
Dusk2Dawn location(latitude, longitude, tz_offset);
```

**Daily Calculation** (calculate once at midnight or on first sync):
```cpp
DateTime now = getCurrentTime(); // From HTTP Date header sync
int sunsetMinutes = location.sunset(now.year, now.month, now.day, false); // false = no DST adjustment (server handles DST)

// Convert to HH:MM
int sunsetHour = sunsetMinutes / 60;
int sunsetMin = sunsetMinutes % 60;
```

**Trigger Window Logic**:
```cpp
// ±15 minute window around sunset
int currentMinutesSinceMidnight = now.hour * 60 + now.minute;
int windowStart = sunsetMinutes - 15;
int windowEnd = sunsetMinutes + 15;

bool isSunsetTime = (currentMinutesSinceMidnight >= windowStart &&
                     currentMinutesSinceMidnight <= windowEnd);
```

**One-Time Trigger Strategy**:
```cpp
// Prevent animation from playing multiple times during 30-min window
static bool sunsetPlayedToday = false;
static int lastDayOfYear = 0;

int currentDayOfYear = dayOfYear(now.year, now.month, now.day);
if (currentDayOfYear != lastDayOfYear) {
    sunsetPlayedToday = false;
    lastDayOfYear = currentDayOfYear;
}

if (isSunsetTime && !sunsetPlayedToday) {
    playSunsetAnimation();
    sunsetPlayedToday = true;
}
```

### 3.5 Network Request Changes

**Current Endpoint**: `https://final-surf-lamp-web.onrender.com/api/arduino/4433/data`
**New Endpoint**: `https://final-surf-lamp-web.onrender.com/api/arduino/v2/4433/data`

**Change Required**: Update URL construction in `WebServerHandler.cpp`:
```cpp
// OLD:
String url = "https://" + apiServer + "/api/arduino/" + String(ARDUINO_ID) + "/data";

// NEW:
String url = "https://" + apiServer + "/api/arduino/v2/" + String(ARDUINO_ID) + "/data";
```

**JSON Parsing Changes** (WebServerHandler.cpp):
```cpp
// REMOVE these fields (no longer sent by server):
// - sunset_animation
// - day_of_year

// ADD these new fields:
float latitude = doc["latitude"] | 0.0;
float longitude = doc["longitude"] | 0.0;
int8_t tz_offset = doc["tz_offset"] | 0;

// Store coordinates if changed
if (isLocationDifferent(latitude, longitude, tz_offset)) {
    preferences.begin("surf_lamp", false); // RW mode
    preferences.putFloat("latitude", latitude);
    preferences.putFloat("longitude", longitude);
    preferences.putChar("tz_offset", tz_offset);
    preferences.end();

    // Reinitialize Dusk2Dawn with new coordinates
    location = Dusk2Dawn(latitude, longitude, tz_offset);

    // Recalculate sunset for current day
    recalculateSunset();
}
```

**Cold Start Strategy**: Immediate heartbeat on WiFi connect
```cpp
// In lamp_template.ino setup():
setupWiFi();
fetchSurfDataFromServer(); // NEW: Immediate fetch instead of waiting 13 min
lastDataFetch = millis();
```

### 3.6 Dual-Core Task Distribution

**Core 0 (Network Secretary)**:
- WiFi connection management
- HTTP requests (every 13 minutes)
- Date header parsing
- Coordinate change detection
- Flash memory writes (if location changed)

**Core 1 (LED Artist)**:
- LED refresh (200 FPS for smooth animations)
- Sunset trigger checking (every loop iteration)
- Sunset animation playback (30 seconds)
- Button inputs
- Status LED updates

**Communication Bridge**:
```cpp
// Atomic variables (thread-safe without mutex overhead)
std::atomic<int> sunsetMinutesSinceMidnight(0);
std::atomic<int> currentYear(2025);
std::atomic<int> currentMonth(12);
std::atomic<int> currentDay(20);

// Core 0 writes (after HTTP sync)
sunsetMinutesSinceMidnight.store(calculateSunset());

// Core 1 reads (in main loop)
int sunsetTime = sunsetMinutesSinceMidnight.load();
```

**Task Creation**:
```cpp
// In setup()
xTaskCreatePinnedToCore(
    networkTask,      // Function
    "NetworkSecretary", // Name
    10000,            // Stack size
    NULL,             // Parameters
    1,                // Priority
    &networkTaskHandle, // Handle
    0                 // Core 0
);

// Main loop runs on Core 1 by default
```

---

## 4. Implementation Checklist

### Phase 1: Server v2 API (Backend)
- [ ] Add `pytz` to `web_and_database/requirements.txt`
- [ ] Create helper function `get_current_tz_offset(location_name)` in `utils/helpers.py`
- [ ] Create new route `/api/arduino/v2/<int:arduino_id>/data` in `api_arduino.py`
- [ ] Copy logic from legacy route, remove sunset calculation
- [ ] Add lat/lon/tz_offset to response JSON
- [ ] Test with curl/Postman to verify response format
- [ ] Deploy to Render staging environment
- [ ] Verify legacy `/api/arduino/{id}/data` still works unchanged

### Phase 2: Arduino Firmware (Edge Computing)
- [ ] Install Dusk2Dawn library in Arduino IDE/PlatformIO
- [ ] Create `SunsetCalculator.h/cpp` module with:
  - [ ] Dusk2Dawn instance
  - [ ] Flash storage (Preferences)
  - [ ] Date header parsing
  - [ ] Sunset calculation logic
  - [ ] Trigger window detection
- [ ] Update `WebServerHandler.cpp`:
  - [ ] Change URL to `/api/arduino/v2/{id}/data`
  - [ ] Parse new fields (lat, lon, tz_offset)
  - [ ] Remove old fields (sunset_animation, day_of_year)
  - [ ] Call coordinate storage if changed
- [ ] Update `lamp_template.ino`:
  - [ ] Add immediate fetch on WiFi connect
  - [ ] Remove old sunset trigger logic
  - [ ] Add new sunset calculation check in loop
- [ ] Create dual-core task structure:
  - [ ] Core 0: Network task (HTTP + time sync)
  - [ ] Core 1: Main loop (LED display + sunset trigger)
  - [ ] Atomic variable communication
- [ ] Test on workbench ESP32 before deploying

### Phase 3: Testing & Validation
- [ ] **Unit Tests** (Arduino simulator or physical test):
  - [ ] Date header parsing accuracy
  - [ ] Sunset calculation matches expected time
  - [ ] Trigger window detection (±15 min)
  - [ ] One-time-per-day logic (doesn't repeat)
  - [ ] Flash write-on-change (not every request)
- [ ] **Integration Tests**:
  - [ ] Server responds with correct lat/lon/tz for each location
  - [ ] Arduino fetches and stores coordinates
  - [ ] Legacy endpoint still works for old devices
- [ ] **Field Test**:
  - [ ] Deploy v2 firmware to ONE new device
  - [ ] Monitor Render logs for v2 endpoint calls
  - [ ] Verify sunset animation triggers at correct local time
  - [ ] Disconnect WiFi mid-day, verify sunset still triggers

### Phase 4: Production Rollout
- [ ] Document firmware version in `Config.h` (e.g., `#define FIRMWARE_VERSION "2.0.0"`)
- [ ] Flash all new devices with v2 firmware before shipping
- [ ] Update manufacturing documentation with v2 endpoint note
- [ ] Add server monitoring for v2 vs legacy usage ratio
- [ ] Update user-facing documentation (sunset works offline)

---

## 5. Acceptance Criteria

**Server-Side**:
- ✅ Legacy `/api/arduino/{id}/data` works unchanged (old devices unaffected)
- ✅ New `/api/arduino/v2/{id}/data` returns lat/lon/tz_offset
- ✅ Timezone offset updates automatically during DST transitions
- ✅ No database schema changes required

**Arduino-Side**:
- ✅ Sunset calculated locally using Dusk2Dawn library
- ✅ Time synchronized from HTTP Date header (no NTP required)
- ✅ Coordinates stored in flash, only updated when changed
- ✅ Sunset animation triggers ±15 min window around calculated sunset
- ✅ Animation plays once per day (doesn't repeat during window)
- ✅ Feature works even if server offline for hours (autonomous operation)
- ✅ LED display never stutters during network requests (dual-core separation)
- ✅ Immediate data fetch on boot (device operational within seconds)

**User Experience**:
- ✅ Old lamps continue working without any changes
- ✅ New lamps work immediately after WiFi setup
- ✅ Sunset animation happens at correct local time
- ✅ Feature resilient to internet outages

---

## 6. Design Decisions Reference

| Decision Point | Chosen Strategy | Rationale |
|---|---|---|
| **Timezone Storage** | Server-managed offset | Server calculates DST, Arduino stays simple |
| **Cold Start** | Immediate heartbeat on WiFi connect | User doesn't wait 13 min for first sync |
| **Coordinate Propagation** | Always include in response (stateless) | 20 bytes overhead, eliminates flag logic |
| **Migration Strategy** | Dual-mode server (v2 + legacy) | No OTA capability on deployed devices |
| **Solar Library** | Dusk2Dawn | ESP32 verified, minimal footprint, simple API |
| **Time Source** | HTTP Date header (piggyback) | Zero marginal cost, already present |
| **Concurrency** | Dual-core (Core 0=network, Core 1=display) | Network latency never blocks LED updates |

---

## 7. File Changes Summary

### Backend Changes
- `web_and_database/requirements.txt` - Add `pytz`
- `web_and_database/utils/helpers.py` - Add `get_current_tz_offset(location)`
- `web_and_database/blueprints/api_arduino.py` - Add `/api/arduino/v2/<id>/data` route

### Arduino Changes
- `arduino_code/lamp_refractored/Config.h` - Update `FIRMWARE_VERSION` to `"2.0.0"`
- `arduino_code/lamp_refractored/lamp_template.ino` - Add immediate fetch, remove old sunset logic
- `arduino_code/lamp_refractored/WebServerHandler.cpp` - Update URL to v2, parse new fields
- `arduino_code/lamp_refractored/SunsetCalculator.h` - **NEW FILE** - Sunset calculation module
- `arduino_code/lamp_refractored/SunsetCalculator.cpp` - **NEW FILE** - Implementation
- `arduino_code/lamp_refractored/platformio.ini` or `libraries.txt` - Add Dusk2Dawn dependency

---

## 8. Risk Mitigation

| Risk | Mitigation |
|---|---|
| **Clock drift causes missed trigger** | 13-min sync interval limits max drift to ~10 sec (acceptable for ±15 min window) |
| **Polar regions (no sunset)** | Dusk2Dawn returns `-1`, handle gracefully (disable feature) |
| **Server sends wrong coordinates** | Arduino validates lat (-90 to +90) and lon (-180 to +180) before storing |
| **Flash wear from repeated writes** | Write-on-change logic prevents unnecessary writes (100k cycle limit = 1500 years) |
| **Old devices break during migration** | Dual-mode server preserves legacy endpoint forever |
| **Network latency blocks LED display** | Dual-core separation ensures Core 1 never waits for network |

---

## 9. Future Enhancements (Out of Scope)

- OTA firmware updates for deployed devices
- NTP fallback if HTTP Date header missing
- User-configurable trigger window (e.g., ±30 min instead of ±15 min)
- Multiple daily animations (sunrise + sunset)
- Astronomy events (solstice, equinox special animations)

---

**Document Status**: Ready for Implementation
**Last Updated**: 2025-12-20
**Approved By**: Shahar (System Architect)
