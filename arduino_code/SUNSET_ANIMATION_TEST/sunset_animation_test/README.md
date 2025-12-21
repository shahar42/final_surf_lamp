# Sunset Animation Test

Standalone Arduino sketch to test the sunset animation visually without needing WiFi, backend, or API.

## Hardware Configuration

**Pre-configured for Maayan's Lamp:**
- Total LEDs: 56
- Wave Height Strip: 14 LEDs (forward)
- Wave Period Strip: 14 LEDs (forward)
- Wind Speed Strip: 18 LEDs (reverse)

## Files

- `sunset_animation_test.ino` - Main test sketch
- `animation.h` - Sunset animation library (shared with main lamp code)

## How to Use

### Upload to Arduino

1. Open `sunset_animation_test.ino` in Arduino IDE
2. Select board: ESP32 Dev Module
3. Upload to Arduino

### Trigger Animation

**Two modes available:**

#### Mode 1: Button Trigger (Default)
```cpp
#define AUTO_PLAY false
```
- Press boot button (GPIO 0) to play animation
- Animation plays once per button press

#### Mode 2: Auto-Loop
```cpp
#define AUTO_PLAY true
#define AUTO_PLAY_INTERVAL 60000  // 60 seconds
```
- Animation plays automatically every 60 seconds
- Good for continuous demo/testing

### Configuration Options

```cpp
#define ANIMATION_DURATION 30  // Animation length in seconds (default: 30s)
#define BRIGHTNESS 75          // LED brightness 0-255 (default: 75)
#define AUTO_PLAY_INTERVAL 60000  // Time between auto-plays in milliseconds
```

## Animation Sequence

1. **Orange** (0-10s) - Warm sunset start
2. **Pink** (10-20s) - Transition to twilight
3. **Purple** (20-25s) - Deep twilight colors
4. **Deep Blue** (25-30s) - Night approaching
5. **Fade to black** (30-32s) - Complete darkness

Each strip shows the full gradient from bottom to top, with slight hue variations for depth.

## Serial Monitor Output

```
🌅 ================================================================
🌅 SUNSET ANIMATION TEST
🌅 ================================================================

Total LEDs: 56
Wave Height: 14 LEDs (indices 3→16, FORWARD)
Wave Period: 14 LEDs (indices 42→55, FORWARD)
Wind Speed: 18 LEDs (indices 38→21, REVERSE)

Animation duration: 30 seconds
Auto-play: ENABLED
Auto-play interval: 60 seconds

💡 LED strip initialized
🌈 Running startup rainbow...
✅ Setup complete!

🎬 Press button to trigger sunset animation
================================================================

🌅 ============================================================
🌅 STARTING SUNSET ANIMATION
🌅 ============================================================
🌅 Starting sunset animation...
   Wave Height: 14 LEDs | Wave Period: 14 LEDs | Wind Speed: 18 LEDs
✅ Sunset animation complete
✅ ANIMATION COMPLETE
============================================================
```

## Adapting for Other Lamps

To test on a different lamp configuration, modify these values:

```cpp
// Example: 3-strip lamp with 20 LEDs each
#define TOTAL_LEDS 60

#define WAVE_HEIGHT_START 0
#define WAVE_HEIGHT_END 19
#define WAVE_HEIGHT_LENGTH 20
#define WAVE_HEIGHT_FORWARD true

#define WAVE_PERIOD_START 20
#define WAVE_PERIOD_END 39
#define WAVE_PERIOD_LENGTH 20
#define WAVE_PERIOD_FORWARD true

#define WIND_SPEED_START 59  // Reverse strip
#define WIND_SPEED_END 40
#define WIND_SPEED_LENGTH 20
#define WIND_SPEED_FORWARD false
```

## Troubleshooting

**LEDs not lighting:**
- Check `LED_PIN` matches your wiring (default: GPIO 2)
- Verify power supply is adequate for 56 LEDs
- Check serial monitor for initialization messages

**Animation looks wrong:**
- Verify strip indices match your physical wiring
- Check `FORWARD/REVERSE` direction settings
- Adjust `BRIGHTNESS` if colors look washed out

**Performance issues:**
- 30-second animation = 600 frames @ 20 FPS
- ESP32 handles this easily, but reduce `ANIMATION_DURATION` if needed

## Integration with Main Lamp

This exact animation runs automatically on the main lamp every day at sunset (±15 min window). The `animation.h` file is shared between this test and the production lamp code.
