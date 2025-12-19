#ifndef ANIMATION_H
#define ANIMATION_H

#include <FastLED.h>

namespace Animation {
    // Strip configuration for dynamic animation
    struct StripConfig {
        int start;       // Start index
        int end;         // End index
        bool forward;    // Direction: true = forward (start→end), false = reverse (end→start)
        int length;      // Number of LEDs in strip
    };

    /**
     * Sunset Animation: Warm gradient transition across three LED strips
     * Colors: Orange → Pink → Purple → Deep Blue
     * Duration: 30 seconds (configurable)
     *
     * Dynamically adapts to any strip configuration - each strip gets full gradient
     *
     * Usage: Call once when backend signals sunset time
     */
    void playSunset(CRGB* leds, StripConfig waveHeight, StripConfig wavePeriod, StripConfig windSpeed, int durationSeconds = 30) {
        Serial.println("🌅 Starting sunset animation...");
        Serial.printf("   Wave Height: %d LEDs | Wave Period: %d LEDs | Wind Speed: %d LEDs\n",
                      waveHeight.length, wavePeriod.length, windSpeed.length);

        const int totalSteps = durationSeconds * 20;  // 20 updates per second (50ms each)
        const int stepDelay = 50;  // milliseconds

        // Lambda to fill a strip with gradient based on position
        auto fillStripGradient = [&](const StripConfig& strip, uint8_t baseHue, uint8_t sat, uint8_t val) {
            for (int i = 0; i < strip.length; i++) {
                // Calculate physical LED index based on direction
                // Forward: start at low index, count up (start + i)
                // Reverse: start at high index, count down (end - i)
                int ledIndex = strip.forward ? (strip.start + i) : (strip.end - i);

                // Gradient position within strip (0.0 at bottom → 1.0 at top)
                float stripProgress = (float)i / strip.length;

                // Slight hue shift along strip height for depth effect
                uint8_t hue = baseHue + (stripProgress * 20);  // ±10 hue shift

                leds[ledIndex] = CHSV(hue, sat, val);
            }
        };

        // Animation loop
        for (int step = 0; step < totalSteps; step++) {
            float progress = (float)step / totalSteps;  // 0.0 → 1.0

            // Sunset color palette (HSV for smooth transitions)
            // Orange (25) → Pink (340) → Purple (280) → Deep Blue (240)
            uint8_t hue;
            if (progress < 0.33) {
                // Orange to Pink
                hue = 25 + (340 - 25) * (progress / 0.33);
            } else if (progress < 0.66) {
                // Pink to Purple
                hue = 340 + (280 - 340) * ((progress - 0.33) / 0.33);
            } else {
                // Purple to Deep Blue
                hue = 280 + (240 - 280) * ((progress - 0.66) / 0.34);
            }

            // Saturation: High at start, medium at end (255 → 200)
            uint8_t sat = 255 - (55 * progress);

            // Brightness: Full at start, dim at end (200 → 80)
            uint8_t val = 200 - (120 * progress);

            // Apply gradient to each strip independently
            fillStripGradient(waveHeight, hue, sat, val);
            fillStripGradient(wavePeriod, hue, sat, val);
            fillStripGradient(windSpeed, hue, sat, val);

            FastLED.show();
            delay(stepDelay);
            yield();  // Prevent watchdog timeout
        }

        // Fade to black at end
        for (int brightness = 80; brightness >= 0; brightness -= 2) {
            fillStripGradient(waveHeight, 240, 200, brightness);
            fillStripGradient(wavePeriod, 240, 200, brightness);
            fillStripGradient(windSpeed, 240, 200, brightness);
            FastLED.show();
            delay(20);
        }

        FastLED.clear();
        FastLED.show();

        Serial.println("✅ Sunset animation complete");
    }

    /**
     * Check if sunset animation should trigger
     * Prevents replaying animation multiple times in same sunset window
     */
    class SunsetTracker {
    private:
        bool playedToday = false;
        int lastTriggerDay = -1;  // Day of year when last triggered

    public:
        bool shouldPlay(bool sunsetTriggerFromBackend, int currentDayOfYear) {
            // Backend not signaling sunset → don't play
            if (!sunsetTriggerFromBackend) {
                return false;
            }

            // New day → reset played flag
            if (currentDayOfYear != lastTriggerDay) {
                playedToday = false;
                lastTriggerDay = currentDayOfYear;
            }

            // Already played today → don't replay
            if (playedToday) {
                return false;
            }

            // Trigger animation and mark as played
            playedToday = true;
            return true;
        }

        void reset() {
            playedToday = false;
            lastTriggerDay = -1;
        }
    };
}

#endif
