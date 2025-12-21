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
    float easeInOutCubic(float t) {
        if (t < 0.5) {
            return 4.0 * t * t * t;  // Ease in: slow start
        } else {
            float f = (2.0 * t - 2.0);
            return 0.5 * f * f * f + 1.0;  // Ease out: slow end
        }
    }

    // Easing function: Sine ease-in-out for ultra-smooth transitions
    float easeInOutSine(float t) {
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
    void playSunset(CRGB* leds, StripConfig waveHeight, StripConfig wavePeriod, StripConfig windSpeed, int durationSeconds = 30) {
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
     * Startup Animation: "The Rising Tide"
     * A professional fluid simulation where deep ocean water fills the lamp.
     * Features:
     * - Cubic Easing: Slow start, energetic surge, slow cresting.
     * - Water Texture: Perlin noise (inoise8) for organic shimmering.
     * - Deep Ocean Gradient: Indigo (bottom) to Aqua (surface).
     * - Foam Crest: Bright white/cyan edge at the rising waterline.
     */
    void playStartupTide(CRGB* leds, StripConfig waveHeight, StripConfig wavePeriod, StripConfig windSpeed) {
        Serial.println("🌊 Starting 'The Rising Tide' animation...");
        FastLED.clear();

        const int FPS = 60;
        const int durationSeconds = 3; 
        const int totalFrames = durationSeconds * FPS;
        const int frameInterval = 1000 / FPS;

        // Animation Loop
        for (int frame = 0; frame < totalFrames; frame++) {
            unsigned long frameStart = millis();
            float t = (float)frame / totalFrames; // 0.0 to 1.0

            // 1. Fluid Physics: Cubic In-Out Easing
            // Simulates viscous fluid: heavy start, surge, then slowing surface tension
            float ease = (t < 0.5) ? 4.0 * t * t * t : 1.0 - pow(-2.0 * t + 2.0, 3.0) / 2.0;
            
            // 2. Water Texture Parameters
            // Slow rolling noise to make water feel "liquid"
            uint16_t noiseScale = 20;
            uint32_t noiseTime = millis() / 3;

            auto drawTideOnStrip = [&](const StripConfig& strip) {
                // Current water level for this strip (0.0 to length)
                float waterLevel = ease * strip.length;
                int crestIndex = (int)waterLevel;

                for (int i = 0; i < strip.length; i++) {
                    // Physical LED index logic
                    // Forward: Start=0, End=15 -> i=0 is Bottom (Start+0)
                    // Reverse: Start=21, End=38 -> i=0 is Bottom (End-0)
                    int ledIndex = strip.forward ? (strip.start + i) : (strip.end - i);

                    if (i <= crestIndex) {
                        // A. Deep Ocean Gradient
                        // Map position 0->1 to Hue 160 (Deep Blue) -> 130 (Aqua)
                        // 'i' is the vertical height from bottom
                        uint8_t hue = map(i, 0, strip.length, 160, 130);
                        
                        // B. Water Texture (Perlin Noise)
                        // Adds 10-20% brightness variance for "shimmer"
                        uint8_t noise = inoise8(i * noiseScale, noiseTime);
                        uint8_t brightness = scale8(255, 200 + (noise / 5)); // 200-255 range

                        // C. Foam Crest
                        // The top 2-3 LEDs get whiter and brighter
                        if (i >= crestIndex - 2) {
                            // Foam is white/cyan
                            leds[ledIndex] = CHSV(120, 100 - (i - (crestIndex - 2)) * 40, 255);
                        } else {
                            // Deep water body
                            leds[ledIndex] = CHSV(hue, 255, brightness);
                        }
                    } else {
                        // Above water
                        leds[ledIndex] = CRGB::Black;
                    }
                }
            };

            // Render all 3 strips
            drawTideOnStrip(waveHeight);
            drawTideOnStrip(wavePeriod);
            drawTideOnStrip(windSpeed);

            FastLED.show();

            // Frame timing
            unsigned long frameTime = millis() - frameStart;
            if (frameTime < frameInterval) delay(frameInterval - frameTime);
        }
        
        Serial.println("✅ Tide animation complete");
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
