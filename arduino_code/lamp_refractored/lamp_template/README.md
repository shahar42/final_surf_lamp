# Surf Lamp - Modular Template v3.0.0

**Professional Arduino template for creating surf lamps with any LED configuration.**

Based on Scott Meyers' "Effective C++" principles and modular architecture design.

---

## Quick Start (Create New Lamp in 10 Minutes)

### Step 1: Copy Template

```bash
cd /home/shahar42/Git_Surf_Lamp_Agent/arduino_code/
cp -r lamp_template my_new_lamp
cd my_new_lamp
```

### Step 2: Edit Config.h

Open `Config.h` and edit **ONLY** these values in the admin section:

```cpp
// Device identity
const int ARDUINO_ID = 7;  // Your unique lamp ID from database

// Hardware
#define TOTAL_LEDS 48      // Your total LED count

// LED strip mapping (your physical LED indices)
#define WAVE_HEIGHT_BOTTOM 2
#define WAVE_HEIGHT_TOP 15

#define WAVE_PERIOD_BOTTOM 35
#define WAVE_PERIOD_TOP 47

#define WIND_SPEED_BOTTOM 30
#define WIND_SPEED_TOP 18

// Scaling (adjust max ranges for your location)
#define MAX_WAVE_HEIGHT_METERS 3.0
#define MAX_WIND_SPEED_MPS 18.0
```

**DO NOT edit below the "DO NOT MODIFY BELOW THIS LINE" comment!**

### Step 3: Rename Main File

```bash
mv lamp_template.ino my_new_lamp.ino
```

### Step 4: Compile & Upload

1. Open `my_new_lamp.ino` in Arduino IDE
2. Select board: ESP32 Dev Module
3. Compile (Ctrl+R) - verify no errors
4. Upload (Ctrl+U) to your ESP32

**Done!** Your lamp is now running with custom configuration.

---

## Architecture Overview

### Modular Design

```
lamp_template.ino          ← Main orchestration (< 200 lines, identical for all lamps)
├── Config.h               ← ⭐ ONLY USER-EDITABLE FILE (lamp-specific)
├── SurfState.h            ← Data structures (SurfData, WaveConfig, etc.)
├── LedController.h/cpp    ← LED display functions (reusable)
├── Themes.h/cpp           ← Color themes (reusable)
├── WebServerHandler.h/cpp ← HTTP endpoints (reusable)
├── WiFiHandler.h/cpp      ← WiFi management (reusable)
├── ServerDiscovery.h      ← API server discovery (reusable)
├── WiFiFingerprinting.h   ← Location detection (reusable)
└── animation.h            ← Sunset animation (reusable)
```

**Key Principle**: Users edit ONE file (Config.h), all other files are reusable.

### Benefits

✅ **Easy to use correctly, hard to use incorrectly** (Scott Meyers Item 18)
✅ **Compile-time validation** - Config errors caught before upload
✅ **Zero risk** - Can't accidentally break reusable code
✅ **Bug fixes once** - All lamps benefit from module updates
✅ **< 10 minutes** to create new lamp configuration

---

## Configuration Parameters Explained

### Required Parameters (Must Edit)

#### `ARDUINO_ID`
- **Type**: `int`
- **Purpose**: Unique identifier for this lamp in backend database
- **Example**: `6` (Maayan's lamp), `7` (Ben's lamp)
- **How to get**: Check backend database for your assigned ID

#### `TOTAL_LEDS`
- **Type**: `int`
- **Purpose**: Total number of LEDs in your physical strip
- **Example**: `56` (Maayan's lamp), `48` (Ben's lamp)
- **How to measure**: Count all LEDs on your strip, including unused ones

#### LED Strip Mapping (`BOTTOM` and `TOP` indices)

Each surf lamp has 3 strips:

1. **Wave Height Strip** (typically right side)
   - `WAVE_HEIGHT_BOTTOM` - First LED index of strip
   - `WAVE_HEIGHT_TOP` - Last LED index of strip

2. **Wave Period Strip** (typically left side)
   - `WAVE_PERIOD_BOTTOM` - First LED index of strip
   - `WAVE_PERIOD_TOP` - Last LED index of strip

3. **Wind Speed Strip** (typically center)
   - `WIND_SPEED_BOTTOM` - First LED index (also status indicator)
   - `WIND_SPEED_TOP` - Last LED index (also wind direction indicator)

**Direction auto-detection**: If `BOTTOM < TOP` = FORWARD, if `BOTTOM > TOP` = REVERSE

**Example** (Maayan's 56-LED lamp):
```cpp
#define WAVE_HEIGHT_BOTTOM 3    // LEDs 3→16 (14 LEDs, FORWARD)
#define WAVE_HEIGHT_TOP 16

#define WAVE_PERIOD_BOTTOM 42   // LEDs 42→55 (14 LEDs, FORWARD)
#define WAVE_PERIOD_TOP 55

#define WIND_SPEED_BOTTOM 38    // LEDs 38→21 (18 LEDs, REVERSE)
#define WIND_SPEED_TOP 21
```

### Optional Parameters (Fine Tuning)

#### `MAX_WAVE_HEIGHT_METERS`
- **Default**: `3.0`
- **Purpose**: Maximum wave height displayed on strip
- **When to change**: If your surf spot rarely exceeds 2m, lower to `2.0` for better resolution

#### `MAX_WIND_SPEED_MPS`
- **Default**: `18.0` (≈35 knots)
- **Purpose**: Maximum wind speed displayed on strip
- **When to change**: Adjust based on typical wind at your location

#### Wave Animation Parameters
- `WAVE_BRIGHTNESS_MIN_PERCENT` - Minimum brightness during threshold blink (default: 45%)
- `WAVE_BRIGHTNESS_MAX_PERCENT` - Maximum brightness during threshold blink (default: 100%)
- `WAVE_LENGTH_MULTIPLIER` - Wave length as % of strip (default: 0.7 = 70%)
- `WAVE_SPEED_MULTIPLIER` - Animation speed (default: 1.2, range: 0.8-1.5)

---

## Compilation & Upload

### Prerequisites

1. **Arduino IDE** (1.8.19 or newer)
2. **ESP32 Board Support**:
   - File → Preferences → Additional Board Manager URLs
   - Add: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Tools → Board → Boards Manager → Search "ESP32" → Install

3. **Required Libraries** (Tools → Manage Libraries):
   - FastLED (3.5.0+)
   - ArduinoJson (6.21.0+)
   - WiFiManager (2.0.16+)

### Board Settings

- **Board**: ESP32 Dev Module
- **Upload Speed**: 921600
- **Flash Frequency**: 80MHz
- **Flash Mode**: QIO
- **Flash Size**: 4MB (32Mb)
- **Partition Scheme**: Default 4MB with spiffs
- **Core Debug Level**: None (or Info for debugging)

### Compilation Process

1. Open `your_lamp_name.ino` in Arduino IDE
2. Arduino IDE automatically compiles all `.h` and `.cpp` files in directory
3. Compile (Ctrl+R) - Check for errors in output window
4. If successful, upload (Ctrl+U)

### Common Compilation Errors

#### `error: 'TOTAL_LEDS' was not declared`
- **Cause**: Config.h not found or not included
- **Fix**: Ensure Config.h is in same directory as .ino file

#### `static assertion failed: WAVE_HEIGHT_LENGTH must be positive`
- **Cause**: BOTTOM and TOP indices are the same
- **Fix**: Check LED strip mapping - BOTTOM and TOP must be different

#### `static assertion failed: WIND_SPEED_LENGTH needs min 3 LEDs`
- **Cause**: Wind strip too short
- **Fix**: Allocate at least 3 LEDs for wind strip

#### `error: no matching function for call to 'FastLED.addLeds'`
- **Cause**: FastLED library not installed or wrong version
- **Fix**: Install FastLED 3.5.0 or newer

---

## Operating Modes

### Normal Mode
- All 3 strips show surf conditions
- Threshold exceeded → Blinking animation
- Full brightness (adjustable via dashboard)

### Off Hours (Highest Priority)
- Lamp completely dark
- Configured via dashboard time settings
- Use case: Sleep time, lamp should be invisible

### Quiet Hours (Secondary Priority)
- Only top LED of each strip illuminated
- Wind direction indicator remains on
- 30% brightness reduction
- Use case: Gentle nightlight, ambient presence

### Threshold Alert Mode
- Triggered when wave height OR wind speed exceeds user threshold
- Traveling wave animation with brightness modulation
- Speed and intensity configurable in Config.h

---

## LED Meanings

### Status LED (Wind Strip Bottom)
- 🔵 **Blue** (blinking): Connecting to WiFi
- 🟢 **Green** (blinking): Connected, fresh data (< 30 min old)
- 🟠 **Orange** (blinking): Connected, stale data (> 30 min old)
- 🔴 **Red** (blinking): WiFi disconnected
- 🟡 **Yellow** (blinking): Configuration portal active

### Wind Direction LED (Wind Strip Top)
- 🟢 **Green**: North wind (0-10°, 300-360°)
- 🟡 **Yellow**: East wind (10-180°)
- 🔴 **Red**: South wind (180-250°)
- 🔵 **Blue**: West wind (250-300°)

### WiFi Setup Patterns

#### AP Mode (Configuration Portal)
- Wave Height (Right): **All Red**
- Wind Speed (Center): **All White**
- Wave Period (Left): **All Green**
- **Action**: Connect to "SurfLamp-Setup" WiFi (open network)

#### Trying to Connect
- All LEDs: **Slow blinking green**

#### Checking Location
- All LEDs: **Slow blinking purple**

---

## HTTP Endpoints

Your lamp exposes these endpoints at `http://<lamp_ip>`:

### Data & Control
- `POST /api/update` - Receive surf data from backend
- `GET /api/fetch` - Manually trigger surf data fetch

### Monitoring
- `GET /api/status` - Full device status (WiFi, surf data, LED calculations, timing)
- `GET /api/info` - Hardware specs (chip model, flash size, firmware version)
- `GET /api/wifi-diagnostics` - WiFi connection diagnostics

### Testing
- `GET /api/test` - Simple connectivity test
- `GET /api/led-test` - Run LED test sequence (all strips + rainbow)
- `GET /api/status-led-test` - Test all status LED error states
- `GET /api/discovery-test` - Test API server discovery

---

## Troubleshooting

### Lamp Not Connecting to WiFi

1. **Hold BOOT button for 5 seconds** → Forces WiFi reset
2. Connect to "SurfLamp-Setup" WiFi (open network)
3. Browser should auto-open to 192.168.4.1
4. Enter your WiFi credentials

**Common issues**:
- ❌ 5GHz WiFi → ESP32 only supports 2.4GHz
- ❌ Hidden SSID → Must be visible (broadcast enabled)
- ❌ WPA3 security → Change router to WPA2 or WPA2/WPA3 mixed mode
- ❌ Weak signal → Move lamp closer to router or use WiFi extender

### Wrong LED Colors/Positions

**Diagnosis**: Run LED test (`GET /api/led-test`)
- Each strip lights up separately with different color
- Verify which physical LEDs correspond to each strip

**Fix**: Edit Config.h LED mapping to match your physical wiring

### Threshold Not Working

**Check**:
1. `/api/status` → View current thresholds and LED calculations
2. Verify wave height in meters vs threshold in meters
3. Check `wind_threshold_exceeded` in status response

**Common mistake**: Threshold set too high (e.g., 5m waves never happen at your spot)

### Data Not Updating

**Check**:
1. Status LED color:
   - Orange = Stale data, server not responding
   - Green = Fresh data
2. `/api/status` → Check `time_since_last_fetch_ms`
3. `/api/fetch` → Manually trigger fetch
4. Check backend logs for Arduino polling

### Compilation Fails

**Check**:
1. All required libraries installed (FastLED, ArduinoJson, WiFiManager)
2. ESP32 board support installed
3. Config.h in same directory as .ino
4. Config.h parameter validation (static_assert errors explain the issue)

---

## Adding Features

### Adding New Theme

Edit `Themes.cpp`, add new case in `getThemeColors()`:

```cpp
} else if (theme == "my_custom_theme") {
    // Wave, Wind, Period colors (HSV format)
    return {CHSV(180, 255, 200), CHSV(30, 255, 200), CHSV(90, 255, 200)};
```

### Adding New HTTP Endpoint

1. Add handler function in `WebServerHandler.cpp`
2. Register in `setupHTTPEndpoints()`

```cpp
void handleMyEndpoint() {
    webServer->send(200, "application/json", "{\"status\":\"ok\"}");
}

// In setupHTTPEndpoints():
server.on("/api/my-endpoint", HTTP_GET, handleMyEndpoint);
```

### Modifying LED Behavior

Edit functions in `LedController.cpp` - all LED logic is centralized there.

---

## Firmware Version History

### v3.0.0 (Current) - Modular Template
- Refactored monolithic code into reusable modules
- Config.h as single source of configuration
- Compile-time validation with static_assert
- Scott Meyers design principles applied

### v2.0.0 - Configuration-Driven
- Admin configuration section in single file
- Auto-calculated derived values

### v1.0.0 - Original Monolithic
- Hardcoded for each lamp
- Code duplication across variants

---

## Support & Documentation

### Files in This Directory

- `Config.h` - **Edit this for your lamp**
- `lamp_template.ino` - Main orchestration file
- `*.h` / `*.cpp` - Reusable module implementations
- `README.md` - This file

### Additional Resources

- Backend integration: See `web_and_database/` documentation
- Troubleshooting: See `STATUS_LED_GUIDE.md` (if exists)
- Architecture decisions: See `CLAUDE.md` in project root

### Getting Help

If stuck:
1. Check `/api/status` endpoint for diagnostics
2. Enable Core Debug Level: Info in Arduino IDE
3. Check Serial Monitor (115200 baud) for detailed logs

---

## License & Credits

**Template Architecture**: Based on Scott Meyers' "Effective C++" principles
**Created**: 2025-12-20 by Shahar & Claude
**Version**: 3.0.0

---

**Happy surfing! 🌊**
