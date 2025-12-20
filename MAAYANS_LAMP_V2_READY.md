# Maayan's Lamp - V2 Configuration Complete

**Arduino ID**: 6
**Status**: ✅ Ready for compilation and upload

---

## Configuration Summary

### Hardware Setup
- **Total LEDs**: 56 (WS2812B, GRB color order)
- **LED Pin**: GPIO 2
- **Global Brightness**: 75/255 (indoor safe)
- **Button**: GPIO 0 (ESP32 boot button for WiFi reset)

### LED Strip Mapping

**Wave Height (Right Strip)**:
- LEDs: 3 → 16 (14 LEDs total)
- Direction: FORWARD
- Scaling: 3.0m max wave height = ~21cm per LED

**Wave Period (Left Strip)**:
- LEDs: 41 → 55 (15 LEDs total)
- Direction: FORWARD
- Scaling: 1:1 mapping (1 second = 1 LED)

**Wind Speed (Center Strip)**:
- LEDs: 38 → 21 (18 LEDs total)
- Direction: REVERSE
- Scaling: 35 knots max (~18 m/s)
- Special LEDs:
  - LED 38 (bottom): Status indicator (green/orange/red)
  - LED 21 (top): Wind direction (green=N, yellow=E, red=S, blue=W)

### Surf Data Scaling
- **Max Wave Height**: 3.0 meters
- **Max Wind Speed**: 35 knots (18.0 m/s)
- **Wave Period**: 1 LED = 1 second (no scaling)

### V2 Features Enabled

**Autonomous Sunset Calculation**:
- ✅ Stores lat/lon/tz_offset in flash
- ✅ Parses HTTP Date headers for time sync
- ✅ Calculates sunset locally using Dusk2Dawn
- ✅ ±15 minute trigger window
- ✅ One-time-per-day animation logic
- ✅ Works offline after initial sync

**Dual-Core Architecture**:
- ✅ Core 0: Network requests (background, non-blocking)
- ✅ Core 1: LED animations (real-time, 200 FPS)
- ✅ Atomic variable communication (lock-free)
- ✅ LEDs never stutter during network I/O

---

## Files Location

**All code in**: `/home/shahar42/Git_Surf_Lamp_Agent/arduino_code/lamp_refractored/`

**Key Files**:
- `Config.h` - Maayan's lamp configuration (ID=6)
- `lamp_template.ino` - Main orchestration (dual-core)
- `SunsetCalculator.h/cpp` - Autonomous sunset
- `DualCoreManager.h/cpp` - Dual-core task management
- `WebServerHandler.cpp` - V2 API endpoint
- `LedController.cpp` - LED display logic
- `WiFiHandler.cpp` - WiFi + fingerprinting
- `Themes.cpp` - 5 color themes
- `animation.h` - Sunset animation

---

## Compilation Instructions

### 1. Install Required Library
**Arduino IDE**:
1. Open Library Manager (Tools → Manage Libraries)
2. Search: "Dusk2Dawn"
3. Install: Dusk2Dawn by dmkishi

**PlatformIO**:
Add to `platformio.ini`:
```ini
lib_deps = dmkishi/Dusk2Dawn
```

### 2. Open Project
- Navigate to: `arduino_code/lamp_refractored/`
- Open: `lamp_template.ino`

### 3. Board Configuration
- **Board**: ESP32 Dev Module
- **Upload Speed**: 921600
- **Flash Frequency**: 80MHz
- **Partition Scheme**: Default 4MB

### 4. Compile & Upload
- Click Verify (checkmark icon) to compile
- Click Upload (arrow icon) to flash

---

## Expected Serial Output

```
🌊 ================================================================
🌊 SURF LAMP - MODULAR TEMPLATE CONFIGURATION
🌊 ================================================================
🔧 Arduino ID: 6

📍 LED STRIP CONFIGURATION:
   Total LEDs: 56
   Wave Height: LEDs 3→16 (14 total, FORWARD)
   Wave Period: LEDs 41→55 (15 total, FORWARD)
   Wind Speed:  LEDs 38→21 (18 total, REVERSE)

🎯 SPECIAL FUNCTION LEDS:
   Status LED: 38 (wind strip bottom)
   Wind Direction LED: 21 (wind strip top)

📊 SCALING CONFIGURATION:
   Max Wave Height: 3.0 meters
   Max Wind Speed: 18.0 m/s (35.0 knots)
   Wave Height Scaling: 21 cm per LED
   Wind Speed Scaling: 0.9 LEDs per m/s

🌊 WAVE ANIMATION SETTINGS:
   Brightness Range: 45% - 100%
   Wave Length: Side=14.0, Center=12.6 LEDs
   Animation Speed: 1.2x

🚀 Starting dual-core architecture...
✅ Core 0 task created (Network Secretary)
✅ Core 1 running main loop (LED Artist)

🔧 [Core 0] Network Secretary started
🌐 Fetching surf data from: https://final-surf-lamp-web.onrender.com/api/arduino/v2/6/data
📅 HTTP Date: Sat, 21 Dec 2025 04:15:30 GMT
🕐 Time synced: 2025-12-21 04:15:30
📍 Coordinates updated: lat=32.0853, lon=34.7818, tz=2
🌅 Sunset calculated: 16:47 (±15min trigger window)
✅ [Core 0] Fetch successful

🔄 [Core 1] Detected state change, updating display...
```

---

## WiFi Setup

**First Boot**:
1. Device creates AP: `SurfLamp-Setup`
2. Password: `surf123456`
3. Connect to AP (phone auto-redirects to config page)
4. Select WiFi network and enter password
5. Device connects and starts fetching data

**WiFi Reset**:
- Hold ESP32 boot button (GPIO 0) for 1 second
- Device wipes credentials and restarts to config portal

**Location Fingerprinting**:
- Device scans surrounding WiFi networks
- Stores fingerprint to detect location changes
- If lamp moved to new location, forces WiFi reconfiguration

---

## Testing Checklist

### Basic Functionality
- [ ] Code compiles without errors
- [ ] Device connects to WiFi
- [ ] Serial shows Arduino ID = 6
- [ ] LED strip mappings print correctly
- [ ] Dual-core tasks start successfully

### Data Fetching
- [ ] Initial fetch completes (immediate on WiFi connect)
- [ ] Serial shows HTTP Date header parsed
- [ ] Coordinates stored: lat=32.0853, lon=34.7818, tz=2
- [ ] Sunset time calculated and displayed
- [ ] Core 0 fetches every 13 minutes in background

### LED Display
- [ ] Wave height strip shows data (right side, 14 LEDs)
- [ ] Wave period strip shows data (left side, 15 LEDs)
- [ ] Wind speed strip shows data (center, 18 LEDs)
- [ ] Status LED shows green (bottom of wind strip)
- [ ] Wind direction LED shows correct color (top of wind strip)
- [ ] No stutter during network requests (dual-core working)

### Sunset Animation
- [ ] Wait for calculated sunset time (±15 min window)
- [ ] Animation plays automatically (30 seconds)
- [ ] Serial shows "[Core 1] Sunset detected - playing animation"
- [ ] Animation plays once (doesn't repeat during 30-min window)
- [ ] Next day: Flag resets, animation can play again

### Threshold Alerts
- [ ] Wave height exceeds threshold → blinking animation
- [ ] Wind speed exceeds threshold → blinking animation
- [ ] Both can be active simultaneously
- [ ] 200 FPS smooth animation (no stutter)

---

## Troubleshooting

**Issue**: Compilation error "Dusk2Dawn.h: No such file or directory"
**Solution**: Install Dusk2Dawn library (see step 1 above)

**Issue**: Wrong LED indices light up
**Solution**: Verify Config.h matches physical wiring, check FORWARD/REVERSE directions

**Issue**: Sunset never triggers
**Solution**: Check serial for calculated sunset time, verify clock is synced, check coordinatesInitialized flag

**Issue**: LEDs stutter during network requests
**Solution**: Check dual-core tasks started (see "Starting dual-core" in serial), verify Core 0 and Core 1 messages appear

**Issue**: WiFi won't connect
**Solution**: Ensure 2.4GHz network (ESP32 doesn't support 5GHz), check WiFi diagnostics in serial output

---

## Database Entry

**Verify Maayan's lamp is registered**:
```bash
curl https://final-surf-lamp-web.onrender.com/api/arduino/v2/6/data | jq
```

**Expected Response**:
```json
{
  "latitude": 32.0853,
  "longitude": 34.7818,
  "tz_offset": 2,
  "wave_height_cm": 36,
  "wave_period_s": 4.75,
  "wind_speed_mps": 0,
  "wind_direction_deg": 0,
  ...
}
```

---

## Next Steps

1. **Compile** the code (Arduino IDE or PlatformIO)
2. **Upload** to Maayan's ESP32
3. **Monitor** serial output for startup sequence
4. **Connect** to WiFi via config portal
5. **Verify** data fetching and LED display
6. **Wait** for sunset to test autonomous trigger

**Configuration is complete and ready for deployment!**
