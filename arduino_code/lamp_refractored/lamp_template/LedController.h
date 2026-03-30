/*
 * LED CONTROLLER
 *
 * LED display functions for surf lamp.
 * Handles all LED manipulation, status patterns, and animations.
 */

#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <FastLED.h>
#include "Config.h"
#include "SurfState.h"
#include "MutexGuard.h"

// ---------------- LED ARRAY ----------------
// Global LED array (managed by this module)
extern CRGB leds[TOTAL_LEDS];

// ---------------- INITIALIZATION ----------------

/**
 * Initialize FastLED library and LED strip
 */
void initializeLEDs();

/**
 * Play startup animation ("The Rising Tide")
 */
void playStartupAnimation();

// ---------------- BASIC LED CONTROL ----------------

/**
 * Clear all LEDs to black
 */
void clearLEDs();

/**
 * Set status LED to solid color (no blinking)
 */
void setStatusLED(CRGB color);

// ---------------- STATUS PATTERNS (WiFi states) ----------------

/**
 * Blink status LED with breathing effect
 */
void blinkStatusLED(CRGB color);

// Status Patterns
void blinkBlueLED();    // Connecting to WiFi
void blinkGreenLED();   // Data is fresh
void blinkRedLED();     // WiFi disconnected
void blinkYellowLED();  // Config mode active
void blinkOrangeLED();  // Stale data / server issues
void showNoDataConnected(); // Connected but no data (Left strip green only)
void showTryingToConnect();
void showCheckingLocation();
void showAPMode();          // WiFi configuration portal active

// Error display patterns (left strip only)
void showInvalidDataError();     // All zeros (solid RED)
void showServerUnreachableError(); // HTTP timeout (half green, half blue)
void showStaleDataError();       // Data >30min old (half red, half blue)
void showPartialDataError();     // One sensor failing (solid PURPLE)
void showJsonParseError();       // Malformed JSON (half green, half yellow)

// ---------------- DATA DISPLAY FUNCTIONS ----------------

/**
 * Update wave height strip with specified number of active LEDs
 */
void updateWaveHeightLEDs(int numActiveLeds, CHSV color);

/**
 * Update wave period strip with specified number of active LEDs
 */
void updateWavePeriodLEDs(int numActiveLeds, CHSV color);

/**
 * Update wind speed strip with specified number of active LEDs
 */
void updateWindSpeedLEDs(int numActiveLeds, CHSV color);

/**
 * Set wind direction indicator LED based on compass direction
 * @param windDirection Degrees (0-360, 0=North)
 *   - North (0-10°, 300-360°): Green
 *   - East (10-180°): Yellow
 *   - South (180-250°): Red
 *   - West (250-300°): Blue
 */
void setWindDirection(int windDirection);

// ---------------- THRESHOLD ANIMATIONS (blinking) ----------------

/**
 * Update wave height strip with blinking animation (threshold exceeded)
 */
void updateBlinkingWaveHeightLEDs(int numActiveLeds, CHSV baseColor);

/**
 * Update wind speed strip with blinking animation (threshold exceeded)
 */
void updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor);

/**
 * Apply wave height threshold logic
 */
void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm);

/**
 * Apply wind speed threshold logic
 */
void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots);

// ---------------- DISPLAY CACHE ----------------
// Core 1 snapshot of lastSurfData. Refreshed once per data update.
// Only accessed on Core 1 — no mutex needed for reads.

struct DisplayCache {
    int waveHeight_cm = 0;
    float wavePeriod = 0.0;
    int windSpeed = 0;
    int windDirection = 0;
    int waveThreshold_cm = 100;
    int windSpeedThreshold_knots = 15;
    float brightnessMultiplier = BrightnessLevel::LEVEL_MID;
    uint8_t themeIndex = 0;
    bool quietHoursActive = false;
    bool offHoursActive = false;
    bool dataReceived = false;
    bool serverUnreachableError = false;
    bool jsonParseError = false;
    bool invalidDataError = false;
    bool partialDataError = false;
    bool staleDataError = false;
    bool staleDataWarning = false;
    unsigned long lastUpdate = 0;
};

extern DisplayCache displayCache;

/**
 * Refresh the display cache from lastSurfData (one mutex lock).
 * Call this on Core 1 when needsDisplayUpdate is true, before rendering.
 */
void refreshDisplayCache();

// ---------------- HIGH-LEVEL DISPLAY UPDATES ----------------

/**
 * Update entire surf display based on cached state.
 * Call refreshDisplayCache() before this.
 */
void updateSurfDisplay();

/**
 * Update blinking animations for threshold alerts
 */
void updateBlinkingAnimation();

#endif // LED_CONTROLLER_H