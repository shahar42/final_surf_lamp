#ifndef SURF_DATA_MODEL_H
#define SURF_DATA_MODEL_H

#include <Arduino.h>

/**
 * Surf Data Model
 * - Clean data structures for surf conditions
 * - Single source of truth for surf state
 * - Type-safe with validation
 */

/**
 * Main surf data structure
 * Stores current surf conditions and thresholds
 */
struct SurfData {
    // Surf Measurements (from server)
    float waveHeight;        // Wave height in meters
    float wavePeriod;        // Wave period in seconds
    float windSpeed;         // Wind speed in m/s
    int windDirection;       // Wind direction in degrees (0-360)

    // User Thresholds
    int waveThreshold;       // Wave height threshold in meters
    int windSpeedThreshold;  // Wind speed threshold in knots

    // System State
    bool quietHoursActive;   // True during night hours
    bool dataReceived;       // True if valid data has been received
    bool needsDisplayUpdate; // Flag to trigger display refresh

    // Metadata
    unsigned long lastUpdate;  // Timestamp of last data update (millis)

    // Constructor with defaults
    SurfData()
        : waveHeight(0.0)
        , wavePeriod(0.0)
        , windSpeed(0.0)
        , windDirection(0)
        , waveThreshold(100)
        , windSpeedThreshold(15)
        , quietHoursActive(false)
        , dataReceived(false)
        , needsDisplayUpdate(false)
        , lastUpdate(0)
    {}

    /**
     * Check if data is fresh (within timeout)
     */
    bool isFresh(unsigned long timeout_ms) const {
        if (!dataReceived) return false;
        return (millis() - lastUpdate) < timeout_ms;
    }

    /**
     * Check if wave threshold is exceeded
     */
    bool isWaveThresholdExceeded() const {
        return waveHeight >= waveThreshold;
    }

    /**
     * Check if wind threshold is exceeded (converts m/s to knots)
     */
    bool isWindThresholdExceeded() const {
        float windSpeedKnots = windSpeed * 1.94384;  // m/s to knots
        return windSpeedKnots >= windSpeedThreshold;
    }

    /**
     * Mark data as stale/invalid
     */
    void invalidate() {
        dataReceived = false;
        needsDisplayUpdate = true;
    }

    /**
     * Update all surf data at once
     */
    void update(float waveHeight_m, float wavePeriod_s, float windSpeed_mps,
                int windDirection_deg, int waveThreshold_m, int windSpeedThreshold_kts,
                bool quietHours, const String& theme)
    {
        this->waveHeight = waveHeight_m;
        this->wavePeriod = wavePeriod_s;
        this->windSpeed = windSpeed_mps;
        this->windDirection = windDirection_deg;
        this->waveThreshold = waveThreshold_m;
        this->windSpeedThreshold = windSpeedThreshold_kts;
        this->quietHoursActive = quietHours;
        this->lastUpdate = millis();
        this->dataReceived = true;
        this->needsDisplayUpdate = true;
    }

    /**
     * Print data summary (for debugging)
     */
    void printSummary() const {
        Serial.println("🌊 Surf Data Summary:");
        Serial.printf("   Wave Height: %.2f m (threshold: %d m) %s\n",
                      waveHeight, waveThreshold,
                      isWaveThresholdExceeded() ? "⚠️ EXCEEDED" : "");
        Serial.printf("   Wave Period: %.1f s\n", wavePeriod);
        Serial.printf("   Wind Speed: %.1f m/s (%.1f knots, threshold: %d knots) %s\n",
                      windSpeed, windSpeed * 1.94384, windSpeedThreshold,
                      isWindThresholdExceeded() ? "⚠️ EXCEEDED" : "");
        Serial.printf("   Wind Direction: %d°\n", windDirection);
        Serial.printf("   Quiet Hours: %s\n", quietHoursActive ? "YES" : "NO");
        Serial.printf("   Data Age: %lu ms %s\n",
                      millis() - lastUpdate,
                      dataReceived ? "" : "(INVALID)");
    }
};

/**
 * Wave animation configuration
 * Controls wave effect parameters
 */
struct WaveConfig {
    // User-adjustable parameters
    uint8_t brightness_min_percent;   // Minimum brightness during wave (0-100%)
    uint8_t brightness_max_percent;   // Maximum brightness during wave (0-100%)
    float wave_length_side;           // Wave length for side strips (LEDs per cycle)
    float wave_length_center;         // Wave length for center strip (LEDs per cycle)
    float wave_speed;                 // Wave speed multiplier

    // Constructor with defaults
    WaveConfig()
        : brightness_min_percent(50)
        , brightness_max_percent(110)
        , wave_length_side(6.0)
        , wave_length_center(8.0)
        , wave_speed(1.2)
    {}

    /**
     * Get base intensity for wave animation
     */
    float getBaseIntensity() const {
        return (brightness_min_percent + brightness_max_percent) / 200.0;
    }

    /**
     * Get amplitude for wave animation
     */
    float getAmplitude() const {
        return (brightness_max_percent - brightness_min_percent) / 200.0;
    }

    /**
     * Validate configuration
     */
    bool isValid() const {
        return brightness_min_percent <= 100 &&
               brightness_max_percent <= 100 &&
               wave_length_side > 0 &&
               wave_length_center > 0 &&
               wave_speed > 0;
    }
};

/**
 * LED mapping configuration
 * Controls how surf data maps to LED counts
 */
struct LEDMappingConfig {
    // User-adjustable parameters
    float wind_scale_numerator;          // Wind speed scaling numerator
    float wind_scale_denominator;        // Wind speed scaling denominator
    float mps_to_knots_factor;           // Conversion constant: m/s to knots
    uint8_t wave_height_divisor;         // Wave height scaling: cm per LED
    float threshold_brightness_multiplier; // Brightness boost when threshold exceeded

    // Constructor with defaults
    LEDMappingConfig()
        : wind_scale_numerator(12.0)
        , wind_scale_denominator(13.0)
        , mps_to_knots_factor(1.94384)
        , wave_height_divisor(25)
        , threshold_brightness_multiplier(1.4)
    {}

    /**
     * Calculate wind speed LEDs from m/s
     */
    int calculateWindLEDs(float windSpeed_mps, int maxLEDs) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            maxLEDs - 2  // Reserve LEDs for status and direction
        );
    }

    /**
     * Calculate wave height LEDs from centimeters
     */
    int calculateWaveLEDsFromCm(int waveHeight_cm, int maxLEDs) const {
        return constrain(
            static_cast<int>(waveHeight_cm / wave_height_divisor) + 1,  // +1 ensures at least 1 LED
            0,
            maxLEDs
        );
    }

    /**
     * Calculate wave height LEDs from meters
     */
    int calculateWaveLEDsFromMeters(float waveHeight_m, int maxLEDs) const {
        return calculateWaveLEDsFromCm(static_cast<int>(waveHeight_m * 100), maxLEDs);
    }

    /**
     * Calculate wave period LEDs (1:1 mapping)
     */
    int calculateWavePeriodLEDs(float wavePeriod_s, int maxLEDs) const {
        return constrain(static_cast<int>(wavePeriod_s), 0, maxLEDs);
    }

    /**
     * Convert wind speed from m/s to knots
     */
    float windSpeedToKnots(float windSpeed_mps) const {
        return windSpeed_mps * mps_to_knots_factor;
    }

    /**
     * Get threshold alert brightness value (clamped to 255)
     */
    uint8_t getThresholdBrightness(uint8_t baseBrightness = 255) const {
        return min(255, static_cast<int>(baseBrightness * threshold_brightness_multiplier));
    }
};

#endif // SURF_DATA_MODEL_H
