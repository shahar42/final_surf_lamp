/*
 * SURF LAMP CONFIGURATION FILE
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>


const int ARDUINO_ID = 6;

// ---------------- HARDWARE SETUP ----------------
#define LED_PIN 2              // pin connected to LED strip
// NOTE: TOTAL_LEDS should be set to the highest LED index + 1.
#define TOTAL_LEDS 57          
#define LED_TYPE WS2812B       
#define COLOR_ORDER GRB        
#define BRIGHTNESS 75          // Global brightness effects all leds

// ---------------- LED STRIP MAPPING ----------------
// Direction is auto-detected: if bottom < top = FORWARD, if bottom > top = REVERSE

#define WAVE_HEIGHT_BOTTOM 2  
#define WAVE_HEIGHT_TOP 16     

#define WAVE_PERIOD_BOTTOM 41  
#define WAVE_PERIOD_TOP 55     

// Note: Wind strip is REVERSED (BOTTOM > TOP)
// Bottom LED serves as status indicator, Top LED shows wind direction
#define WIND_SPEED_BOTTOM 38  
#define WIND_SPEED_TOP 21      

// ---------------- SURF DATA SCALING ----------------
// These values determine the maximum range displayed on each strip

#define MAX_WAVE_HEIGHT_METERS 3.0   
#define MAX_WIND_SPEED_MPS 18.0      // Maximum wind speed currently 45 knots
// Note: Wave period uses 1:1 mapping (1 LED = 1 second)

// ---------------- WAVE ANIMATION PARAMETERS ----------------
// Controls the blinking/wave effect when thresholds are exceeded

#define WAVE_BRIGHTNESS_MIN_PERCENT 45   // Minimum brightness during wave animation (0-100%)
#define WAVE_BRIGHTNESS_MAX_PERCENT 100  // Maximum brightness during wave animation (0-100%)
#define WAVE_LENGTH_MULTIPLIER 0.7       // Wave length as % of strip length
#define WAVE_SPEED_MULTIPLIER 1.2        // Animation speed multiplier
#define SUNRISE_OVERLAP_SECONDS 5        // Overlap time for sunrise animation

// ---------------- SYSTEM CONSTANTS ----------------

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

// Strip directions
#define WAVE_HEIGHT_FORWARD (WAVE_HEIGHT_BOTTOM < WAVE_HEIGHT_TOP)
#define WAVE_PERIOD_FORWARD (WAVE_PERIOD_BOTTOM < WAVE_PERIOD_TOP)
#define WIND_SPEED_FORWARD (WIND_SPEED_BOTTOM < WIND_SPEED_TOP)

// Strip start/end indices
#define WAVE_HEIGHT_START (WAVE_HEIGHT_FORWARD ? WAVE_HEIGHT_BOTTOM : WAVE_HEIGHT_TOP)
#define WAVE_HEIGHT_END (WAVE_HEIGHT_FORWARD ? WAVE_HEIGHT_TOP : WAVE_HEIGHT_BOTTOM)
#define WAVE_PERIOD_START (WAVE_PERIOD_FORWARD ? WAVE_PERIOD_BOTTOM : WAVE_PERIOD_TOP)
#define WAVE_PERIOD_END (WAVE_PERIOD_FORWARD ? WAVE_PERIOD_TOP : WAVE_PERIOD_BOTTOM)
#define WIND_SPEED_START (WIND_SPEED_FORWARD ? WIND_SPEED_BOTTOM : WIND_SPEED_TOP)
#define WIND_SPEED_END (WIND_SPEED_FORWARD ? WIND_SPEED_TOP : WIND_SPEED_BOTTOM)

// Strip lengths
#define WAVE_HEIGHT_LENGTH (abs(WAVE_HEIGHT_TOP - WAVE_HEIGHT_BOTTOM) + 1)
#define WAVE_PERIOD_LENGTH (abs(WAVE_PERIOD_TOP - WAVE_PERIOD_BOTTOM) + 1)
#define WIND_SPEED_LENGTH (abs(WIND_SPEED_TOP - WIND_SPEED_BOTTOM) + 1)

// Special function LEDs
#define STATUS_LED_INDEX WIND_SPEED_BOTTOM
#define WIND_DIRECTION_INDEX WIND_SPEED_TOP

// Legacy compatibility names
#define NUM_LEDS_RIGHT WAVE_HEIGHT_LENGTH
#define NUM_LEDS_LEFT WAVE_PERIOD_LENGTH
#define NUM_LEDS_CENTER WIND_SPEED_LENGTH

// ---------------- COMPILE-TIME VALIDATION ----------------

static_assert(TOTAL_LEDS > 0, "TOTAL_LEDS must be positive");
static_assert(TOTAL_LEDS <= 300, "TOTAL_LEDS exceeds reasonable limit (300)");
static_assert(BRIGHTNESS >= 0 && BRIGHTNESS <= 255, "BRIGHTNESS must be 0-255");

static_assert(WAVE_HEIGHT_LENGTH > 0, "Wave height strip is empty");
static_assert(WAVE_PERIOD_LENGTH > 0, "Wave period strip is empty");
static_assert(WIND_SPEED_LENGTH >= 3, "Wind speed strip needs minimum 3 LEDs");

static_assert(WIND_SPEED_BOTTOM > WIND_SPEED_TOP, "Wind strip MUST be reversed (BOTTOM > TOP)");

static_assert(WAVE_HEIGHT_BOTTOM < TOTAL_LEDS, "WAVE_HEIGHT_BOTTOM out of range");
static_assert(WAVE_HEIGHT_TOP < TOTAL_LEDS, "WAVE_HEIGHT_TOP out of range");
static_assert(WAVE_PERIOD_BOTTOM < TOTAL_LEDS, "WAVE_PERIOD_BOTTOM out of range");
static_assert(WAVE_PERIOD_TOP < TOTAL_LEDS, "WAVE_PERIOD_TOP out of range");
static_assert(WIND_SPEED_BOTTOM < TOTAL_LEDS, "WIND_SPEED_BOTTOM out of range");
static_assert(WIND_SPEED_TOP < TOTAL_LEDS, "WIND_SPEED_TOP out of range");
static_assert(STATUS_LED_INDEX < TOTAL_LEDS, "Status LED index out of range");
static_assert(WIND_DIRECTION_INDEX < TOTAL_LEDS, "Wind direction LED index out of range");

static_assert(MAX_WAVE_HEIGHT_METERS > 0, "MAX_WAVE_HEIGHT_METERS must be positive");
static_assert(MAX_WIND_SPEED_MPS > 0, "MAX_WIND_SPEED_MPS must be positive");

static_assert(WAVE_BRIGHTNESS_MIN_PERCENT >= 0 && WAVE_BRIGHTNESS_MIN_PERCENT <= 100,
              "WAVE_BRIGHTNESS_MIN_PERCENT must be 0-100");
static_assert(WAVE_BRIGHTNESS_MAX_PERCENT >= 0 && WAVE_BRIGHTNESS_MAX_PERCENT <= 100,
              "WAVE_BRIGHTNESS_MAX_PERCENT must be 0-100");
static_assert(WAVE_BRIGHTNESS_MIN_PERCENT <= WAVE_BRIGHTNESS_MAX_PERCENT,
              "WAVE_BRIGHTNESS_MIN_PERCENT must be <= WAVE_BRIGHTNESS_MAX_PERCENT");

// ---------------- WAVE ANIMATION CONFIGURATION STRUCT ----------------

struct WaveConfig {
    uint8_t brightness_min_percent = WAVE_BRIGHTNESS_MIN_PERCENT;
    uint8_t brightness_max_percent = WAVE_BRIGHTNESS_MAX_PERCENT;
    float wave_speed = WAVE_SPEED_MULTIPLIER;

    float wave_length_side = (WAVE_HEIGHT_LENGTH + WAVE_PERIOD_LENGTH) / 2.0 * WAVE_LENGTH_MULTIPLIER;
    float wave_length_center = WIND_SPEED_LENGTH * WAVE_LENGTH_MULTIPLIER;

    float getBaseIntensity() const {
        return (brightness_min_percent + brightness_max_percent) / 200.0;
    }
    float getAmplitude() const {
        return (brightness_max_percent - brightness_min_percent) / 200.0;
    }
};

// ---------------- LED MAPPING CONFIGURATION STRUCT ----------------

struct LEDMappingConfig {
    float wind_scale_numerator = WIND_SPEED_LENGTH - 2;
    float wind_scale_denominator = MAX_WIND_SPEED_MPS;
    float mps_to_knots_factor = 1.94384;
    uint8_t wave_height_divisor = (MAX_WAVE_HEIGHT_METERS * 100) / WAVE_HEIGHT_LENGTH;
    float threshold_brightness_multiplier = 1.2;

    int calculateWindLEDs(float windSpeed_mps) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            WIND_SPEED_LENGTH - 2
        );
    }

    int calculateWaveLEDsFromCm(int waveHeight_cm) const {
        return constrain(
            static_cast<int>((waveHeight_cm + wave_height_divisor / 2) / wave_height_divisor),
            0,
            WAVE_HEIGHT_LENGTH
        );
    }

    int calculateWaveLEDsFromMeters(float waveHeight_m) const {
        return calculateWaveLEDsFromCm(static_cast<int>(waveHeight_m * 100));
    }

    int calculateWavePeriodLEDs(float wavePeriod_s) const {
        return constrain(static_cast<int>(wavePeriod_s), 0, WAVE_PERIOD_LENGTH);
    }

    float windSpeedToKnots(float windSpeed_mps) const {
        return windSpeed_mps * mps_to_knots_factor;
    }

    uint8_t getThresholdBrightness() const {
        return min(MAX_BRIGHTNESS, static_cast<int>(MAX_BRIGHTNESS * threshold_brightness_multiplier));
    }
};

extern WaveConfig waveConfig;
extern LEDMappingConfig ledMapping;

// ---------------- BRIGHTNESS LEVEL STRUCT ----------------

struct BrightnessLevel {
    static constexpr float LEVEL_LOW = 0.2f;   // Very dim
    static constexpr float LEVEL_MID = 0.6f;   // Default brightness
    static constexpr float LEVEL_HIGH = 1.0f;  // Maximum brightness
};

// ---------------- SURF DATA DEFAULTS STRUCT ----------------

struct SurfDataDefaults {
    static constexpr int WAVE_HEIGHT_CM = 0;
    static constexpr float WAVE_PERIOD_S = 0.0;
    static constexpr int WIND_SPEED_MPS = 0;
    static constexpr int WIND_DIRECTION_DEG = 0;
    static constexpr int WAVE_THRESHOLD_CM = 100;
    static constexpr int WIND_SPEED_THRESHOLD_KNOTS = 15;
    static constexpr bool QUIET_HOURS_ACTIVE = false;
    static constexpr bool OFF_HOURS_ACTIVE = false;
    static constexpr float BRIGHTNESS_MULTIPLIER = 0.6;
    static constexpr const char* LED_THEME = "classic_surf";
};

// ---------------- CACHED SETTINGS STRUCT ----------------

struct CachedSettings {
    // Location data
    String location = "";
    float latitude = 0.0;
    float longitude = 0.0;
    int8_t tz_offset = 0;

    // Thresholds
    int wave_threshold_min_cm = 100;
    int wave_threshold_max_cm = 99900;
    int wind_speed_threshold_min_knots = 15;
    int wind_speed_threshold_max_knots = 999;

    // Display settings
    String led_theme = "classic_surf";
    float brightness_multiplier = 0.6;

    // Hour modes
    bool quiet_hours_active = false;
    bool off_hours_active = false;

    // Timing
    unsigned long last_fetch_ms = 0;
    static constexpr unsigned long FETCH_INTERVAL_MS = 3600000; // 60 minutes

    bool needsRefresh() const {
        return last_fetch_ms == 0 || millis() - last_fetch_ms > FETCH_INTERVAL_MS;
    }
};

#endif // CONFIG_H