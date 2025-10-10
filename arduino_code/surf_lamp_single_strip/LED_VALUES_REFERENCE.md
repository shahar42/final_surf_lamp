# LED Physical Values Reference - Single Strip Lamp (Arduino ID 1)

**Date Created:** 10/10/2025
**Hardware:** Single continuous WS2812B LED strip (47 LEDs total)
**Firmware:** `surf_lamp_single_strip.ino` v2.0.0

---

## 🌊 Wave Height Strip (Right Side)
**LEDs:** 1→14 (forward direction)
**Formula:** `(waveHeight_cm / 25) + 1`
**Scaling:** 25 cm (0.25 m) per LED
**Maximum Display:** 3.5 meters

| LED Index | Position | Wave Height Range |
|-----------|----------|-------------------|
| 1 | Bottom | 0-25 cm (0.00-0.25 m) |
| 2 | ↑ | 25-50 cm (0.25-0.50 m) |
| 3 | ↑ | 50-75 cm (0.50-0.75 m) |
| 4 | ↑ | 75-100 cm (0.75-1.00 m) |
| 5 | ↑ | 100-125 cm (1.00-1.25 m) |
| 6 | ↑ | 125-150 cm (1.25-1.50 m) |
| 7 | ↑ | 150-175 cm (1.50-1.75 m) |
| 8 | ↑ | 175-200 cm (1.75-2.00 m) |
| 9 | ↑ | 200-225 cm (2.00-2.25 m) |
| 10 | ↑ | 225-250 cm (2.25-2.50 m) |
| 11 | ↑ | 250-275 cm (2.50-2.75 m) |
| 12 | ↑ | 275-300 cm (2.75-3.00 m) |
| 13 | ↑ | 300-325 cm (3.00-3.25 m) |
| 14 | Top | 325-350 cm (3.25-3.50 m) |

---

## 🌊 Wave Period Strip (Left Side)
**LEDs:** 33→46 (forward direction)
**Formula:** Direct 1:1 mapping `wavePeriod_s`
**Scaling:** 1 second per LED
**Maximum Display:** 14 seconds

| LED Index | Position | Wave Period |
|-----------|----------|-------------|
| 33 | Bottom | 1 second |
| 34 | ↑ | 2 seconds |
| 35 | ↑ | 3 seconds |
| 36 | ↑ | 4 seconds |
| 37 | ↑ | 5 seconds |
| 38 | ↑ | 6 seconds |
| 39 | ↑ | 7 seconds |
| 40 | ↑ | 8 seconds |
| 41 | ↑ | 9 seconds |
| 42 | ↑ | 10 seconds |
| 43 | ↑ | 11 seconds |
| 44 | ↑ | 12 seconds |
| 45 | ↑ | 13 seconds |
| 46 | Top | 14 seconds |

---

## 💨 Wind Speed Strip (Center)
**LEDs:** 30→17 (REVERSE direction)
**Formula:** `windSpeed_mps * 12.0 / 13.0`
**Scaling:** 1.08 m/s (2.1 knots) per LED
**Maximum Display:** 13 m/s (25.2 knots)

### Active Wind Speed LEDs (29→18)
*LED 30 = Status indicator, LED 17 = Wind direction*

| Physical LED | Logical Position | Wind Speed (m/s) | Wind Speed (knots) |
|--------------|------------------|------------------|--------------------|
| 29 | LED 1 (Bottom) | 1.08 | 2.1 |
| 28 | LED 2 | 2.17 | 4.2 |
| 27 | LED 3 | 3.25 | 6.3 |
| 26 | LED 4 | 4.33 | 8.4 |
| 25 | LED 5 | 5.42 | 10.5 |
| 24 | LED 6 | 6.50 | 12.6 |
| 23 | LED 7 | 7.58 | 14.7 |
| 22 | LED 8 | 8.67 | 16.8 |
| 21 | LED 9 | 9.75 | 18.9 |
| 20 | LED 10 | 10.83 | 21.0 |
| 19 | LED 11 | 11.92 | 23.1 |
| 18 | LED 12 (Top) | 13.00 | 25.2 |

### Special LEDs
- **LED 30:** Status indicator (blue=connecting, green=operational, red=error, yellow=config)
- **LED 17:** Wind direction (green=N, yellow=E, red=S, blue=W)

---

## 📊 Comparison with Original 3-Strip Lamp

| Feature | Original Lamp | Single-Strip Lamp |
|---------|--------------|-------------------|
| **Wave Height LEDs** | 15 LEDs | 14 LEDs |
| **Wave Period LEDs** | 15 LEDs | 14 LEDs |
| **Wind Speed LEDs** | 20 total (18 usable) | 14 total (12 usable) |
| **Wind Scale Factor** | 18.0 / 13.0 | 12.0 / 13.0 |
| **Wind per LED** | 0.72 m/s (1.4 knots) | 1.08 m/s (2.1 knots) |
| **Wave Height per LED** | 25 cm | 25 cm *(unchanged)* |
| **Wave Period per LED** | 1 second | 1 second *(unchanged)* |

---

## 🧮 Calculation Examples

### Example 1: Moderate Conditions
**Input:** Wave height = 150 cm, Period = 8s, Wind = 6.5 m/s
- **Wave Height LEDs:** (150 / 25) + 1 = 7 LEDs (up to LED 7)
- **Wave Period LEDs:** 8 LEDs (up to LED 40)
- **Wind Speed LEDs:** 6.5 * 12 / 13 = 6 LEDs (up to LED 24)

### Example 2: Epic Swell
**Input:** Wave height = 300 cm, Period = 14s, Wind = 13 m/s
- **Wave Height LEDs:** (300 / 25) + 1 = 13 LEDs (up to LED 13)
- **Wave Period LEDs:** 14 LEDs (entire strip lit - LED 46)
- **Wind Speed LEDs:** 13 * 12 / 13 = 12 LEDs (entire strip lit - LED 18)

### Example 3: Flat Conditions
**Input:** Wave height = 50 cm, Period = 3s, Wind = 2 m/s
- **Wave Height LEDs:** (50 / 25) + 1 = 3 LEDs (up to LED 3)
- **Wave Period LEDs:** 3 LEDs (up to LED 35)
- **Wind Speed LEDs:** 2 * 12 / 13 = 1.8 → 2 LEDs (up to LED 28)

---

## ⚙️ Configuration Constants

Located in `surf_lamp_single_strip.ino`:

```cpp
// LED Mapping Configuration (lines 139-145)
struct LEDMappingConfig {
    float wind_scale_numerator = 12.0;      // Single-strip: 12 usable LEDs
    float wind_scale_denominator = 13.0;    // Max wind: 13 m/s
    float mps_to_knots_factor = 1.94384;    // Conversion: m/s to knots
    uint8_t wave_height_divisor = 25;       // 25 cm per LED
    float threshold_brightness_multiplier = 1.4;  // 40% brighter when threshold exceeded
};
```

---

## 🔧 Adjustment Guide

### To Change Wind Sensitivity
Modify `wind_scale_numerator` (line 141):
- **Higher value** = more sensitive (more LEDs at lower wind)
- **Lower value** = less sensitive (fewer LEDs at higher wind)
- **Current:** 12.0 fills strip at 13 m/s

### To Change Wave Height Sensitivity
Modify `wave_height_divisor` (line 144):
- **Higher value** = less sensitive (fewer LEDs for same height)
- **Lower value** = more sensitive (more LEDs for same height)
- **Current:** 25 cm per LED

### To Change Wave Period Sensitivity
Wave period uses 1:1 mapping (cannot be adjusted without code changes)

---

## 📝 Notes

1. **Wind strip direction**: Physical LEDs count DOWN (30→17) but logical positions count UP (1→12)
2. **Quiet hours mode**: Shows only the TOP LED of each strip (highest active LED)
3. **Threshold blinking**: LEDs blink with wave animation when surf exceeds user thresholds
4. **Reserved LEDs**: LED 30 (status) and LED 17 (wind direction) never show wind speed data
5. **Minimum LEDs**: All strips show at least 1 LED when any data > 0 is received

---

**Last Updated:** 10/10/2025
**Firmware Version:** 2.0.0-single-strip
**Tested:** ✅ Calculations verified against original lamp formulas
