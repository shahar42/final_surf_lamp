# Sapir's Surf Lamp - LED Value Reference Card

**Arduino ID:** 5
**Configuration:** 3 separate LED strips

---

## 📊 LED Strip Specifications

### 🌊 Wave Height Strip (Right Side)
- **Total LEDs:** 14
- **Value per LED:** 25 cm (0.25 meters)
- **Range:** 0 - 3.5 meters
- **Formula:** `waveHeight_cm / 25 + 1`

| LEDs Lit | Wave Height |
|----------|-------------|
| 1 LED    | 0-25 cm     |
| 2 LEDs   | 26-50 cm    |
| 4 LEDs   | 76-100 cm   |
| 8 LEDs   | 176-200 cm  |
| 14 LEDs  | 326-350 cm  |

---

### 🌀 Wind Speed Strip (Center)
- **Total LEDs:** 15 (13 usable for wind speed)
- **Reserved LEDs:**
  - Bottom (LED 0): Wind direction indicator
  - Top: Status LED
- **Value per LED:** ~1.5 m/s (~2.9 knots)
- **Range:** 0 - 15.43 m/s (0 - 30 knots)
- **Formula:** `windSpeed_mps * 13.0 / 15.43`

| LEDs Lit | Wind Speed (m/s) | Wind Speed (knots) |
|----------|------------------|--------------------|
| 1 LED    | 0-1.19 m/s       | 0-2.3 knots        |
| 2 LEDs   | 1.19-2.37 m/s    | 2.3-4.6 knots      |
| 4 LEDs   | 3.56-4.75 m/s    | 6.9-9.2 knots      |
| 6 LEDs   | 5.94-7.12 m/s    | 11.5-13.8 knots    |
| 10 LEDs  | 10.68-11.87 m/s  | 20.7-23.0 knots    |
| 13 LEDs  | 14.24+ m/s       | 27.6+ knots        |

---

### 🌊 Wave Period Strip (Left Side)
- **Total LEDs:** 14
- **Value per LED:** 1 second
- **Range:** 0 - 14 seconds
- **Formula:** `wavePeriod_s` (1:1 mapping)

| LEDs Lit | Wave Period |
|----------|-------------|
| 1 LED    | 1 second    |
| 5 LEDs   | 5 seconds   |
| 10 LEDs  | 10 seconds  |
| 14 LEDs  | 14 seconds  |

---

## 🎨 LED Indicators

### Wind Direction (Bottom LED of Center Strip)
- **North (0°, 300-360°):** Green
- **East (10-180°):** Yellow
- **South (180-250°):** Red
- **West (250-300°):** Blue

### Status LED (Top of Center Strip)
- **Blinking Green:** Fresh data (< 30 min old)
- **Blinking Orange:** Stale data (> 30 min old)
- **Blinking Red:** WiFi disconnected
- **Blinking Blue:** Connecting to WiFi

---

## 📐 Scaling Comparison with Other Lamps

| Feature | Sapir's Lamp (ID 5) | Main Lamp (ID 4433) | Wooden Lamp (ID 2) |
|---------|---------------------|---------------------|---------------------|
| Wind LEDs | 15 (13 usable) | 20 (18 usable) | 43 (41 usable) |
| Wind max | 38 knots | 38 knots | 38 knots |
| m/s per LED | 1.5 m/s | 1.09 m/s | 0.48 m/s |
| knots per LED | 2.9 knots | 2.1 knots | 0.93 knots |
| Wave Height LEDs | 14 | 15 | 39 |
| cm per LED | 25 cm | 25 cm | 10 cm |
| Wave Period LEDs | 14 | 15 | 39 |
| s per LED | 1 s | 1 s | 1 s |

**Result:** Sapir's lamp has **coarsest granularity** (largest steps), Main lamp is **medium**, Wooden lamp has **finest granularity** (smallest steps).
