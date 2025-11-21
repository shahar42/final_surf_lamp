#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <Arduino.h>
#include <FastLED.h>
#include "../config/SystemConfig.h"
#include "ThemeManager.h"

/**
 * LED Controller
 * - Low-level LED strip control
 * - Hardware abstraction layer
 * - Clean interface for display logic
 * - Single responsibility: LED manipulation only
 */

class LEDController {
private:
    CRGB* leds;              // Pointer to LED array
    ThemeManager& themeManager;

    // Animation state
    float blinkPhase;
    unsigned long lastBlinkUpdate;
    float statusPhase;
    unsigned long lastStatusUpdate;

public:
    /**
     * Constructor
     * @param ledArray Pointer to FastLED array
     * @param themes Reference to theme manager
     */
    LEDController(CRGB* ledArray, ThemeManager& themes)
        : leds(ledArray)
        , themeManager(themes)
        , blinkPhase(0.0)
        , lastBlinkUpdate(0)
        , statusPhase(0.0)
        , lastStatusUpdate(0)
    {}

    // ======================== BASIC LED CONTROL ========================

    /**
     * Clear all LEDs
     */
    void clearAll() {
        FastLED.clear();
    }

    /**
     * Show LED updates (call after making changes)
     */
    void show() {
        FastLED.show();
    }

    /**
     * Set global brightness
     */
    void setBrightness(uint8_t brightness) {
        FastLED.setBrightness(brightness);
    }

    // ======================== WAVE HEIGHT STRIP ========================

    /**
     * Update wave height LEDs (solid color)
     * @param numLEDs Number of LEDs to light (0 to WAVE_HEIGHT_LENGTH)
     * @param color Color to display
     */
    void setWaveHeightLEDs(int numLEDs, CHSV color) {
        for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
            int index = WAVE_HEIGHT_START + i;
            leds[index] = (i < numLEDs) ? color : CRGB::Black;
        }
    }

    /**
     * Update wave height LEDs with wave animation
     * @param numLEDs Number of LEDs to animate
     * @param baseColor Base color for animation
     * @param waveLength Wave length in LEDs
     * @param minBrightness Minimum brightness (0.0-1.0)
     * @param maxBrightness Maximum brightness (0.0-1.0)
     */
    void setWaveHeightLEDsAnimated(int numLEDs, CHSV baseColor,
                                   float waveLength, float minBrightness, float maxBrightness) {
        for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
            int index = WAVE_HEIGHT_START + i;

            if (i < numLEDs) {
                // Calculate wave position
                float wavePhase = blinkPhase * WAVE_SPEED - (i * 2.0 * PI / waveLength);
                float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
                int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

                leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
            } else {
                leds[index] = CRGB::Black;
            }
        }
    }

    // ======================== WAVE PERIOD STRIP ========================

    /**
     * Update wave period LEDs (solid color)
     * @param numLEDs Number of LEDs to light (0 to WAVE_PERIOD_LENGTH)
     * @param color Color to display
     */
    void setWavePeriodLEDs(int numLEDs, CHSV color) {
        for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
            int index = WAVE_PERIOD_START + i;
            leds[index] = (i < numLEDs) ? color : CRGB::Black;
        }
    }

    // ======================== WIND SPEED STRIP (REVERSE) ========================

    /**
     * Update wind speed LEDs (solid color)
     * Wind strip runs BACKWARDS: LED 30 (bottom) -> LED 17 (top)
     * Skips LED 30 (status) and LED 17 (wind direction)
     * @param numLEDs Number of LEDs to light (0 to WIND_SPEED_LENGTH-2)
     * @param color Color to display
     */
    void setWindSpeedLEDs(int numLEDs, CHSV color) {
        // Wind strip: LEDs 29,28,27...18 (skip 30 and 17)
        for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
            int index = WIND_SPEED_START - i;  // Count backwards from 30
            int ledPosition = i - 1;           // Logical position (0-based)

            leds[index] = (ledPosition < numLEDs) ? color : CRGB::Black;
        }
    }

    /**
     * Update wind speed LEDs with wave animation
     * @param numLEDs Number of LEDs to animate
     * @param baseColor Base color for animation
     * @param waveLength Wave length in LEDs
     * @param minBrightness Minimum brightness (0.0-1.0)
     * @param maxBrightness Maximum brightness (0.0-1.0)
     */
    void setWindSpeedLEDsAnimated(int numLEDs, CHSV baseColor,
                                  float waveLength, float minBrightness, float maxBrightness) {
        for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
            int index = WIND_SPEED_START - i;  // Count backwards
            int ledPosition = i - 1;           // Logical position

            if (ledPosition < numLEDs) {
                // Calculate wave position
                float wavePhase = blinkPhase * WAVE_SPEED - (ledPosition * 2.0 * PI / waveLength);
                float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
                int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

                leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
            } else {
                leds[index] = CRGB::Black;
            }
        }
    }

    // ======================== SPECIAL LEDS ========================

    /**
     * Set status LED (LED 30)
     * @param color Color to display
     */
    void setStatusLED(CRGB color) {
        leds[STATUS_LED_INDEX] = color;
    }

    /**
     * Set status LED with breathing animation
     * @param color Base color
     */
    void setStatusLEDBreathing(CRGB color) {
        // Update animation phase
        if (millis() - lastStatusUpdate >= STATUS_LED_UPDATE_RATE) {
            statusPhase += 0.05;  // ~1.25-second cycle
            if (statusPhase >= 2 * PI) statusPhase = 0.0;
            lastStatusUpdate = millis();
        }

        // Gentle breathing pattern (70% to 100% brightness)
        float brightnessFactor = 0.7 + 0.3 * sin(statusPhase);
        int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(MAX_BRIGHTNESS * brightnessFactor));

        // Convert RGB to HSV for brightness control
        CHSV hsvColor = rgb2hsv_approximate(color);
        hsvColor.val = adjustedBrightness;

        leds[STATUS_LED_INDEX] = hsvColor;
    }

    /**
     * Set wind direction LED (LED 17)
     * Color coding: North=Green, East=Yellow, South=Red, West=Blue
     * @param windDirection Wind direction in degrees (0-360)
     */
    void setWindDirectionLED(int windDirection) {
        CRGB color;

        // Wind direction color coding
        if ((windDirection >= 0 && windDirection <= 10) || (windDirection >= 300 && windDirection <= 360)) {
            color = CRGB::Green;   // North - Green
        } else if (windDirection > 10 && windDirection <= 180) {
            color = CRGB::Yellow;  // East - Yellow
        } else if (windDirection > 180 && windDirection <= 250) {
            color = CRGB::Red;     // South - Red
        } else if (windDirection > 250 && windDirection < 300) {
            color = CRGB::Blue;    // West - Blue
        } else {
            color = CRGB::White;   // Invalid/unknown
        }

        leds[WIND_DIRECTION_INDEX] = color;
    }

    // ======================== ANIMATION CONTROL ========================

    /**
     * Update animation phase (call periodically)
     * Updates the blink phase for wave animations
     */
    void updateAnimationPhase() {
        unsigned long currentMillis = millis();
        if (currentMillis - lastBlinkUpdate >= ANIMATION_UPDATE_RATE) {
            blinkPhase += 0.0419;  // 1.5-second cycle
            if (blinkPhase >= 2 * PI) blinkPhase = 0.0;
            lastBlinkUpdate = currentMillis;
        }
    }

    /**
     * Get current animation phase (for external use)
     */
    float getAnimationPhase() const {
        return blinkPhase;
    }

    /**
     * Reset animation phase
     */
    void resetAnimationPhase() {
        blinkPhase = 0.0;
        lastBlinkUpdate = millis();
    }

    // ======================== TEST FUNCTIONS ========================

    /**
     * LED test sequence
     * Tests all LED strips and special LEDs
     */
    void runTestSequence() {
        Serial.println("🧪 Running LED test sequence...");

        // Test wave height strip (blue)
        Serial.println("   Testing Wave Height strip (LEDs 1-14)...");
        setWaveHeightLEDs(WAVE_HEIGHT_LENGTH, CHSV(160, 255, 255));
        show();
        delay(1000);

        // Test wave period strip (yellow)
        Serial.println("   Testing Wave Period strip (LEDs 33-46)...");
        clearAll();
        setWavePeriodLEDs(WAVE_PERIOD_LENGTH, CHSV(60, 255, 255));
        show();
        delay(1000);

        // Test wind speed strip (white)
        Serial.println("   Testing Wind Speed strip (LEDs 30-17)...");
        clearAll();
        setWindSpeedLEDs(WIND_SPEED_LENGTH - 2, CHSV(0, 50, 255));
        show();
        delay(1000);

        // Test status LED (green)
        Serial.println("   Testing status LED (LED 30)...");
        clearAll();
        setStatusLED(CRGB::Green);
        show();
        delay(1000);

        // Test wind direction LED (red)
        Serial.println("   Testing wind direction LED (LED 17)...");
        clearAll();
        setWindDirectionLED(180);  // South = Red
        show();
        delay(1000);

        // Rainbow test on entire strip
        Serial.println("   Running rainbow test on all LEDs...");
        for (int hue = 0; hue < 256; hue += 5) {
            fill_solid(leds, TOTAL_LEDS, CHSV(hue, 255, 255));
            show();
            delay(20);
        }

        clearAll();
        show();
        Serial.println("✅ LED test completed");
    }

    // ======================== UTILITY FUNCTIONS ========================

    /**
     * Set a single LED by index
     * @param index LED index (0 to TOTAL_LEDS-1)
     * @param color Color to set
     */
    void setLED(int index, CRGB color) {
        if (index >= 0 && index < TOTAL_LEDS) {
            leds[index] = color;
        }
    }

    /**
     * Get LED array pointer (for advanced use)
     */
    CRGB* getLEDArray() {
        return leds;
    }
};

#endif // LED_CONTROLLER_H
