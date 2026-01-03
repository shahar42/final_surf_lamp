/*
 * SURF LAMP CONFIGURATION FILE
 *
 * This is the ONLY file you need to edit to create a new lamp.
 * All other files are reusable across different lamp configurations.
 *
 * Based on Scott Meyers' "Easy to use correctly, hard to use incorrectly" principle.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ============================================================================================
// ADMIN CONFIGURATION SECTION - EDIT THESE VALUES FOR YOUR LAMP
// ============================================================================================

// ---------------- DEVICE IDENTITY ----------------
const int ARDUINO_ID = 8;  // Unique lamp ID from database (must match backend)

// ---------------- HARDWARE SETUP ----------------
#define LED_PIN 2              // GPIO pin connected to LED strip data line
// NOTE: TOTAL_LEDS should be set to the highest LED index used in your strips + 1.
// In most cases this is WAVE_PERIOD_TOP + 1, but check all three strip TOP values to be sure.
#define TOTAL_LEDS 88          // Total number of LEDs in the physical strip
#define LED_TYPE WS2812B       // LED chipset type (WS2812B, SK6812, APA102, etc.)
#define COLOR_ORDER GRB        // Color order for your LED strip (GRB, RGB, BRG, etc.)
#define BRIGHTNESS 75          // Global brightness (0-255, recommend 50-100 for indoor use)

// ---------------- LED STRIP MAPPING ----------------
// Define the physical LED indices for each strip (bottom = where strip starts, top = where it ends)
// Direction is auto-detected: if bottom < top = FORWARD, if bottom > top = REVERSE

// Wave Height Strip (Right Side in typical lamp orientation)
#define WAVE_HEIGHT_BOTTOM 5   // First LED index of wave height strip
#define WAVE_HEIGHT_TOP 27     // Last LED index of wave height strip

// Wave Period Strip (Left Side in typical lamp orientation)
#define WAVE_PERIOD_BOTTOM 64  // First LED index of wave period strip
#define WAVE_PERIOD_TOP 87     // Last LED index of wave period strip

// Wind Speed Strip (Center)
// CRITICAL: Wind strip is ALWAYS REVERSED (BOTTOM > TOP) in hardware design
// NOTE: Bottom LED serves as status indicator, Top LED shows wind direction
#define WIND_SPEED_BOTTOM 59   // First LED index (also used for status LED)
#define WIND_SPEED_TOP 34      // Last LED index (also used for wind direction LED)

// ---------------- SURF DATA SCALING ----------------
// These values determine the maximum range displayed on each strip

#define MAX_WAVE_HEIGHT_METERS 3.0   // Maximum wave height to display (meters)
#define MAX_WIND_SPEED_MPS 18.0      // Maximum wind speed to display (m/s) - equivalent to ~35 knots
// Note: Wave period uses 1:1 mapping (1 LED = 1 second), no scaling needed

// ---------------- WAVE ANIMATION PARAMETERS ----------------
// Controls the blinking/wave effect when thresholds are exceeded

#define WAVE_BRIGHTNESS_MIN_PERCENT 45   // Minimum brightness during wave animation (0-100%)
#define WAVE_BRIGHTNESS_MAX_PERCENT 100  // Maximum brightness during wave animation (0-100%)
#define WAVE_LENGTH_MULTIPLIER 0.7       // Wave length as % of strip length (0.7 = 70% of strip)
#define WAVE_SPEED_MULTIPLIER 1.2        // Animation speed multiplier (higher = faster, recommend 0.8-1.5)
#define SUNRISE_OVERLAP_SECONDS 5        // How many seconds before the tide finishes that the sunrise crest begins

// ---------------- SYSTEM CONSTANTS ----------------
// These rarely need changing, but can be adjusted if needed

#define BUTTON_PIN 0                     // ESP32 boot button for WiFi reset
#define WIFI_TIMEOUT 30                  // WiFi connection timeout (seconds)
#define MAX_BRIGHTNESS 255               // Maximum LED brightness value
#define HTTP_TIMEOUT_MS 15000            // HTTP request timeout (milliseconds)
#define JSON_CAPACITY 1024               // JSON document capacity for parsing

// ============================================================================================
// END OF ADMIN CONFIGURATION
// DO NOT MODIFY BELOW THIS LINE - Auto-calculated values and compile-time validation
// ============================================================================================

// ---------------- AUTO-CALCULATED VALUES ----------------
// These are derived from the admin configuration above

// Strip directions (auto-detected at compile time)
#define WAVE_HEIGHT_FORWARD (WAVE_HEIGHT_BOTTOM < WAVE_HEIGHT_TOP)
#define WAVE_PERIOD_FORWARD (WAVE_PERIOD_BOTTOM < WAVE_PERIOD_TOP)
#define WIND_SPEED_FORWARD (WIND_SPEED_BOTTOM < WIND_SPEED_TOP)

// Strip start/end indices (normalized to match code expectations)
#define WAVE_HEIGHT_START (WAVE_HEIGHT_FORWARD ? WAVE_HEIGHT_BOTTOM : WAVE_HEIGHT_TOP)
#define WAVE_HEIGHT_END (WAVE_HEIGHT_FORWARD ? WAVE_HEIGHT_TOP : WAVE_HEIGHT_BOTTOM)
#define WAVE_PERIOD_START (WAVE_PERIOD_FORWARD ? WAVE_PERIOD_BOTTOM : WAVE_PERIOD_TOP)
#define WAVE_PERIOD_END (WAVE_PERIOD_FORWARD ? WAVE_PERIOD_TOP : WAVE_PERIOD_BOTTOM)
#define WIND_SPEED_START (WIND_SPEED_FORWARD ? WIND_SPEED_BOTTOM : WIND_SPEED_TOP)
#define WIND_SPEED_END (WIND_SPEED_FORWARD ? WIND_SPEED_TOP : WIND_SPEED_BOTTOM)

// Strip lengths (auto-calculated from bottom/top indices)
#define WAVE_HEIGHT_LENGTH (abs(WAVE_HEIGHT_TOP - WAVE_HEIGHT_BOTTOM) + 1)
#define WAVE_PERIOD_LENGTH (abs(WAVE_PERIOD_TOP - WAVE_PERIOD_BOTTOM) + 1)
#define WIND_SPEED_LENGTH (abs(WIND_SPEED_TOP - WIND_SPEED_BOTTOM) + 1)

// Special function LEDs (wind strip bottom = status, wind strip top = direction)
#define STATUS_LED_INDEX WIND_SPEED_BOTTOM
#define WIND_DIRECTION_INDEX WIND_SPEED_TOP

// Legacy compatibility names (for backward compatibility with older code)
#define NUM_LEDS_RIGHT WAVE_HEIGHT_LENGTH
#define NUM_LEDS_LEFT WAVE_PERIOD_LENGTH
#define NUM_LEDS_CENTER WIND_SPEED_LENGTH

// ---------------- COMPILE-TIME VALIDATION ----------------
// These checks prevent common configuration errors at compile time

// Basic sanity checks
static_assert(TOTAL_LEDS > 0, "TOTAL_LEDS must be positive");
static_assert(TOTAL_LEDS <= 300, "TOTAL_LEDS exceeds reasonable limit (300). Check your configuration.");
static_assert(BRIGHTNESS >= 0 && BRIGHTNESS <= 255, "BRIGHTNESS must be 0-255");

// Strip length validation
static_assert(WAVE_HEIGHT_LENGTH > 0, "Wave height strip is empty (BOTTOM and TOP are same index)");
static_assert(WAVE_PERIOD_LENGTH > 0, "Wave period strip is empty (BOTTOM and TOP are same index)");
static_assert(WIND_SPEED_LENGTH >= 3, "Wind speed strip needs minimum 3 LEDs (status + direction + 1 data LED)");

// Hardware design constraint: Wind strip MUST be reversed
static_assert(WIND_SPEED_BOTTOM > WIND_SPEED_TOP, "CRITICAL: Wind strip MUST be reversed (BOTTOM > TOP) - this is a hardware requirement!");

// LED index bounds checking
static_assert(WAVE_HEIGHT_BOTTOM < TOTAL_LEDS, "WAVE_HEIGHT_BOTTOM out of range");
static_assert(WAVE_HEIGHT_TOP < TOTAL_LEDS, "WAVE_HEIGHT_TOP out of range");
static_assert(WAVE_PERIOD_BOTTOM < TOTAL_LEDS, "WAVE_PERIOD_BOTTOM out of range");
static_assert(WAVE_PERIOD_TOP < TOTAL_LEDS, "WAVE_PERIOD_TOP out of range");
static_assert(WIND_SPEED_BOTTOM < TOTAL_LEDS, "WIND_SPEED_BOTTOM out of range");
static_assert(WIND_SPEED_TOP < TOTAL_LEDS, "WIND_SPEED_TOP out of range");
static_assert(STATUS_LED_INDEX < TOTAL_LEDS, "Status LED index out of range");
static_assert(WIND_DIRECTION_INDEX < TOTAL_LEDS, "Wind direction LED index out of range");

// Scaling parameter validation
static_assert(MAX_WAVE_HEIGHT_METERS > 0, "MAX_WAVE_HEIGHT_METERS must be positive");
static_assert(MAX_WIND_SPEED_MPS > 0, "MAX_WIND_SPEED_MPS must be positive");

// Animation parameter validation
static_assert(WAVE_BRIGHTNESS_MIN_PERCENT >= 0 && WAVE_BRIGHTNESS_MIN_PERCENT <= 100,
              "WAVE_BRIGHTNESS_MIN_PERCENT must be 0-100");
static_assert(WAVE_BRIGHTNESS_MAX_PERCENT >= 0 && WAVE_BRIGHTNESS_MAX_PERCENT <= 100,
              "WAVE_BRIGHTNESS_MAX_PERCENT must be 0-100");
static_assert(WAVE_BRIGHTNESS_MIN_PERCENT <= WAVE_BRIGHTNESS_MAX_PERCENT,
              "WAVE_BRIGHTNESS_MIN_PERCENT must be <= WAVE_BRIGHTNESS_MAX_PERCENT");

// ---------------- WAVE ANIMATION CONFIGURATION STRUCT ----------------

struct WaveConfig {
    // Parameters loaded from admin configuration
    uint8_t brightness_min_percent = WAVE_BRIGHTNESS_MIN_PERCENT;
    uint8_t brightness_max_percent = WAVE_BRIGHTNESS_MAX_PERCENT;
    float wave_speed = WAVE_SPEED_MULTIPLIER;

    // Wave lengths calculated dynamically based on strip length
    // Scales animation to match lamp size: longer strips = longer waves
    float wave_length_side = (WAVE_HEIGHT_LENGTH + WAVE_PERIOD_LENGTH) / 2.0 * WAVE_LENGTH_MULTIPLIER;
    float wave_length_center = WIND_SPEED_LENGTH * WAVE_LENGTH_MULTIPLIER;

    // Calculated properties (pure functions, no side effects)
    float getBaseIntensity() const {
        return (brightness_min_percent + brightness_max_percent) / 200.0;
    }
    float getAmplitude() const {
        return (brightness_max_percent - brightness_min_percent) / 200.0;
    }
};

// ---------------- LED MAPPING CONFIGURATION STRUCT ----------------

struct LEDMappingConfig {
    // Auto-calculated scaling parameters (derived from admin configuration)
    float wind_scale_numerator = WIND_SPEED_LENGTH - 2;  // Usable LEDs (excluding status + wind direction)
    float wind_scale_denominator = MAX_WIND_SPEED_MPS;   // Maximum wind speed from admin config
    float mps_to_knots_factor = 1.94384;                 // Conversion constant: m/s to knots
    uint8_t wave_height_divisor = (MAX_WAVE_HEIGHT_METERS * 100) / WAVE_HEIGHT_LENGTH;  // Centimeters per LED
    float threshold_brightness_multiplier = 1.2;         // Brightness boost when threshold exceeded (60% brighter)

    // Helper: Calculate wind speed LEDs from m/s (used by all wind speed calculations)
    int calculateWindLEDs(float windSpeed_mps) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            WIND_SPEED_LENGTH - 2  // Reserve bottom for status, top for wind direction
        );
    }

    // Helper: Calculate wave height LEDs from centimeters (used by updateSurfDisplay)
    int calculateWaveLEDsFromCm(int waveHeight_cm) const {
        // Round to nearest LED: add half divisor before dividing
        return constrain(
            static_cast<int>((waveHeight_cm + wave_height_divisor / 2) / wave_height_divisor),
            0,
            WAVE_HEIGHT_LENGTH
        );
    }

    // Helper: Calculate wave height LEDs from meters (used by status endpoint)
    int calculateWaveLEDsFromMeters(float waveHeight_m) const {
        return calculateWaveLEDsFromCm(static_cast<int>(waveHeight_m * 100));  // Convert m to cm
    }

    // Helper: Calculate wave period LEDs (1:1 mapping: seconds to LEDs)
    int calculateWavePeriodLEDs(float wavePeriod_s) const {
        return constrain(static_cast<int>(wavePeriod_s), 0, WAVE_PERIOD_LENGTH);
    }

    // Helper: Convert wind speed from m/s to knots
    float windSpeedToKnots(float windSpeed_mps) const {
        return windSpeed_mps * mps_to_knots_factor;
    }

    // Helper: Get threshold alert brightness value (pre-calculated, clamped to MAX_BRIGHTNESS)
    uint8_t getThresholdBrightness() const {
        return min(MAX_BRIGHTNESS, static_cast<int>(MAX_BRIGHTNESS * threshold_brightness_multiplier));
    }
};

// Global configuration instances (defined in main .ino file, declared extern here)
extern WaveConfig waveConfig;
extern LEDMappingConfig ledMapping;

// Configuration printing removed to save flash memory

#endif // CONFIG_H
