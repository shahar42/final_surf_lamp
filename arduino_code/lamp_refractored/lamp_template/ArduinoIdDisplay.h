/*
 * ARDUINO ID DISPLAY MODULE
 *
 * Displays the Arduino ID in binary on startup for hardware identification.
 * Uses the first 10 LEDs from the bottom of the middle (wind speed) strip.
 *
 * Binary encoding:
 * - White LED = 0
 * - Blue LED = 1
 *
 * 10 bits can represent 0-1023, sufficient for 1000+ lamp IDs.
 */

#ifndef ARDUINO_ID_DISPLAY_H
#define ARDUINO_ID_DISPLAY_H

#include <FastLED.h>
#include "Config.h"

namespace ArduinoId {

    /**
     * Display Arduino ID in binary format for 5 seconds
     *
     * Uses the first 10 LEDs from the bottom of the wind speed strip.
     * LSB (Least Significant Bit) is displayed at the bottom LED.
     *
     * @param leds Pointer to the global LED array
     */
    inline void displayId(CRGB* leds) {
        const int DISPLAY_DURATION_MS = 5000;
        const int NUM_BINARY_LEDS = 10;

        // Colors for binary display
        const CRGB COLOR_ZERO = CRGB::White;  // 0 = White
        const CRGB COLOR_ONE = CRGB::Blue;    // 1 = Blue

        Serial.println("🔢 Displaying Arduino ID in binary...");
        Serial.printf("   Arduino ID: %d (decimal)\n", ARDUINO_ID);

        // Convert Arduino ID to binary and print for debugging
        Serial.print("   Binary: ");
        for (int bit = NUM_BINARY_LEDS - 1; bit >= 0; bit--) {
            Serial.print((ARDUINO_ID >> bit) & 1);
        }
        Serial.println();

        // Validate we have enough LEDs in wind strip
        if (WIND_SPEED_LENGTH < NUM_BINARY_LEDS) {
            Serial.printf("⚠️ Warning: Wind strip only has %d LEDs, need %d for ID display\n",
                          WIND_SPEED_LENGTH, NUM_BINARY_LEDS);
            return;
        }

        // Clear all LEDs first
        FastLED.clear();

        // Calculate the first 10 LED indices from bottom of wind strip
        // WIND_SPEED_BOTTOM is always the starting point (bottom LED)
        for (int i = 0; i < NUM_BINARY_LEDS; i++) {
            int bit = (ARDUINO_ID >> i) & 1;  // Extract bit i (LSB first)

            // Calculate physical LED index
            // If FORWARD (bottom < top): indices go up from bottom
            // If REVERSE (bottom > top): indices go down from bottom
            int ledIndex;
            if (WIND_SPEED_FORWARD) {
                ledIndex = WIND_SPEED_BOTTOM + i;
            } else {
                ledIndex = WIND_SPEED_BOTTOM - i;
            }

            // Set LED color based on bit value
            leds[ledIndex] = (bit == 1) ? COLOR_ONE : COLOR_ZERO;

            // Debug output
            Serial.printf("   Bit %d = %d → LED[%d] = %s\n",
                          i, bit, ledIndex, (bit == 1) ? "Blue" : "White");
        }

        FastLED.show();
        Serial.printf("✅ Arduino ID displayed for %d seconds\n", DISPLAY_DURATION_MS / 1000);

        // Hold display for 5 seconds
        delay(DISPLAY_DURATION_MS);

        // Clear display after showing
        FastLED.clear();
        FastLED.show();

        Serial.println("🔢 Arduino ID display complete");
    }

} // namespace ArduinoId

#endif // ARDUINO_ID_DISPLAY_H
