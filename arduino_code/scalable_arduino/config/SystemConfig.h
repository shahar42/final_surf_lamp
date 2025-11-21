#ifndef SYSTEM_CONFIG_H
#define SYSTEM_CONFIG_H

#include <Arduino.h>

/**
 * System-Wide Configuration
 * - All constants centralized here
 * - Easy to modify settings
 * - Single source of truth
 * - Compiled into binary (no runtime overhead)
 */

// ======================== HARDWARE CONFIGURATION ========================

// Pin Assignments
#define BUTTON_PIN 0              // ESP32 boot button
#define LED_PIN 2                 // GPIO 2 - Single continuous strip

// LED Strip Configuration
#define TOTAL_LEDS 47             // Total LEDs in the strip (0-46)
#define BRIGHTNESS 38             // Global brightness (0-255)
#define LED_TYPE WS2812B          // LED chip type
#define COLOR_ORDER GRB           // Color channel order

// LED Strip Section Mapping
// Wave Height (Right Side) - Forward direction
#define WAVE_HEIGHT_START 1
#define WAVE_HEIGHT_END 14
#define WAVE_HEIGHT_LENGTH 14

// Wave Period (Left Side) - Forward direction
#define WAVE_PERIOD_START 33
#define WAVE_PERIOD_END 46
#define WAVE_PERIOD_LENGTH 14

// Wind Speed (Center) - REVERSE direction (30 down to 17)
#define WIND_SPEED_START 30       // Bottom LED (also status LED)
#define WIND_SPEED_END 17         // Top LED (also wind direction LED)
#define WIND_SPEED_LENGTH 14      // Total including status + direction

// Special LEDs
#define STATUS_LED_INDEX 30       // Status indicator (bottom of wind strip)
#define WIND_DIRECTION_INDEX 17   // Wind direction (top of wind strip)

// Compatibility aliases
#define NUM_LEDS_RIGHT WAVE_HEIGHT_LENGTH
#define NUM_LEDS_LEFT WAVE_PERIOD_LENGTH
#define NUM_LEDS_CENTER WIND_SPEED_LENGTH

// ======================== DEVICE IDENTIFICATION ========================

#define ARDUINO_ID 1              // Unique device identifier

// ======================== NETWORK CONFIGURATION ========================

// WiFi Timeouts
#define WIFI_TIMEOUT 30           // Timeout for WiFi connection (seconds)
#define AP_TIMEOUT 60000          // AP mode timeout (milliseconds)

// HTTP Configuration
#define HTTP_TIMEOUT_MS 15000     // HTTP request timeout
#define HTTP_SERVER_PORT 80       // Web server port

// Default WiFi Credentials (fallback)
#define DEFAULT_SSID "Sunrise"
#define DEFAULT_PASSWORD "4085429360"

// AP Mode Configuration
#define CONFIG_AP_SSID "SurfLamp-Setup"
#define CONFIG_AP_PASSWORD "surf123456"

// ======================== DATA FETCH CONFIGURATION ========================

#define FETCH_INTERVAL 780000     // 13 minutes (milliseconds)
#define DATA_FRESHNESS_TIMEOUT 1800000  // 30 minutes

// ======================== LED BEHAVIOR CONFIGURATION ========================

// Animation Timing
#define BLINK_INTERVAL 1500       // Threshold alert blink speed (ms)
#define ANIMATION_UPDATE_RATE 5   // Animation frame update rate (ms)
#define STATUS_LED_UPDATE_RATE 20 // Status LED breathing update rate (ms)

// Brightness Limits
#define MAX_BRIGHTNESS 255        // Maximum LED brightness value
#define QUIET_HOURS_BRIGHTNESS_MULTIPLIER 0.3  // 30% brightness during quiet hours

// ======================== LED MAPPING CONFIGURATION ========================

// Wind Speed Mapping
#define WIND_SCALE_NUMERATOR 12.0
#define WIND_SCALE_DENOMINATOR 13.0
#define MPS_TO_KNOTS_FACTOR 1.94384

// Wave Height Mapping
#define WAVE_HEIGHT_DIVISOR 25    // Centimeters per LED (25cm = 1 LED)

// Threshold Alert Behavior
#define THRESHOLD_BRIGHTNESS_MULTIPLIER 1.4  // 60% brighter when threshold exceeded

// ======================== WAVE ANIMATION CONFIGURATION ========================

// Wave Effect Parameters
#define WAVE_BRIGHTNESS_MIN_PERCENT 50    // Minimum brightness during wave (0-100%)
#define WAVE_BRIGHTNESS_MAX_PERCENT 110   // Maximum brightness during wave (0-100%)
#define WAVE_LENGTH_SIDE 6.0              // Wave length for side strips (LEDs per cycle)
#define WAVE_LENGTH_CENTER 8.0            // Wave length for center strip (LEDs per cycle)
#define WAVE_SPEED 1.2                    // Wave speed multiplier

// ======================== JSON CONFIGURATION ========================

#define JSON_CAPACITY 1024        // JSON document capacity

// ======================== SYSTEM INFORMATION ========================

#define FIRMWARE_VERSION "3.0.0-scalable"
#define DEVICE_NAME "Surf Lamp (Scalable)"

// ======================== DEBUG CONFIGURATION ========================

// Enable/disable debug features
#define DEBUG_SERIAL_ENABLED true
#define DEBUG_BAUD_RATE 115200

// ======================== HELPER FUNCTIONS ========================

/**
 * Configuration validation (optional)
 * Call during setup() to verify configuration sanity
 */
inline bool validateConfiguration() {
    bool valid = true;

    // Check LED indices don't overlap incorrectly
    if (WAVE_HEIGHT_END >= WAVE_PERIOD_START) {
        Serial.println("⚠️ Config Error: Wave height and period strips overlap");
        valid = false;
    }

    if (WIND_SPEED_END > WIND_SPEED_START) {
        Serial.println("⚠️ Config Error: Wind speed strip direction incorrect");
        valid = false;
    }

    // Check brightness bounds
    if (BRIGHTNESS > MAX_BRIGHTNESS) {
        Serial.println("⚠️ Config Error: Brightness exceeds maximum");
        valid = false;
    }

    // Check timeouts are reasonable
    if (WIFI_TIMEOUT < 5) {
        Serial.println("⚠️ Config Warning: WiFi timeout very short");
    }

    if (valid) {
        Serial.println("✅ Configuration validation passed");
    } else {
        Serial.println("❌ Configuration validation FAILED");
    }

    return valid;
}

/**
 * Print configuration summary
 * Useful for debugging and documentation
 */
inline void printConfiguration() {
    Serial.println("📋 System Configuration:");
    Serial.printf("   Device: %s v%s\n", DEVICE_NAME, FIRMWARE_VERSION);
    Serial.printf("   Arduino ID: %d\n", ARDUINO_ID);
    Serial.println();

    Serial.println("   LED Configuration:");
    Serial.printf("     Total LEDs: %d\n", TOTAL_LEDS);
    Serial.printf("     Wave Height: LEDs %d-%d (%d total)\n",
                  WAVE_HEIGHT_START, WAVE_HEIGHT_END, WAVE_HEIGHT_LENGTH);
    Serial.printf("     Wave Period: LEDs %d-%d (%d total)\n",
                  WAVE_PERIOD_START, WAVE_PERIOD_END, WAVE_PERIOD_LENGTH);
    Serial.printf("     Wind Speed:  LEDs %d-%d (%d total, REVERSE)\n",
                  WIND_SPEED_START, WIND_SPEED_END, WIND_SPEED_LENGTH);
    Serial.printf("     Status LED:  %d\n", STATUS_LED_INDEX);
    Serial.printf("     Wind Dir:    %d\n", WIND_DIRECTION_INDEX);
    Serial.printf("     Brightness:  %d/%d\n", BRIGHTNESS, MAX_BRIGHTNESS);
    Serial.println();

    Serial.println("   Network Configuration:");
    Serial.printf("     WiFi Timeout: %d seconds\n", WIFI_TIMEOUT);
    Serial.printf("     AP Timeout:   %lu ms\n", AP_TIMEOUT);
    Serial.printf("     HTTP Timeout: %d ms\n", HTTP_TIMEOUT_MS);
    Serial.printf("     Config AP:    %s\n", CONFIG_AP_SSID);
    Serial.println();

    Serial.println("   Data Fetch Configuration:");
    Serial.printf("     Fetch Interval: %lu ms (~%d minutes)\n",
                  FETCH_INTERVAL, (int)(FETCH_INTERVAL / 60000));
    Serial.printf("     Data Freshness: %lu ms (~%d minutes)\n",
                  DATA_FRESHNESS_TIMEOUT, (int)(DATA_FRESHNESS_TIMEOUT / 60000));
    Serial.println();

    Serial.println("   LED Mapping Configuration:");
    Serial.printf("     Wind Scale: %.1f / %.1f\n",
                  WIND_SCALE_NUMERATOR, WIND_SCALE_DENOMINATOR);
    Serial.printf("     Wave Divisor: %d cm/LED\n", WAVE_HEIGHT_DIVISOR);
    Serial.printf("     Threshold Brightness: x%.1f\n",
                  THRESHOLD_BRIGHTNESS_MULTIPLIER);
    Serial.println();
}

#endif // SYSTEM_CONFIG_H
