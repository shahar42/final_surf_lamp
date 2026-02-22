#include "LedController.h"
#include "FastSin.h"
#include <vector>

/**
 * REFERENCE IMPLEMENTATION: Gerstner Wave Engine
 * 
 * This file demonstrates how to map the 2D Gerstner formulas:
 *   x = a + R * sin(m*a + w*t)
 *   y = R * cos(m*a + w*t)
 * onto a 1D LED strip.
 */

struct GerstnerWave {
    float amplitude;    // R
    float wavenumber;   // m = 2*PI / wavelength
    float omega;        // w = sqrt(g * m)
    float phase;        // current accumulation of w*t
};

// State: 3 waves for organic interference
static GerstnerWave waves[3] = {
    {0.8f, 0.5f, 1.2f, 0.0f}, // Swell
    {0.4f, 1.2f, 2.5f, 0.0f}, // Secondary
    {0.15f, 3.5f, 5.0f, 0.0f} // Wind Chop
};

void updateGerstnerWaves() {
    unsigned long now = millis();
    static unsigned long lastUpdate = 0;
    float dt = (now - lastUpdate) / 1000.0f;
    lastUpdate = now;

    // 1. Update Phase (w * t)
    for (int i = 0; i < 3; i++) {
        waves[i].phase += waves[i].omega * dt;
    }

    // 2. Clear Buffer
    FastLED.clear();

    // 3. Render Each Strip
    // We treat the LED index as the "base position" (a)
    for (int a = 0; a < WAVE_HEIGHT_LENGTH; a++) {
        float x_displacement = 0;
        float y_displacement = 0;

        for (int i = 0; i < 3; i++) {
            float theta = (waves[i].wavenumber * a) + waves[i].phase;
            
            // Gerstner Formulas
            x_displacement += waves[i].amplitude * FastMath::fastSin(theta);
            y_displacement += waves[i].amplitude * cos(theta); // Using cos for Trochoid shape
        }

        /**
         * MAPPING TO 1D:
         * In a 1D strip, 'y' represents the brightness (height).
         * The 'x' displacement causes particles to "bunch up" at the peaks.
         * To simulate this, we calculate the brightness based on 'y',
         * but we slightly shift the index we are writing to based on 'x'.
         */
        
        // Final vertical height maps to brightness (0-1.0)
        // We normalize the sum of amplitudes so it doesn't clip
        float total_amp = waves[0].amplitude + waves[1].amplitude + waves[2].amplitude;
        float height_normalized = (y_displacement + total_amp) / (2.0f * total_amp);

        // Optional: The "Sharpness" factor
        // Squaring the height creates even more dramatic crests
        float intensity = pow(height_normalized, 3.0f);

        // Apply to the LED
        int ledIndex = WAVE_HEIGHT_START + a;
        if (ledIndex < TOTAL_LEDS) {
            CHSV themeColor = getWaveHeightColor(displayCache.themeIndex);
            leds[ledIndex] = CHSV(themeColor.hue, themeColor.sat, (uint8_t)(intensity * 255));
        }
    }

    FastLED.show();
}

/**
 * DESIGN NOTE:
 * To truly capture the Gerstner "Bunching" (x-displacement) on 1D:
 * Instead of calculating displacement for each LED, you should calculate 
 * where each "particle" lands:
 * 
 * float final_x = a + x_displacement;
 * int target_led = round(final_x);
 * leds[target_led] += brightness;
 * 
 * This creates high-density light at the crests and low-density in the troughs!
 */
