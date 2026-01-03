# Surf Lamp Configuration Guide

**Version:** 2.0.0-template
**Last Updated:** 2025-12-13

## Overview

This template uses a **configuration-driven design** where admins only need to modify key parameters at the top of the file. Everything else (strip lengths, directions, scaling factors) is automatically calculated.

---

## Quick Start: Creating a New Lamp

### Step 1: Copy Template
```bash
cp arduino_code/template_ino/main_reference.ino arduino_code/new_lamp/new_lamp.ino
cp arduino_code/template_ino/ServerDiscovery.h arduino_code/new_lamp/
```

### Step 2: Open Configuration Section
Open `new_lamp.ino` and locate the **CONFIG SECTION** (lines 37-88).

### Step 3: Configure Admin Parameters

Only modify values in the CONFIG SECTION:

```cpp
// ============== ADMIN CONFIGURATION ==============

// ---------------- DEVICE IDENTITY ----------------
const int ARDUINO_ID = 2;  // ← Change this to your lamp's unique ID

// ---------------- HARDWARE SETUP ----------------
#define LED_PIN 2              // GPIO pin for LED data
#define TOTAL_LEDS 146         // Total LEDs in your strip
#define LED_TYPE WS2812B       // LED chipset
#define COLOR_ORDER GRB        // Color order (GRB or RGB)
#define BRIGHTNESS 90          // Global brightness (0-255)

// ---------------- LED STRIP MAPPING ----------------
// Wave Height Strip
#define WAVE_HEIGHT_BOTTOM 11  // First LED of wave height strip
#define WAVE_HEIGHT_TOP 49     // Last LED of wave height strip

// Wave Period Strip
#define WAVE_PERIOD_BOTTOM 107
#define WAVE_PERIOD_TOP 145

// Wind Speed Strip
#define WIND_SPEED_BOTTOM 101  // Bottom = Status LED
#define WIND_SPEED_TOP 59      // Top = Wind Direction LED

// ---------------- SURF DATA SCALING ----------------
#define MAX_WAVE_HEIGHT_METERS 3.9   // Maximum displayable wave height
#define MAX_WIND_SPEED_MPS 13.0      // Maximum displayable wind speed

// ---------------- WAVE ANIMATION ----------------
#define WAVE_BRIGHTNESS_MIN_PERCENT 50   // Min brightness during blink
#define WAVE_BRIGHTNESS_MAX_PERCENT 110  // Max brightness during blink
#define WAVE_LENGTH_SIDE 10.0            // Wave length for side strips
#define WAVE_LENGTH_CENTER 12.0          // Wave length for center strip
#define WAVE_SPEED_MULTIPLIER 1.2        // Animation speed
```

### Step 4: Upload and Verify
1. Upload to Arduino
2. Open Serial Monitor (115200 baud)
3. Verify configuration printout matches your settings

---

## Configuration Parameters Explained

### 1. Device Identity

#### `ARDUINO_ID`
- **Type:** Integer (0-999)
- **Purpose:** Unique identifier for this lamp in the database
- **Example:** `const int ARDUINO_ID = 2;`
- **Note:** Must match the `arduino_id` in the database `lamps` table

---

### 2. Hardware Setup

#### `LED_PIN`
- **Type:** GPIO pin number
- **Purpose:** Which ESP32 pin drives the LED strip
- **Common Values:** `2` (built-in), `4`, `5`, `16-19`, `21-23`
- **Example:** `#define LED_PIN 2`

#### `TOTAL_LEDS`
- **Type:** Integer (1-500)
- **Purpose:** Total number of LEDs in the physical strip
- **Example:** `#define TOTAL_LEDS 146`
- **How to count:** Connect strip and run LED test to see full range

#### `LED_TYPE`
- **Type:** FastLED chipset constant
- **Purpose:** LED chipset model
- **Common Values:** `WS2812B`, `WS2811`, `APA102`, `SK6812`
- **Example:** `#define LED_TYPE WS2812B`

#### `COLOR_ORDER`
- **Type:** FastLED color order constant
- **Purpose:** Corrects color channel mapping
- **Common Values:** `GRB` (most common), `RGB`, `BGR`
- **Example:** `#define COLOR_ORDER GRB`
- **How to test:** If red appears green, try different order

#### `BRIGHTNESS`
- **Type:** Integer (0-255)
- **Purpose:** Global brightness level
- **Recommended:** `60-120` (too bright = eye strain, too dim = invisible)
- **Example:** `#define BRIGHTNESS 90`

---

### 3. LED Strip Mapping

These define where each visual strip starts and ends on the physical LED strip.

#### Understanding Bottom vs Top
- **Bottom LED** = Where the strip starts (physically closest to base)
- **Top LED** = Where the strip ends (physically at top of lamp)
- **Direction** = Auto-detected from bottom < top

#### Wave Height Strip
```cpp
#define WAVE_HEIGHT_BOTTOM 11  // First LED of strip
#define WAVE_HEIGHT_TOP 49     // Last LED of strip
```
- **Purpose:** Displays wave height (in meters)
- **Typically:** Right side of lamp
- **Auto-calculated:** Length = 39 LEDs, Direction = FORWARD

#### Wave Period Strip
```cpp
#define WAVE_PERIOD_BOTTOM 107
#define WAVE_PERIOD_TOP 145
```
- **Purpose:** Displays wave period (in seconds, 1 LED = 1 second)
- **Typically:** Left side of lamp
- **Auto-calculated:** Length = 39 LEDs, Direction = FORWARD

#### Wind Speed Strip
```cpp
#define WIND_SPEED_BOTTOM 101  // Also the status LED
#define WIND_SPEED_TOP 59      // Also wind direction LED
```
- **Purpose:** Displays wind speed (in m/s)
- **Typically:** Center of lamp
- **Auto-calculated:** Length = 43 LEDs, Direction = REVERSE (101→59)
- **Special:** Bottom LED = WiFi status, Top LED = Wind direction

#### Direction Detection
The code automatically detects direction:
- **FORWARD:** bottom < top (e.g., 11→49)
- **REVERSE:** bottom > top (e.g., 101→59)

#### Mapping Example
If your physical strip is wired like this:
```
LED indices: [0][1][2]...[10][11-49][50-100][101-59][146]
                          ^^^^^^^^   ^^^^^^^^  ^^^^^^^^
                          Wave Ht    Unused    Wind (reverse)
                                     [107-145]
                                     ^^^^^^^^^
                                     Wave Per
```

---

### 4. Surf Data Scaling

Controls how surf conditions map to LED counts.

#### `MAX_WAVE_HEIGHT_METERS`
```cpp
#define MAX_WAVE_HEIGHT_METERS 3.9
```
- **Purpose:** Maximum wave height that fills entire wave height strip
- **Type:** Float (meters)
- **Calculation:** Auto-calculates `wave_height_divisor` = (3.9 * 100) / 39 = 10 cm per LED
- **Example:** 1.5m wave → 15 LEDs lit
- **Typical Range:** `2.0-5.0` meters depending on surf location

#### `MAX_WIND_SPEED_MPS`
```cpp
#define MAX_WIND_SPEED_MPS 13.0
```
- **Purpose:** Maximum wind speed that fills entire wind speed strip
- **Type:** Float (meters per second)
- **Calculation:** Auto-calculates wind scaling = (43 - 2) / 13.0 = 3.15 LEDs per m/s
- **Example:** 6.5 m/s wind → 20 LEDs lit
- **Typical Range:** `10.0-20.0` m/s depending on location

**Why -2 LEDs for wind?**
Bottom LED = status indicator, Top LED = wind direction → only 41 usable LEDs for wind speed

---

### 5. Wave Animation

Controls the blinking/wave effect when thresholds are exceeded.

#### `WAVE_BRIGHTNESS_MIN_PERCENT` / `WAVE_BRIGHTNESS_MAX_PERCENT`
```cpp
#define WAVE_BRIGHTNESS_MIN_PERCENT 50
#define WAVE_BRIGHTNESS_MAX_PERCENT 110
```
- **Purpose:** Brightness range during blinking animation
- **Type:** Integer (0-200%)
- **Effect:** LEDs pulse between 50% and 110% brightness
- **Recommended:** Min 30-60%, Max 100-150%
- **Note:** Values >100% create extra-bright alerts

#### `WAVE_LENGTH_SIDE` / `WAVE_LENGTH_CENTER`
```cpp
#define WAVE_LENGTH_SIDE 10.0
#define WAVE_LENGTH_CENTER 12.0
```
- **Purpose:** How many LEDs per wave cycle
- **Type:** Float (LEDs)
- **Effect:** Smaller = tighter waves, Larger = smoother waves
- **Recommended:** 8.0-15.0 for side strips, 10.0-18.0 for center
- **Visual:** 10.0 = wave repeats every 10 LEDs

#### `WAVE_SPEED_MULTIPLIER`
```cpp
#define WAVE_SPEED_MULTIPLIER 1.2
```
- **Purpose:** Animation speed
- **Type:** Float (multiplier)
- **Effect:** Higher = faster animation
- **Recommended:** 0.8-2.0
- **Default:** 1.2 (20% faster than base speed)

---

## Auto-Calculated Values

**DO NOT MODIFY THESE** - They are computed from your admin configuration:

### Strip Directions
```cpp
#define WAVE_HEIGHT_FORWARD (WAVE_HEIGHT_BOTTOM < WAVE_HEIGHT_TOP)
```
- Returns `true` if forward, `false` if reverse

### Strip Lengths
```cpp
#define WAVE_HEIGHT_LENGTH (abs(WAVE_HEIGHT_TOP - WAVE_HEIGHT_BOTTOM) + 1)
```
- Calculates number of LEDs in the strip

### Special Function LEDs
```cpp
#define STATUS_LED_INDEX WIND_SPEED_BOTTOM      // LED 101
#define WIND_DIRECTION_INDEX WIND_SPEED_TOP     // LED 59
```

### Scaling Factors
```cpp
// Wind speed scaling
float wind_scale_numerator = WIND_SPEED_LENGTH - 2;  // 41 usable LEDs
float wind_scale_denominator = MAX_WIND_SPEED_MPS;   // 13.0 m/s

// Wave height scaling
uint8_t wave_height_divisor = (MAX_WAVE_HEIGHT_METERS * 100) / WAVE_HEIGHT_LENGTH;  // 10 cm per LED
```

---

## Verification Checklist

After uploading, verify via Serial Monitor (115200 baud):

```
✅ Arduino ID matches database
✅ LED strip directions correct (FORWARD/REVERSE)
✅ Strip lengths match physical LED counts
✅ Status LED index = wind strip bottom
✅ Wind direction LED index = wind strip top
✅ Wave height scaling: cm per LED looks reasonable
✅ Wind speed scaling: LEDs per m/s looks reasonable
✅ Animation settings match expectations
```

---

## Common Configurations

### Wooden Lamp (Reference)
```cpp
const int ARDUINO_ID = 2;
#define TOTAL_LEDS 146
#define WAVE_HEIGHT_BOTTOM 11
#define WAVE_HEIGHT_TOP 49
#define WAVE_PERIOD_BOTTOM 107
#define WAVE_PERIOD_TOP 145
#define WIND_SPEED_BOTTOM 101
#define WIND_SPEED_TOP 59
#define MAX_WAVE_HEIGHT_METERS 3.9
#define MAX_WIND_SPEED_MPS 13.0
```

### Small Lamp (47 LEDs)
```cpp
const int ARDUINO_ID = 4;
#define TOTAL_LEDS 47
#define WAVE_HEIGHT_BOTTOM 0
#define WAVE_HEIGHT_TOP 14
#define WAVE_PERIOD_BOTTOM 15
#define WAVE_PERIOD_TOP 29
#define WIND_SPEED_BOTTOM 30
#define WIND_SPEED_TOP 46
#define MAX_WAVE_HEIGHT_METERS 2.8  // 14 LEDs × 20cm = 2.8m
#define MAX_WIND_SPEED_MPS 15.0     // 15 LEDs for wind
```

---

## Troubleshooting

### Problem: LEDs light in wrong direction
**Cause:** Strip wired backwards
**Fix:** Swap BOTTOM and TOP values, or flip physical strip

### Problem: Wave height doesn't use full strip
**Cause:** `MAX_WAVE_HEIGHT_METERS` too high
**Fix:** Reduce to smaller value (try 2.0-3.0m)

### Problem: Wind speed maxes out too early
**Cause:** `MAX_WIND_SPEED_MPS` too low
**Fix:** Increase to larger value (try 15-20 m/s)

### Problem: Blinking too fast/slow
**Cause:** `WAVE_SPEED_MULTIPLIER` not tuned
**Fix:** Adjust between 0.5-2.0 until comfortable

### Problem: Blinking too dim
**Cause:** `WAVE_BRIGHTNESS_MAX_PERCENT` too low
**Fix:** Increase to 120-150%

---

## Advanced: Understanding Scaling

### Wave Height Calculation
```cpp
wave_height_divisor = (MAX_WAVE_HEIGHT_METERS * 100) / WAVE_HEIGHT_LENGTH
// Example: (3.9 * 100) / 39 = 10 cm per LED

LED count = (wave_height_cm / wave_height_divisor) + 1
// Example: 150cm wave → (150 / 10) + 1 = 16 LEDs
```

### Wind Speed Calculation
```cpp
usable_wind_leds = WIND_SPEED_LENGTH - 2
wind_scaling = usable_wind_leds / MAX_WIND_SPEED_MPS
// Example: (43 - 2) / 13.0 = 3.15 LEDs per m/s

LED count = wind_speed_mps * wind_scaling
// Example: 6.5 m/s → 6.5 * 3.15 = 20 LEDs
```

### Wave Period (No Scaling)
```cpp
LED count = wave_period_seconds
// Example: 8 second period → 8 LEDs (1:1 mapping)
```

---

## Support

**Issues?** Check:
1. Serial monitor output for configuration summary
2. STATUS_LED_GUIDE.md for LED status meanings
3. claude_readthis_before_making_arduino_code_changes.md for critical notes

**Database Integration:**
- Arduino ID must exist in `lamps` table
- `lamps.arduino_id` must match `ARDUINO_ID` in code
- Run `/api/info` endpoint to verify lamp identity

---

**Last Updated:** 2025-12-13
**Template Version:** 2.0.0-template
