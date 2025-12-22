# Arduino V2 Integration Specification

**Backend Status**: ✅ Deployed and ready
**Your Task**: Implement Arduino firmware changes below

---

## Server V2 Endpoint

**URL**: `https://final-surf-lamp-web.onrender.com/api/arduino/v2/{arduino_id}/data`

**Response Format**:
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

**Changes from Legacy**:
- ✅ Added: `latitude`, `longitude`, `tz_offset`
- ❌ Removed: `sunset_animation`, `day_of_year`

---

## Required Arduino Changes

### 1. Update Request URL

**File**: `WebServerHandler.cpp`

```cpp
// OLD:
String url = "https://" + apiServer + "/api/arduino/" + String(ARDUINO_ID) + "/data";

// NEW:
String url = "https://" + apiServer + "/api/arduino/v2/" + String(ARDUINO_ID) + "/data";
```

### 2. Add Dusk2Dawn Library

**Installation**: Arduino Library Manager → Search "Dusk2Dawn" → Install

**Or PlatformIO**: Add to `platformio.ini`:
```ini
lib_deps = dmkishi/Dusk2Dawn
```

### 3. Parse New Fields + Remove Old Ones

**File**: `WebServerHandler.cpp` (in `processSurfData()`)

```cpp
// ADD NEW FIELDS:
float latitude = doc["latitude"] | 0.0;
float longitude = doc["longitude"] | 0.0;
int8_t tz_offset = doc["tz_offset"] | 0;

// REMOVE THESE (no longer sent):
// - sunset_animation
// - day_of_year
```

### 4. Store Coordinates in Flash (Write-on-Change)

**File**: New module `SunsetCalculator.h/cpp` or add to existing module

```cpp
#include <Preferences.h>

Preferences preferences;

bool isLocationDifferent(float new_lat, float new_lon, int8_t new_tz) {
    preferences.begin("surf_lamp", true); // Read-only
    float old_lat = preferences.getFloat("latitude", 0.0);
    float old_lon = preferences.getFloat("longitude", 0.0);
    int8_t old_tz = preferences.getChar("tz_offset", 0);
    preferences.end();

    return (abs(new_lat - old_lat) > 0.0001 ||
            abs(new_lon - old_lon) > 0.0001 ||
            new_tz != old_tz);
}

void storeCoordinates(float lat, float lon, int8_t tz) {
    if (isLocationDifferent(lat, lon, tz)) {
        preferences.begin("surf_lamp", false); // Read-write
        preferences.putFloat("latitude", lat);
        preferences.putFloat("longitude", lon);
        preferences.putChar("tz_offset", tz);
        preferences.end();
        Serial.println("📍 Coordinates updated in flash");
    }
}
```

### 5. Extract Time from HTTP Date Header

**File**: `WebServerHandler.cpp` (in `fetchSurfDataFromServer()`)

```cpp
// After http.GET() succeeds:
String dateHeader = http.header("Date");
Serial.println("HTTP Date: " + dateHeader);

// Parse RFC 2822: "Sat, 20 Dec 2025 22:09:22 GMT"
// Store year, month, day, hour, minute for sunset calc
DateTime currentTime = parseDateHeader(dateHeader);
```

**Parser Function** (simple version):
```cpp
struct DateTime {
    int year;
    int month;
    int day;
    int hour;
    int minute;
};

DateTime parseDateHeader(String dateHeader) {
    // Example: "Sat, 20 Dec 2025 22:09:22 GMT"
    DateTime dt;

    // Extract date parts (basic parser, improve as needed)
    int firstComma = dateHeader.indexOf(',');
    int firstSpace = dateHeader.indexOf(' ', firstComma + 2);

    String dayStr = dateHeader.substring(firstComma + 2, firstSpace);
    dt.day = dayStr.toInt();

    // Month lookup (Dec → 12)
    String monthStr = dateHeader.substring(firstSpace + 1, firstSpace + 4);
    dt.month = monthToInt(monthStr);

    // Year (4 digits after month)
    dt.year = dateHeader.substring(firstSpace + 5, firstSpace + 9).toInt();

    // Time HH:MM:SS
    int timeStart = firstSpace + 10;
    dt.hour = dateHeader.substring(timeStart, timeStart + 2).toInt();
    dt.minute = dateHeader.substring(timeStart + 3, timeStart + 5).toInt();

    return dt;
}

int monthToInt(String month) {
    if (month == "Jan") return 1;
    if (month == "Feb") return 2;
    if (month == "Mar") return 3;
    if (month == "Apr") return 4;
    if (month == "May") return 5;
    if (month == "Jun") return 6;
    if (month == "Jul") return 7;
    if (month == "Aug") return 8;
    if (month == "Sep") return 9;
    if (month == "Oct") return 10;
    if (month == "Nov") return 11;
    if (month == "Dec") return 12;
    return 1;
}
```

### 6. Calculate Sunset with Dusk2Dawn

**File**: New or existing module

```cpp
#include <Dusk2Dawn.h>

// Initialize with stored coordinates
Dusk2Dawn location(latitude, longitude, tz_offset);

// Calculate sunset for current day (returns minutes since midnight)
int sunsetMinutes = location.sunset(currentTime.year, currentTime.month, currentTime.day, false);

// Convert to HH:MM
int sunsetHour = sunsetMinutes / 60;
int sunsetMin = sunsetMinutes % 60;

Serial.printf("Sunset today: %02d:%02d\n", sunsetHour, sunsetMin);
```

### 7. Trigger Window Check (±15 min)

**File**: Main loop

```cpp
int currentMinutesSinceMidnight = currentTime.hour * 60 + currentTime.minute;
int windowStart = sunsetMinutes - 15;
int windowEnd = sunsetMinutes + 15;

bool isSunsetTime = (currentMinutesSinceMidnight >= windowStart &&
                     currentMinutesSinceMidnight <= windowEnd);

if (isSunsetTime && !sunsetPlayedToday) {
    playSunsetAnimation();
    sunsetPlayedToday = true;
}
```

### 8. One-Time-Per-Day Logic

```cpp
static bool sunsetPlayedToday = false;
static int lastDayOfYear = 0;

int currentDayOfYear = calculateDayOfYear(currentTime.year, currentTime.month, currentTime.day);

// Reset flag at midnight
if (currentDayOfYear != lastDayOfYear) {
    sunsetPlayedToday = false;
    lastDayOfYear = currentDayOfYear;
}
```

### 9. Immediate Fetch on WiFi Connect

**File**: `lamp_template.ino`

```cpp
void setup() {
    // ... existing setup code ...

    setupWiFi();

    // NEW: Immediate fetch instead of waiting 13 min
    if (fetchSurfDataFromServer()) {
        Serial.println("✅ Initial data fetch successful");
    }

    lastDataFetch = millis();
}
```

---

## Testing Checklist

- [ ] Compiles without errors
- [ ] Date header parsing works (print parsed values to serial)
- [ ] Sunset calculation matches expected time for your location
- [ ] Coordinates only written to flash when changed (check serial logs)
- [ ] Trigger window works (±15 min around sunset)
- [ ] Animation plays once per day (doesn't repeat)
- [ ] Legacy devices still work (if testing with old firmware)

---

## Test Endpoints

**Legacy** (old firmware): `https://final-surf-lamp-web.onrender.com/api/arduino/4444/data`
**V2** (new firmware): `https://final-surf-lamp-web.onrender.com/api/arduino/v2/4444/data`

Test with curl:
```bash
curl -s https://final-surf-lamp-web.onrender.com/api/arduino/v2/4444/data | jq
```

---

## Notes

- Server automatically handles DST (sends current `tz_offset`)
- Dusk2Dawn returns `-1` if no sunset (polar regions) - handle gracefully
- Flash wear: ~100k writes = 1500 years at 1 location change/week
- Clock drift: Max ~10 sec between 13-min syncs (acceptable)

Questions? Ask before implementing.
