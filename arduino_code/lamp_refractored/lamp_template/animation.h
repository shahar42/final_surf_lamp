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

    // Easing function: Cubic ease-in-out for smooth acceleration/deceleration
    inline float easeInOutCubic(float t) {
        if (t < 0.5) {
            return 4.0 * t * t * t;  // Ease in: slow start
        } else {
            float f = (2.0 * t - 2.0);
            return 0.5 * f * f * f + 1.0;  // Ease out: slow end
        }
    }

    // Easing function: Sine ease-in-out for ultra-smooth transitions
    inline float easeInOutSine(float t) {
        return -(cos(PI * t) - 1.0) / 2.0;
    }

    /**
     * Sunset Animation: Beautiful warm sunset gradient across three LED strips
     * Colors: Orange → Red → Pink → Purple
     * Duration: 30 seconds (configurable)
     *
     * IMPROVED VERSION:
     * - Smooth 60 FPS timing with sine easing
     * - Proper reversed strip handling (gradient flows bottom→top visually on ALL strips)
     * - Natural sunset progression (warm to cool colors)
     * - HSV color space for smooth blending
     * - Starts at pure orange (hue 16), no yellow/green tones
     */
    inline void playSunset(CRGB* leds, StripConfig waveHeight, StripConfig wavePeriod, StripConfig windSpeed, int durationSeconds = 30) {
        Serial.println("🌅 Starting sunset animation...");
        Serial.printf("   Wave Height: %d LEDs | Wave Period: %d LEDs | Wind Speed: %d LEDs\n",
                      waveHeight.length, wavePeriod.length, windSpeed.length);

        const int FPS = 60;                           // Smooth 60 FPS (Perplexity recommendation)
        const int frameInterval = 1000 / FPS;         // 16.67ms per frame
        const int totalFrames = durationSeconds * FPS; // Total frames in animation

        unsigned long animationStart = millis();
        int currentFrame = 0;

        // Lambda to fill a strip with gradient - FIXED for reversed strips
        auto fillStripGradient = [&](const StripConfig& strip, uint8_t baseHue, uint8_t sat, uint8_t val) {
            for (int i = 0; i < strip.length; i++) {
                // CRITICAL FIX: Map i=0 to BOTTOM visually for both forward and reverse strips
                // Forward: start=bottom, count up → start + i
                // Reverse: start=bottom (HIGH index), count down → start - i
                int ledIndex = strip.forward ? (strip.start + i) : (strip.start - i);

                // Gradient position within strip (0.0 at bottom → 1.0 at top)
                float stripProgress = (float)i / (strip.length - 1);  // -1 for proper 0→1 range

                // All LEDs same hue - no gradient shift (prevents color bleeding)
                leds[ledIndex] = CHSV(baseHue, sat, val);
            }
        };

        // Main animation loop - 60 FPS timing
        while (currentFrame < totalFrames) {
            unsigned long frameStart = millis();
            float progress = (float)currentFrame / totalFrames;  // 0.0 → 1.0

            // Apply easing for smooth acceleration/deceleration
            float easedProgress = easeInOutSine(progress);

            // ORANGE TO RED ONLY - 30 second gradient
            // Hue: 16 (pure orange) → 0 (pure red)
            // Brightness: Adds depth layer (bright→dim)
            uint8_t hue = 16 - (uint8_t)(16.0 * easedProgress);  // 16→0

            // Debug: Print hue every 2 seconds
            if (currentFrame % 120 == 0) {
                Serial.printf("   Frame %d: hue=%d (", currentFrame, hue);
                if (hue >= 0 && hue <= 16) Serial.print("ORANGE/RED ✅");
                else Serial.print("ERROR ❌");
                Serial.println(")");
            }

            // Saturation: Keep high for vibrant colors
            uint8_t sat = 255 - (30 * easedProgress);  // 255→225 (stay saturated)

            // Brightness: Depth layer - bright orange→dark red
            // Starts bright (255), ends dim (60) for dramatic sunset feel
            uint8_t val = 255 - (195 * easedProgress);  // 255→60

            // Apply gradient to all strips
            fillStripGradient(waveHeight, hue, sat, val);
            fillStripGradient(wavePeriod, hue, sat, val);
            fillStripGradient(windSpeed, hue, sat, val);

            FastLED.show();

            // Non-blocking frame timing (Perplexity recommendation)
            currentFrame++;
            unsigned long frameTime = millis() - frameStart;
            if (frameTime < frameInterval) {
                delay(frameInterval - frameTime);  // Only delay remainder to hit target FPS
            }
            yield();  // Prevent watchdog timeout
        }

        // Smooth fade to black with easing
        const int fadeFrames = 60;  // 1 second fade
        for (int frame = 0; frame < fadeFrames; frame++) {
            float fadeProgress = (float)frame / fadeFrames;
            float easedFade = easeInOutSine(fadeProgress);
            uint8_t brightness = 60 * (1.0 - easedFade);  // Smooth fade from 60 to 0

            fillStripGradient(waveHeight, 0, 225, brightness);  // Deep red fade
            fillStripGradient(wavePeriod, 0, 225, brightness);
            fillStripGradient(windSpeed, 0, 225, brightness);

            FastLED.show();
            delay(frameInterval);
            yield();
        }

        FastLED.clear();
        FastLED.show();

        unsigned long totalTime = millis() - animationStart;
        Serial.printf("✅ Sunset animation complete (actual time: %lums)\n", totalTime);
    }

    /**
     * Startup Animation: "The Living Tide"
     * An advanced fluid simulation with realistic physics and texture.
     * Features:
     * - Compound Easing: Cubic rise combined with a gentle sine wave for oscillation.
     * - Dynamic Texture: Perlin noise turbulence changes from calm to active.
     * - Realistic Ocean Gradient: Deep Indigo (140) to Tropical Teal (96).
     * - Flickering Crest: Random brightness pulses on the foam.
     */
    inline void playStartupTide(CRGB* leds, StripConfig waveHeight, StripConfig wavePeriod, StripConfig windSpeed) {
        Serial.println("🌊 Starting 'The Living Tide' animation...");
        FastLED.clear();

        const int FPS = 60;
        const int frameInterval = 1000 / FPS;

        // --- Part 1: Tide Rise (20 seconds) ---
        const int tideDuration = 20; 
        const int tideFrames = tideDuration * FPS;

        auto calculateLevelForTime = [](float t) {
            float riseLevel = easeInOutCubic(t);
            float breath = sinf(t * PI * 4.0) * 0.03 * (1.0 - t);
            return constrain(riseLevel + breath, 0.0, 1.0);
        };

        auto drawTideOnStrip = [&](const StripConfig& strip, float waterLevel, uint8_t brightnessScale) {
            uint32_t ms = millis();
            float turbulence = easeInOutCubic(waterLevel);
            uint16_t noiseScale = lerp16by16(30, 80, turbulence * 65535);
            uint32_t noiseTime = ms / lerp8by8(10, 2, turbulence * 255);
            
            int tideLength = strip.length - 1;
            int crestIndex = (int)(waterLevel * tideLength);

            for (int i = 0; i < tideLength; i++) {
                int ledIndex = strip.forward ? (strip.start + i) : (strip.end - i);

                if (i <= crestIndex) {
                    uint8_t hue = map(i, 0, tideLength, 140, 96);
                    int tempBrightness = 180 + (inoise8(i * noiseScale, noiseTime) / 3);
                    uint8_t baseBrightness = min(tempBrightness, 255);

                    if (i >= crestIndex - 2 && crestIndex > 0) {
                        uint8_t flicker = random8(200, 255);
                        leds[ledIndex] = CHSV(110, 80, scale8(flicker, brightnessScale));
                    } else {
                        leds[ledIndex] = CHSV(hue, 255, scale8(baseBrightness, brightnessScale));
                    }
                } else {
                    leds[ledIndex] = CRGB::Black;
                }
            }
        };

        for (int frame = 0; frame < tideFrames; frame++) {
            unsigned long frameStart = millis();
            float t = (float)frame / tideFrames;

            // Explicitly keep top LEDs off during tide rise
            leds[waveHeight.forward ? waveHeight.end : waveHeight.start] = CRGB::Black;
            leds[wavePeriod.forward ? wavePeriod.end : wavePeriod.start] = CRGB::Black;
            leds[windSpeed.forward ? windSpeed.end : windSpeed.start] = CRGB::Black;

            float finalLevel = calculateLevelForTime(t);
            const uint8_t centerBrightness = 230;
            const uint8_t sideBrightness = 178;

            drawTideOnStrip(windSpeed, finalLevel, centerBrightness);
            drawTideOnStrip(waveHeight, finalLevel, sideBrightness);
            drawTideOnStrip(wavePeriod, finalLevel, sideBrightness);

            FastLED.show();

            unsigned long frameTime = millis() - frameStart;
            if (frameTime < frameInterval) delay(frameInterval - frameTime);
        }
        
        Serial.println("🌊 Tide rise complete. Starting sunrise on crest...");

        // --- Part 2: Sunrise on Crest (5 seconds) ---
        const int sunriseDuration = 5;
        const int sunriseFrames = sunriseDuration * FPS;

        for (int frame = 0; frame < sunriseFrames; frame++) {
            unsigned long frameStart = millis();
            float t = (float)frame / sunriseFrames;

            uint8_t sunHue = lerp8by8(0, 60, t * 255); // Red -> Yellow
            uint8_t sunBrightness = lerp8by8(80, 255, easeInOutCubic(t) * 255); // Dim -> Bright, with easing
            CHSV sunColor = CHSV(sunHue, 255, sunBrightness);

            int whTopIndex = waveHeight.forward ? waveHeight.end : waveHeight.start;
            int wpTopIndex = wavePeriod.forward ? wavePeriod.end : wavePeriod.start;
            int wsTopIndex = windSpeed.forward ? windSpeed.end : windSpeed.start;

            leds[whTopIndex] = sunColor;
            leds[wpTopIndex] = sunColor;
            leds[wsTopIndex] = sunColor;

            FastLED.show();

            unsigned long frameTime = millis() - frameStart;
            if (frameTime < frameInterval) delay(frameInterval - frameTime);
        }

        Serial.println("✅ Full startup animation complete.");
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
