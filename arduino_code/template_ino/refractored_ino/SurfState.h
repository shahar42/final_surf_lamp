#ifndef SURF_STATE_H
#define SURF_STATE_H

#include <Arduino.h>
#include "Config.h"

// ---------------------------- Surf Data Structure ----------------------------
// Last received surf data (for status reporting)
// CRITICAL: waveHeight and waveThreshold MUST both be float and both in METERS
struct SurfData {
    float waveHeight = 0.0;        // Stored in METERS (converted from cm via /100.0)
    float wavePeriod = 0.0;
    float windSpeed = 0.0;
    int windDirection = 0;
    float waveThreshold = 1.0;     // Stored in METERS (converted from cm via /100.0)
    int windSpeedThreshold = 15;
    bool quietHoursActive = false;
    bool offHoursActive = false;
    unsigned long lastUpdate = 0;
    bool dataReceived = false;
    bool needsDisplayUpdate = false;  // Flag to trigger display refresh
    String currentTheme = "classic_surf"; // Default theme
};

// ---------------------------- Wave Animation Configuration ----------------------------
struct WaveConfig {
    // Parameters loaded from admin configuration
    uint8_t brightness_min_percent = WAVE_BRIGHTNESS_MIN_PERCENT;
    uint8_t brightness_max_percent = WAVE_BRIGHTNESS_MAX_PERCENT;
    float wave_length_side = WAVE_LENGTH_SIDE;
    float wave_length_center = WAVE_LENGTH_CENTER;
    float wave_speed = WAVE_SPEED_MULTIPLIER;

    // Calculated properties
    float getBaseIntensity() const {
        return (brightness_min_percent + brightness_max_percent) / 200.0;
    }
    float getAmplitude() const {
        return (brightness_max_percent - brightness_min_percent) / 200.0;
    }
};

// ---------------------------- LED Mapping Configuration ----------------------------
struct LEDMappingConfig {
    // Auto-calculated scaling parameters (derived from Config.h)
    float wind_scale_numerator = WIND_SPEED_LENGTH - 2;  // Usable LEDs (excluding status + wind direction)
    float wind_scale_denominator = MAX_WIND_SPEED_MPS;   // Maximum wind speed from admin config
    float mps_to_knots_factor = 1.94384;                 // Conversion constant: m/s to knots
    uint8_t wave_height_divisor = (int)((MAX_WAVE_HEIGHT_METERS * 100) / WAVE_HEIGHT_LENGTH);  // Centimeters per LED
    float threshold_brightness_multiplier = 1.4;         // Brightness boost when threshold exceeded (60% brighter)

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
        if (wave_height_divisor == 0) return 1; // Prevent division by zero
        return constrain(
            static_cast<int>(waveHeight_cm / wave_height_divisor) + 1,  // +1 ensures at least 1 LED
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

#endif // SURF_STATE_H
