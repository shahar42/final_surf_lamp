# Surf Lamp Features Reference

## 1. WiFi Fingerprinting & Home Location Detection

### Overview
Automatically detects when the lamp has been moved to a new physical location (new house, apartment, etc.) and triggers WiFi reconfiguration.

### How It Works
**Fingerprint Storage:**
- After successful WiFi connection, lamp scans for nearby networks
- Stores SSID names of the 4 strongest neighboring WiFi networks
- Saves this "fingerprint" in ESP32 non-volatile storage (NVS)

**Location Detection:**
- On next boot, scans for visible WiFi networks
- Compares current networks to stored fingerprint
- If **0% match** (no common neighbors) → lamp moved to new location
- If **any match found** → same location, proceed with connection

**Visual Feedback:**
- All LEDs blink **purple** (slow) during location check (~1 second)
- If new location detected → triggers config portal (Yellow LED)

### Use Cases
**Scenario 1: User moves to new apartment**
1. Lamp boots up with old WiFi credentials
2. Fingerprinting detects 0% neighbor match
3. Automatic config portal opens
4. User enters new WiFi credentials
5. New fingerprint stored

**Scenario 2: User visits friend's house temporarily**
1. Lamp stays at home, fingerprint remains valid
2. If user brings lamp to friend's house, 0% match triggers reconfiguration
3. Prevents infinite failed connection attempts with wrong credentials

### Implementation
**File:** `WiFiFingerprinting.h`

**Key Functions:**
- `isSameLocation()` - Returns `true` if any neighbor SSID matches stored fingerprint
- `update()` - Stores fingerprint of 4 strongest neighbors (excluding target SSID)
- `load()` - Loads stored fingerprint from NVS on boot
- `clear()` - Wipes fingerprint (factory reset)

**Configuration:**
```cpp
MAX_NEIGHBORS = 4       // Number of neighbor SSIDs to store
MAX_SSID_LEN = 32       // Maximum SSID length
NVS Namespace: "wifi_fp"
```

---

### Connection Failure States & Diagnostics

When WiFi connection fails, the lamp runs **intelligent diagnostics** to determine WHY and takes different actions based on the failure type.

#### Diagnostic States (Checked in Order):

**1. No Networks Found**
- **Detection:** WiFi scan returns 0 networks
- **Error Message:** `"No WiFi networks found. Check if router is powered on and in range."`
- **Action:** Retry connection (10 attempts max, ~5 minutes total - covers router boot time)
- **User Fix:** Check router power, move lamp closer

**2. SSID Not Found**
- **Detection:** Target SSID not in scan results
- **Error Message:** Detailed message with checklist:
  - Is SSID typed correctly (case-sensitive)?
  - Is router's 2.4GHz band enabled? (ESP32 doesn't support 5GHz)
  - Is router in range?
- **Action:** Retry connection (10 attempts max, ~5 minutes total)
- **User Fix:** Verify SSID spelling, enable 2.4GHz band, move closer

**3. Weak Signal (RSSI < -85 dBm)**
- **Detection:** SSID found but signal strength below threshold
- **Error Message:** `"Weak signal (-87 dBm). Move lamp closer to router or use WiFi extender."`
- **Action:** Retry connection (10 attempts max, ~5 minutes total)
- **User Fix:** Move lamp, use WiFi extender, reposition router

**4. WPA3-Only Security**
- **Detection:** Router using `WIFI_AUTH_WPA3_PSK`
- **Error Message:** `"Router uses WPA3 security. ESP32 requires WPA2. Change router to WPA2/WPA3 mixed mode."`
- **Action:** Retry connection (10 attempts max, ~5 minutes total)
- **User Fix:** Change router security settings to WPA2 or WPA2/WPA3 mixed mode

**5. New Location Detected (0% Fingerprint Match)**
- **Detection:** 0% fingerprint match (no common neighbor SSIDs)
- **Error Message:** `"Moved to new location. Please reconfigure WiFi."`
- **Action:** **IMMEDIATELY breaks retry loop** → forces config portal
- **Visual:** Purple blinking LEDs for 1 second before config portal
- **User Fix:** Enter new WiFi credentials in config portal

**6. Authentication Failure (Disconnect Reason Codes)**
- **Detection:** WiFi disconnect event with reason code
- **Common Codes:**
  - Code 2: Wrong password or security mode mismatch
  - Code 203: Authentication failed (most common - wrong password)
  - Code 201: Beacon timeout (weak signal or AP disappeared)
  - Code 204: Association failed (MAC filtering?)
- **Action:** Retry connection (10 attempts max, ~5 minutes total)
- **User Fix:** Re-enter correct password in config portal

#### Retry Logic Flow:
```
Attempt 1-9:  Try to connect (30s timeout each)
              ↓
              Connection failed?
              ↓
              Run diagnostics (SSID scan, signal check, security check)
              ↓
              Check location fingerprint (purple LEDs)
              ↓
              ├─ New location (0% match)? → FORCE CONFIG PORTAL (break loop)
              └─ Same location? → Wait 5 seconds → Retry

Total time attempts 1-9: ~4.5 minutes (covers typical 2-4 min router boot)

Attempt 10:   Try to connect (INDEFINITE timeout)
              ↓
              ├─ Success → Update fingerprint → Continue boot
              └─ Fail → Show config portal indefinitely
```

#### Visual Feedback During Connection Failures:

| LED Pattern | State | Duration |
|-------------|-------|----------|
| **Green blinking** (slow) | Attempting WiFi connection | ~30 seconds per attempt |
| **Purple blinking** (slow) | Checking location fingerprint | ~1 second |
| **Red/White/Green static** | Config portal (AP mode) | Until user configures |

#### Error Message Display:

Failed connection error messages are **injected into the config portal web page** as red banners:

```html
❌ Connection Failed
Network 'MyWiFi5G' not found. Check:
• Is SSID typed correctly (case-sensitive)?
• Is router's 2.4GHz band enabled? (ESP32 doesn't support 5GHz)
• Is router in range?
```

This helps users understand WHY connection failed before re-entering credentials.

---

**Logic Flow (Simple):**
```
Boot → Load stored fingerprint
  ↓
Attempt WiFi connection (10 retries max, ~5 minutes total)
  ↓
├─ SUCCESS → Update fingerprint → Continue
│
└─ FAILURE → Run diagnostics:
    ├─ No networks found? → Retry after 5s
    ├─ SSID not found? → Retry after 5s
    ├─ Weak signal? → Retry after 5s
    ├─ WPA3-only? → Retry after 5s
    ├─ Check location fingerprint (purple LEDs):
    │   ├─ New location (0% match)? → FORCE CONFIG PORTAL (exit retry loop)
    │   └─ Same location? → Retry after 5s
    │
    └─ After 10 failed attempts → ESP.restart() → Config portal
```

**Serial Output:**
```
📍 Loaded fingerprint: 4 neighbors
   - NeighborNetwork1
   - NeighborNetwork2
   - CoffeeShopWiFi
   - BuildingRouter
🔍 Checking if same location...
✅ Match found: 'NeighborNetwork1' - SAME LOCATION
```

Or if moved:
```
🔍 Checking if same location...
❌ 0% match - NEW LOCATION (moved to new house)
```

### Conservative Failure Handling
- If scan fails (0 networks visible) → assumes **same location**
- Prevents false positives from temporary scan failures
- User can manually reset WiFi via boot button if needed

---

## 2. Off Hours Mode

### Overview
**Completely turns OFF all LEDs** during user-configured time periods. Lamp consumes minimal power and shows no light.

### Priority
**HIGHEST PRIORITY** - When active, overrides all other modes (quiet hours, surf display, thresholds).

### Behavior
- All LEDs OFF (including status LED, wind direction, surf condition strips)
- No blinking animations
- No visual feedback whatsoever
- Lamp continues fetching data in background (ready when off hours end)

### Configuration
**Backend-controlled:** User sets time ranges via dashboard

**JSON Field:** `off_hours_active` (boolean)

**Arduino Processing:**
```cpp
if (lastSurfData.offHoursActive) {
    FastLED.clear();
    FastLED.show();
    Serial.println("🔴 Off hours active - lamp turned OFF");
    return;  // Skip all other display logic
}
```

### Use Cases
- **Sleep hours:** User wants complete darkness (11 PM - 7 AM)
- **Work hours:** Lamp in bedroom, user at office (9 AM - 5 PM)
- **Vacation mode:** Turn off lamp while away from home

### Serial Output
```
🔴 Off hours active - lamp turned OFF
```

---

## 3. Quiet Hours Mode

### Overview
**Gentle ambient lighting** during nighttime - only top LED of each strip illuminated. Wind direction LED remains ON.

### Priority
**SECONDARY PRIORITY** - Only activates when off hours is NOT active.

### Behavior
**LEDs Active:**
- Top LED of wave height strip (shows theme color)
- Top LED of wind speed strip (shows theme color)
- Top LED of wave period strip (shows theme color)
- Wind direction LED (top of wind strip) - shows cardinal direction color

**LEDs Inactive:**
- All other LEDs turned off
- No blinking animations
- No threshold alerts

**Brightness:** Dimmed to 30% of normal brightness

### Threshold Logic
**Wave height and wind speed thresholds DO NOT APPLY during quiet hours.**

Even if surf conditions exceed user thresholds:
- No blinking animations
- No alert behavior
- Consistent top-LED-only display

### Configuration
**Backend-controlled:** User opts into quiet hours via dashboard

**JSON Field:** `quiet_hours_active` (boolean)

**Arduino Processing:**
```cpp
if (lastSurfData.quietHoursActive) {
    FastLED.setBrightness(BRIGHTNESS * 0.3); // 30% brightness
    FastLED.clear();

    // Set wind direction LED
    setWindDirection(windDirection);

    // Light only top LED of each strip
    leds[WAVE_HEIGHT_TOP] = getThemeColor(0);      // Wave height
    leds[WIND_SPEED_TOP] = getThemeColor(1);       // Wind speed
    leds[WAVE_PERIOD_TOP] = getThemeColor(2);      // Wave period

    FastLED.show();
    Serial.println("🌙 Quiet hours: Only top LEDs active + wind direction");
    return;
}
```

### Use Cases
- **Light sleepers:** Want to see lamp is on but minimal light (12 AM - 6 AM)
- **Bedroom ambiance:** Subtle night light that doesn't disturb sleep
- **Consistent lighting:** Don't want changing surf conditions to flash during night

### Visual Example
```
Normal Mode (Daytime):
█████████ ← Wave height strip (9 LEDs showing 2.7m waves)
███████ ← Wind speed strip (7 LEDs showing 14 knots)
█████ ← Wave period strip (5 LEDs showing 5 seconds)

Quiet Hours Mode:
        █ ← Only top LED + wind direction
        █
        █
```

### Serial Output
```
🌙 Quiet hours: Only top LEDs active + wind direction
```

---

## Priority Logic Summary

```
Priority Order (Highest to Lowest):
1. OFF HOURS     → All LEDs off, no exceptions
2. QUIET HOURS   → Top LEDs only, no thresholds
3. NORMAL MODE   → Full surf display with thresholds
```

**Decision Tree:**
```
Surf data received?
  ↓
├─ Off hours active?
│  └─ YES → Turn OFF all LEDs → DONE
│
├─ Quiet hours active?
│  └─ YES → Show top LEDs only (30% brightness) → DONE
│
└─ Normal mode → Full surf display with threshold alerts
```

### Configuration Combinations

| Off Hours | Quiet Hours | Lamp Behavior |
|-----------|-------------|---------------|
| ✅ Active | ✅ Active | **Off hours wins** - All LEDs OFF |
| ✅ Active | ❌ Inactive | All LEDs OFF |
| ❌ Inactive | ✅ Active | Top LEDs only (30% brightness) |
| ❌ Inactive | ❌ Inactive | Normal surf display |

---

## Code Location Reference

**WiFi Fingerprinting:**
- Implementation: `WiFiFingerprinting.h` (lines 1-128)
- Usage: `main_reference.ino` line 1345-1350 (location check in setup)

**Off Hours:**
- Implementation: `main_reference.ino` lines 1140-1146 (`updateSurfDisplay()`)
- Data field: `lastSurfData.offHoursActive` (bool)
- JSON field: `off_hours_active`

**Quiet Hours:**
- Implementation: `main_reference.ino` lines 1156-1191 (`updateSurfDisplay()`)
- Data field: `lastSurfData.quietHoursActive` (bool)
- JSON field: `quiet_hours_active`
- Threshold skip: Lines 696-697, 713-714, 730-731

---

## User Documentation Notes

**WiFi Fingerprinting:**
- Transparent to user (automatic behavior)
- Reduces support calls for "lamp won't connect after moving"
- Purple LED blink visible during check

**Off Hours vs Quiet Hours:**
- Off hours = **Complete darkness** (sleep, away, privacy)
- Quiet hours = **Minimal light** (night light, ambiance)
- Users can configure both independently
- Off hours always takes priority

**Dashboard Configuration:**
- Off hours: User sets custom time ranges (e.g., 11 PM - 7 AM)
- Quiet hours: User opts in/out (separate toggle)
- Backend calculates which mode is active and sends flags to Arduino

---

**Last Updated:** 2025-12-17
**Firmware Version:** Configuration-driven template (main_reference.ino)
