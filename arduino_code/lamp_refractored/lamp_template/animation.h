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
     * Sunset Animation
     * Duration: 30 seconds (configurable)
     *
     * IMPROVED VERSION:
     * - Smooth 60 FPS timing with sine easing
     * - Proper reversed strip handling
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
            uint8_t val = 255 - (195 * easedProgress);  // 255→60

            // Apply gradient to all strips
            fillStripGradient(waveHeight, hue, sat, val);
            fillStripGradient(wavePeriod, hue, sat, val);
            fillStripGradient(windSpeed, hue, sat, val);

            FastLED.show();

            // Non-blocking frame timing
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
     * Features:
     * - Compound Easing: Cubic rise combined with a gentle sine wave for oscillation.
     * - Realistic Ocean Gradient: Deep Indigo (140) to Tropical Teal (96).
     * - Flickering Crest: Random brightness pulses on the foam.
     */
    // Easing function: Cubic ease-in for 'slow start, fast end'
    inline float easeInCubic(float t) {
        return t * t * t;
    }

    // Easing function: Cubic ease-out for 'fast start, slow end'
    inline float easeOutCubic(float t) {
        float t_minus_1 = t - 1.0;
        return t_minus_1 * t_minus_1 * t_minus_1 + 1.0;
    }

    /**
     * Startup Animation: "The Living Tide" with Sunset Crest
     * A 23s sequence with an overlapping, accelerating sunset on the crest.
     */
    inline void playStartupTide(CRGB* leds, StripConfig waveHeight, StripConfig wavePeriod, StripConfig windSpeed, int sunriseOverlapSeconds = 4) {
        Serial.println("🌊 Starting 'The Living Tide' v5 (Sunset Crest) animation...");
        FastLED.clear();

        const int FPS = 60;
        const int frameInterval = 1000 / FPS;

        const int tideDuration = 22;
        const int sunsetDuration = 5;
        const int totalDuration = tideDuration + sunsetDuration - sunriseOverlapSeconds;
        const int totalFrames = totalDuration * FPS;
        const int sunsetStartFrame = (tideDuration - sunriseOverlapSeconds) * FPS;

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

        for (int frame = 0; frame < totalFrames; frame++) {
            unsigned long frameStart = millis();

            if (frame <= tideDuration * FPS) {
                float t_tide = (float)frame / (tideDuration * FPS);
                float finalLevel = calculateLevelForTime(t_tide);
                const uint8_t centerBrightness = 230;
                const uint8_t sideBrightness = 178;

                drawTideOnStrip(windSpeed, finalLevel, centerBrightness);
                drawTideOnStrip(waveHeight, finalLevel, sideBrightness);
                drawTideOnStrip(wavePeriod, finalLevel, sideBrightness);
            }

            if (frame >= sunsetStartFrame) {
                float t_sunset = (float)(frame - sunsetStartFrame) / (sunsetDuration * FPS);
                float eased_t_sunset = easeOutCubic(t_sunset); // Ease-Out for sunset

                uint8_t sunHue = lerp8by8(60, 0, eased_t_sunset * 255); // Yellow -> Red
                uint8_t sunBrightness = lerp8by8(255, 80, eased_t_sunset * 255); // Bright -> Dim
                CHSV sunColor = CHSV(sunHue, 255, sunBrightness);

                int whTopIndex = waveHeight.forward ? waveHeight.end : waveHeight.start;
                int wpTopIndex = wavePeriod.forward ? wavePeriod.end : wavePeriod.start;
                int wsTopIndex = windSpeed.forward ? windSpeed.end : windSpeed.start;

                leds[whTopIndex] = sunColor;
                leds[wpTopIndex] = sunColor;
                leds[wsTopIndex] = sunColor;
            }

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
