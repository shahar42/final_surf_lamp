# Main Reference Arduino Template

This directory contains the **configuration-driven template** for all Surf Lamp Arduino firmware.

## Contents

- **main_reference.ino** - Configuration-driven Arduino template
- **CONFIGURATION_GUIDE.md** - Complete admin configuration guide
- **ServerDiscovery.h** - Server discovery header for automatic API endpoint detection
- **STATUS_LED_GUIDE.md** - Complete guide to status LED colors and meanings
- **claude_readthis_before_making_arduino_code_changes.md** - Critical instructions for code modifications

## Purpose

This template uses a **configuration-driven design** where admins only modify essential parameters. Everything else (strip lengths, directions, scaling factors) is auto-calculated.

## Quick Start

```bash
# 1. Copy template files
cp arduino_code/template_ino/main_reference.ino arduino_code/new_lamp/
cp arduino_code/template_ino/ServerDiscovery.h arduino_code/new_lamp/

# 2. Edit CONFIG SECTION in main_reference.ino
# 3. Upload to Arduino
# 4. Verify via Serial Monitor (115200 baud)
```

See **CONFIGURATION_GUIDE.md** for detailed parameter explanations.

## Admin Configuration Parameters

Admins configure **only these values**:

1. **Device Identity:** Arduino ID
2. **Hardware Setup:** LED pin, total LEDs, chipset, brightness
3. **LED Strip Mapping:** Bottom/top LED indices for each strip
4. **Surf Data Scaling:** Max wave height, max wind speed
5. **Wave Animation:** Brightness range, wave length, speed

**Everything else is auto-calculated:**
- Strip directions (forward/reverse)
- Strip lengths
- Special function LEDs (status, wind direction)
- Scaling factors (cm per LED, LEDs per m/s)

## Key Features

- ✅ **Configuration-driven** - No code editing required for new lamps
- ✅ **Auto-calculated scaling** - Dynamic mapping based on strip lengths
- ✅ **Direction auto-detection** - Forward/reverse determined from bottom < top
- ✅ **Wind direction LED in quiet hours** - Fixed 2025-12-13
- ✅ **Comprehensive debug output** - Serial monitor shows all calculated values
- ✅ **Three-strip LED mapping** - Wave height, wave period, wind speed
- ✅ **Robust WiFi diagnostics** - Detailed error messages and reconnection
- ✅ **Theme system** - 5 LED color themes
- ✅ **Threshold alerting** - Blinking wave animation
- ✅ **Off hours vs Quiet hours** - Priority-based sleep modes

## Example Configurations

### Wooden Lamp (146 LEDs)
```cpp
const int ARDUINO_ID = 2;
#define TOTAL_LEDS 146
#define WAVE_HEIGHT_BOTTOM 11
#define WAVE_HEIGHT_TOP 49       // → 39 LEDs, FORWARD
#define WIND_SPEED_BOTTOM 101
#define WIND_SPEED_TOP 59        // → 43 LEDs, REVERSE
#define MAX_WAVE_HEIGHT_METERS 3.9
```

### Small Lamp (47 LEDs)
```cpp
const int ARDUINO_ID = 4;
#define TOTAL_LEDS 47
#define WAVE_HEIGHT_BOTTOM 0
#define WAVE_HEIGHT_TOP 14       // → 15 LEDs, FORWARD
#define WIND_SPEED_BOTTOM 30
#define WIND_SPEED_TOP 46        // → 17 LEDs, FORWARD
#define MAX_WAVE_HEIGHT_METERS 2.8
```

## Serial Monitor Output

After upload, you'll see:
```
🌊 SURF LAMP - CONFIGURATION-DRIVEN TEMPLATE
🔧 Arduino ID: 2

📍 LED STRIP CONFIGURATION:
   Wave Height: LEDs 11→49 (39 total, FORWARD)
   Wind Speed:  LEDs 101→59 (43 total, REVERSE)

📊 SCALING CONFIGURATION:
   Max Wave Height: 3.9 meters
   Wave Height Scaling: 10 cm per LED
   Wind Speed Scaling: 3.2 LEDs per m/s
```

## Version History

- **2025-12-13:** Configuration-driven redesign + quiet hours wind direction fix
- **2025-12-12:** Initial template creation from wooden lamp (Arduino ID 2)

---

**Read CONFIGURATION_GUIDE.md for complete documentation**
