# Legends Marking - Physical Lamp Labeling Tool

**Purpose:** Calculate exact LED positions for physical marking on surf lamps.

Use this tool to determine which LEDs to mark with labels/stickers showing wave heights and wind speeds, making it easy to read surf conditions at a glance.

---

## Usage

```bash
cd /path/to/lamp_refractored/Legends_marking
python3 calculate_led_markers.py
```

The script automatically reads the lamp configuration from `../lamp_template/Config.h`.

---

## What It Shows

The script calculates LED positions for:

**Wave Height Markers:**
- 1 meter waves
- 2 meter waves
- 3 meter waves

**Wind Speed Markers:**
- 10 knots wind
- 20 knots wind
- 30 knots wind

---

## Example Output

```
PHYSICAL MARKING GUIDE
======================================================================

Use stickers, tape, or permanent marker to label these LED positions:

WAVE HEIGHT STRIP:
  → Mark LED #11 = 1.0m waves
  → Mark LED #19 = 2.0m waves

WIND SPEED STRIP:
  → Mark LED #53 = 10 knots
  → Mark LED #46 = 20 knots
  → Mark LED #39 = 30 knots
```

---

## How to Mark the Lamp

**Materials:**
- Small label maker or masking tape
- Permanent marker
- Ruler

**Steps:**
1. Run the script to get LED positions for your lamp
2. Power on the lamp to see LED positions
3. Use the script output to identify which physical LEDs to mark
4. Apply small labels next to those LEDs:
   - "1m", "2m" for wave height strip
   - "10kt", "20kt", "30kt" for wind speed strip

**Tips:**
- Mark on the lamp housing, not directly on LEDs
- Use small labels to avoid blocking LED light
- Consider using different colors for wave vs wind markers
- Test with actual surf data to verify positions

---

## How It Works

The script uses the same LED calculation formulas as the Arduino firmware:

**Wave Height:**
```
num_leds = (wave_height_m / MAX_WAVE_HEIGHT_METERS) * WAVE_HEIGHT_LENGTH
```

**Wind Speed:**
```
wind_mps = wind_knots * 0.514444
num_leds = (wind_mps / MAX_WIND_SPEED_MPS) * (WIND_SPEED_LENGTH - 2)
```

This ensures the markers match exactly what the lamp displays.

---

## Notes

- **Wave Period Strip:** Not included (no standard markers needed, 1 LED = 1 second)
- **Wind Direction LED:** Top LED of wind strip (shows direction color, not speed)
- **Status LED:** Bottom LED of wind strip (shows connection status)
- **Maximum values:** When conditions exceed max, all LEDs light up (no need for marker)

---

## For Different Lamps

Each lamp has its own configuration in Config.h:
- Different total LED counts
- Different strip mappings
- Different max wave height / wind speed

The script reads your specific lamp's Config.h and calculates positions accordingly.

---

**Created:** December 2024
**Purpose:** Help users physically mark their lamps for easier surf condition reading
