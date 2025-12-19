#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ---------------- DEVICE IDENTITY ----------------
const int ARDUINO_ID = 6;  // Maayan's Lamp ID

// ---------------- HARDWARE SETUP ----------------
#define LED_PIN 2              // GPIO pin connected to LED strip data line
#define TOTAL_LEDS 56          // Total number of LEDs in the physical strip
#define LED_TYPE WS2812B       // LED chipset type
#define COLOR_ORDER GRB        // Color order for your LED strip
#define BRIGHTNESS 90          // Global brightness (0-255)
#define MAX_BRIGHTNESS 255     // Maximum LED brightness value
#define BUTTON_PIN 0           // ESP32 boot button

// ---------------- LED STRIP MAPPING ----------------
// Define the physical LED indices for each strip (bottom = where strip starts, top = where it ends)
// Direction is auto-detected: if bottom < top = FORWARD, if bottom > top = REVERSE

// Wave Height Strip (Right Side)
#define WAVE_HEIGHT_BOTTOM 3
#define WAVE_HEIGHT_TOP 16

// Wave Period Strip (Left Side)
#define WAVE_PERIOD_BOTTOM 41
#define WAVE_PERIOD_TOP 55

// Wind Speed Strip (Center)
#define WIND_SPEED_BOTTOM 38   // Bottom LED = Status indicator
#define WIND_SPEED_TOP 21      // Top LED = Wind direction indicator

// ---------------- SURF DATA SCALING ----------------
#define MAX_WAVE_HEIGHT_METERS 3.0   // Maximum wave height to display (meters)
#define MAX_WIND_SPEED_MPS 18.0      // Maximum wind speed to display (m/s) - 35 knots

// ---------------- WAVE ANIMATION ----------------
#define WAVE_BRIGHTNESS_MIN_PERCENT 50   // Minimum brightness during wave animation (0-100%)
#define WAVE_BRIGHTNESS_MAX_PERCENT 110  // Maximum brightness during wave animation (0-100%)
#define WAVE_LENGTH_SIDE 10.0            // Wave length for side strips (LEDs per cycle)
#define WAVE_LENGTH_CENTER 12.0          // Wave length for center strip (LEDs per cycle)
#define WAVE_SPEED_MULTIPLIER 1.2        // Animation speed multiplier (higher = faster)

// ---------------- SYSTEM CONSTANTS ----------------
#define WIFI_TIMEOUT 30                  // WiFi connection timeout (seconds)
#define HTTP_TIMEOUT_MS 15000            // HTTP request timeout (milliseconds)
#define JSON_CAPACITY 1024               // JSON document capacity
const unsigned long FETCH_INTERVAL = 780000; // 13 minutes
const unsigned long DATA_STALENESS_THRESHOLD = 1800000; // 30 minutes (2 missed fetches + grace period)
const int MAX_WIFI_RETRIES = 10;  // 10 attempts × 30s = ~5 min

// ---------------- AUTO-CALCULATED VALUES ----------------
// Strip directions (auto-detected)
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

// Strip lengths (auto-calculated from bottom/top)
#define WAVE_HEIGHT_LENGTH (abs(WAVE_HEIGHT_TOP - WAVE_HEIGHT_BOTTOM) + 1)
#define WAVE_PERIOD_LENGTH (abs(WAVE_PERIOD_TOP - WAVE_PERIOD_BOTTOM) + 1)
#define WIND_SPEED_LENGTH (abs(WIND_SPEED_TOP - WIND_SPEED_BOTTOM) + 1)

// Special function LEDs
#define STATUS_LED_INDEX WIND_SPEED_BOTTOM
#define WIND_DIRECTION_INDEX WIND_SPEED_TOP

#endif // CONFIG_H
