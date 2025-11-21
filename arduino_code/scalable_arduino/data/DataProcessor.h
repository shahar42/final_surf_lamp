#ifndef DATA_PROCESSOR_H
#define DATA_PROCESSOR_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "SurfDataModel.h"
#include "../config/SystemConfig.h"

/**
 * Data Processor
 * - Parses JSON surf data from server
 * - Validates data integrity
 * - Converts units as needed
 * - Single responsibility: Data parsing only
 */

class DataProcessor {
public:
    /**
     * Process raw JSON surf data
     * @param jsonData Raw JSON string from server
     * @param surfData Output surf data structure
     * @param currentTheme Output theme string
     * @return true if parsing successful, false otherwise
     */
    static bool processJSON(const String& jsonData, SurfData& surfData, String& currentTheme) {
        DynamicJsonDocument doc(JSON_CAPACITY);
        DeserializationError error = deserializeJson(doc, jsonData);

        if (error) {
            Serial.printf("❌ DataProcessor: JSON parsing failed: %s\n", error.c_str());
            return false;
        }

        // Extract values with defaults
        int wave_height_cm = doc["wave_height_cm"] | 0;
        float wave_period_s = doc["wave_period_s"] | 0.0;
        int wind_speed_mps = doc["wind_speed_mps"] | 0;
        int wind_direction_deg = doc["wind_direction_deg"] | 0;
        int wave_threshold_cm = doc["wave_threshold_cm"] | 100;
        int wind_speed_threshold_knots = doc["wind_speed_threshold_knots"] | 15;
        bool quiet_hours_active = doc["quiet_hours_active"] | false;
        String led_theme = doc["led_theme"] | "classic_surf";

        // Validate ranges
        if (!validateData(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg)) {
            Serial.println("❌ DataProcessor: Data validation failed");
            return false;
        }

        // Update theme if changed
        if (led_theme != currentTheme) {
            currentTheme = led_theme;
            Serial.printf("🎨 DataProcessor: Theme updated to '%s'\n", currentTheme.c_str());
        }

        // Log received data
        logReceivedData(wave_height_cm, wave_period_s, wind_speed_mps,
                       wind_direction_deg, wave_threshold_cm,
                       wind_speed_threshold_knots, quiet_hours_active, led_theme);

        // Update surf data structure (converts cm to meters)
        surfData.waveHeight = wave_height_cm / 100.0;
        surfData.wavePeriod = wave_period_s;
        surfData.windSpeed = wind_speed_mps;
        surfData.windDirection = wind_direction_deg;
        surfData.waveThreshold = wave_threshold_cm / 100.0;  // Convert to meters
        surfData.windSpeedThreshold = wind_speed_threshold_knots;
        surfData.quietHoursActive = quiet_hours_active;
        surfData.lastUpdate = millis();
        surfData.dataReceived = true;
        surfData.needsDisplayUpdate = true;

        Serial.println("✅ DataProcessor: Data processed successfully");
        return true;
    }

    /**
     * Validate data ranges
     */
    static bool validateData(int wave_height_cm, float wave_period_s,
                            int wind_speed_mps, int wind_direction_deg) {
        // Wave height: 0-500cm (0-5m) reasonable range
        if (wave_height_cm < 0 || wave_height_cm > 500) {
            Serial.printf("⚠️ DataProcessor: Invalid wave height: %d cm\n", wave_height_cm);
            return false;
        }

        // Wave period: 0-30s reasonable range
        if (wave_period_s < 0 || wave_period_s > 30) {
            Serial.printf("⚠️ DataProcessor: Invalid wave period: %.1f s\n", wave_period_s);
            return false;
        }

        // Wind speed: 0-50 m/s reasonable range (~0-100 knots)
        if (wind_speed_mps < 0 || wind_speed_mps > 50) {
            Serial.printf("⚠️ DataProcessor: Invalid wind speed: %d m/s\n", wind_speed_mps);
            return false;
        }

        // Wind direction: 0-360 degrees
        if (wind_direction_deg < 0 || wind_direction_deg > 360) {
            Serial.printf("⚠️ DataProcessor: Invalid wind direction: %d°\n", wind_direction_deg);
            return false;
        }

        return true;
    }

    /**
     * Log received surf data
     */
    static void logReceivedData(int wave_height_cm, float wave_period_s,
                               int wind_speed_mps, int wind_direction_deg,
                               int wave_threshold_cm, int wind_speed_threshold_knots,
                               bool quiet_hours_active, const String& led_theme) {
        Serial.println("🌊 DataProcessor: Surf Data Received:");
        Serial.printf("   Wave Height: %d cm\n", wave_height_cm);
        Serial.printf("   Wave Period: %.1f s\n", wave_period_s);
        Serial.printf("   Wind Speed: %d m/s\n", wind_speed_mps);
        Serial.printf("   Wind Direction: %d°\n", wind_direction_deg);
        Serial.printf("   Wave Threshold: %d cm\n", wave_threshold_cm);
        Serial.printf("   Wind Speed Threshold: %d knots\n", wind_speed_threshold_knots);
        Serial.printf("   Quiet Hours: %s\n", quiet_hours_active ? "true" : "false");
        Serial.printf("   LED Theme: %s\n", led_theme.c_str());
        Serial.printf("   Timestamp: %lu ms\n", millis());
    }
};

#endif // DATA_PROCESSOR_H
