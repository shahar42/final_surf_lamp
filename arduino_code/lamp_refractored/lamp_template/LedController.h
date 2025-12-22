/*
 * LED CONTROLLER
 *
 * LED display functions for surf lamp.
 * Handles all LED manipulation, status patterns, and animations.
 *
 * Design principles:
 * - Non-member functions (Scott Meyers Item 23) for better encapsulation
 * - Each function has single responsibility
 * - Direction handling abstracted (users don't see FORWARD/REVERSE)
 * - Bounds checking prevents buffer overruns
 * - File-static variables hide implementation details
 *
 * Dependencies:
 * - Config.h: LED indices, strip lengths, brightness settings
 * - SurfState.h: lastSurfData for display state
 * - Themes.h: Color theme lookups
 */

#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <FastLED.h>
#include "Config.h"
#include "SurfState.h"

// ---------------- LED ARRAY ----------------
// Global LED array (managed by this module)
extern CRGB leds[TOTAL_LEDS];

// ---------------- INITIALIZATION ----------------

/**
 * Initialize FastLED library and LED strip
 * Sets up LED array, brightness, and clears display
 */
void initializeLEDs();

/**
 * Play startup animation ("The Rising Tide")
 * A professional fluid simulation where deep ocean water fills the lamp.
 */
void playStartupAnimation();

// testAllStatusLEDStates() removed to save flash memory

// ---------------- BASIC LED CONTROL ----------------

/**
 * Clear all LEDs to black
 */
void clearLEDs();

/**
 * Set status LED to solid color (no blinking)
 * @param color RGB color for status LED
 */
void setStatusLED(CRGB color);

// ---------------- STATUS PATTERNS (WiFi states) ----------------

/**
 * Blink status LED with breathing effect
 * @param color RGB color for status LED
 */
void blinkStatusLED(CRGB color);

// Status Patterns
void blinkBlueLED();    // Connecting to WiFi
void blinkGreenLED();   // Data is fresh
void blinkRedLED();     // WiFi disconnected
void blinkYellowLED();  // Config mode active
void blinkOrangeLED();  // Stale data / server issues
void showNoDataConnected(); // Connected but no data (All Green)
void showTryingToConnect();
void showCheckingLocation();
void showAPMode();          // WiFi configuration portal active

// ---------------- DATA DISPLAY FUNCTIONS ----------------

/**
 * Update wave height strip with specified number of active LEDs
 * @param numActiveLeds Number of LEDs to illuminate (0 to WAVE_HEIGHT_LENGTH)
 * @param color HSV color for active LEDs
 */
void updateWaveHeightLEDs(int numActiveLeds, CHSV color);

/**
 * Update wave period strip with specified number of active LEDs
 * @param numActiveLeds Number of LEDs to illuminate (0 to WAVE_PERIOD_LENGTH)
 * @param color HSV color for active LEDs
 */
void updateWavePeriodLEDs(int numActiveLeds, CHSV color);

/**
 * Update wind speed strip with specified number of active LEDs
 * NOTE: Skips status LED (bottom) and wind direction LED (top)
 * @param numActiveLeds Number of LEDs to illuminate (0 to WIND_SPEED_LENGTH-2)
 * @param color HSV color for active LEDs
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
 * Applies traveling wave effect with brightness modulation
 * @param numActiveLeds Number of LEDs to animate
 * @param baseColor HSV color (brightness will be modulated)
 */
void updateBlinkingWaveHeightLEDs(int numActiveLeds, CHSV baseColor);

/**
 * Update wind speed strip with blinking animation (threshold exceeded)
 * Applies traveling wave effect with brightness modulation
 * @param numActiveLeds Number of LEDs to animate
 * @param baseColor HSV color (brightness will be modulated)
 */
void updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor);

/**
 * Apply wave height threshold logic
 * Normal mode: Static theme color
 * Alert mode: Blinking animation if threshold exceeded
 * @param waveHeightLEDs Number of LEDs to display
 * @param waveHeight_cm Wave height in centimeters
 * @param waveThreshold_cm Threshold in centimeters
 */
void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm);

/**
 * Apply wind speed threshold logic
 * Normal mode: Static theme color
 * Alert mode: Blinking animation if threshold exceeded (converted to knots for comparison)
 * @param windSpeedLEDs Number of LEDs to display
 * @param windSpeed_mps Wind speed in m/s
 * @param windSpeedThreshold_knots Threshold in knots
 */
void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots);

// ---------------- HIGH-LEVEL DISPLAY UPDATES ----------------

/**
 * Update entire surf display based on global lastSurfData state
 * Handles all operating modes:
 * - OFF HOURS: Lamp completely off (highest priority)
 * - QUIET HOURS: Only top LED of each strip (secondary priority)
 * - NORMAL MODE: Full surf condition display with threshold animations
 *
 * Reads from global lastSurfData (no parameters needed)
 */
void updateSurfDisplay();

/**
 * Update blinking animations for threshold alerts
 * Called every loop iteration to maintain smooth animation
 * Only animates if thresholds are exceeded and quiet hours is inactive
 *
 * Reads from global lastSurfData (no parameters needed)
 */
void updateBlinkingAnimation();

#endif // LED_CONTROLLER_H
