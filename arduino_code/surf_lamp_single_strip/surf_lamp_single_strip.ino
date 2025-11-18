/*
 * SURF LAMP - SINGLE WRAPPED STRIP VERSION
 *
 * Hardware: Single continuous WS2812B LED strip wrapped to appear as 3 visual strips
 *
 * LED MAPPING (Based on physical testing):
 * - Strip 1 (Wave Height - Right): LEDs 1-14 (14 total, bottom-up)
 * - Strip 2 (Wave Period - Left):  LEDs 33-46 (14 total, bottom-up)
 * - Strip 3 (Wind Speed - Center):  LEDs 30-17 (14 total, REVERSE - bottom 30 to top 17)
 *
 * Special LEDs:
 * - LED 30: Status indicator (blue/green/red/yellow for WiFi/data status)
 * - LED 17: Wind direction indicator (green/yellow/red/blue for N/E/S/W)
 *
 * CHANGES FROM ORIGINAL 3-STRIP VERSION:
 * - Single LED array instead of 3 separate arrays
 * - Custom index mapping functions for each visual strip
 * - Reverse direction handling for wind strip (30→17)
 * - ALL OTHER LOGIC IDENTICAL (WiFi, server, thresholds, themes, etc.)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

#include "ServerDiscovery.h"

// Global discovery instance
ServerDiscovery serverDiscovery;

// ---------------------------- Configuration ----------------------------
#define BUTTON_PIN 0  // ESP32 boot button

// *** SINGLE STRIP CONFIGURATION ***
#define LED_PIN 2            // GPIO 2 - Single continuous strip
#define TOTAL_LEDS 47        // Total LEDs in the strip (0-46)
#define BRIGHTNESS 38
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

// LED STRIP SECTION MAPPING
// Wave Height (Right Side) - Forward direction
#define WAVE_HEIGHT_START 1
#define WAVE_HEIGHT_END 14
#define WAVE_HEIGHT_LENGTH 14

// Wave Period (Left Side) - Forward direction
#define WAVE_PERIOD_START 33
#define WAVE_PERIOD_END 46
#define WAVE_PERIOD_LENGTH 14

// Wind Speed (Center) - REVERSE direction (30 down to 17)
#define WIND_SPEED_START 30      // Bottom LED (also status LED)
#define WIND_SPEED_END 17        // Top LED (also wind direction LED)
#define WIND_SPEED_LENGTH 14     // Total including status + direction

// Special LEDs
#define STATUS_LED_INDEX 30      // Status indicator (bottom of wind strip)
#define WIND_DIRECTION_INDEX 17  // Wind direction (top of wind strip)

// For compatibility with original code calculations
#define NUM_LEDS_RIGHT WAVE_HEIGHT_LENGTH
#define NUM_LEDS_LEFT WAVE_PERIOD_LENGTH
#define NUM_LEDS_CENTER WIND_SPEED_LENGTH

#define WIFI_TIMEOUT 30  // Timeout for WiFi connection in seconds

// System Constants (non-LED related)
#define MAX_BRIGHTNESS 255           // Maximum LED brightness value
#define HTTP_TIMEOUT_MS 15000        // HTTP request timeout in milliseconds
#define JSON_CAPACITY 1024           // JSON document capacity for Arduino data

// Device Configuration
const int ARDUINO_ID = 1;  // ✨ Single-strip surf lamp

// Global Variables
Preferences preferences;
WebServer server(80);
bool configure_wifi = false;
unsigned long apStartTime = 0;
const unsigned long AP_TIMEOUT = 60000;  // 60 seconds timeout
unsigned long lastDataFetch = 0;
const unsigned long FETCH_INTERVAL = 780000; // 13 minutes

// Blinking state variables
unsigned long lastBlinkUpdate = 0;
const unsigned long BLINK_INTERVAL = 1500; // 1.5 seconds for slow smooth blink
float blinkPhase = 0.0; // Phase for smooth sine wave blinking

// Wi-Fi credentials (defaults)
char ssid[32] = "Sunrise";
char password[64] = "4085429360";

// *** SINGLE LED ARRAY (CRITICAL CHANGE) ***
CRGB leds[TOTAL_LEDS];

// Last received surf data (for status reporting)
struct SurfData {
    float waveHeight = 0.0;
    float wavePeriod = 0.0;
    float windSpeed = 0.0;
    int windDirection = 0;
    int waveThreshold = 100;
    int windSpeedThreshold = 15;
    bool quietHoursActive = false;
    unsigned long lastUpdate = 0;
    bool dataReceived = false;
    bool needsDisplayUpdate = false;  // Flag to trigger display refresh
} lastSurfData;


// ---------------------------- Wave Animation Configuration ----------------------------

struct WaveConfig {
    // User-adjustable parameters
    uint8_t brightness_min_percent = 50;   // Minimum brightness during wave (0-100%)
    uint8_t brightness_max_percent = 110;  // Maximum brightness during wave (0-100%)
    float wave_length_side = 6.0;          // Wave length for side strips (LEDs per cycle)
    float wave_length_center = 8.0;        // Wave length for center strip (LEDs per cycle)
    float wave_speed = 1.2;                // Wave speed multiplier

    // Calculated properties
    float getBaseIntensity() const {
        return (brightness_min_percent + brightness_max_percent) / 200.0;
    }
    float getAmplitude() const {
        return (brightness_max_percent - brightness_min_percent) / 200.0;
    }
};

// Global wave configuration instance
WaveConfig waveConfig;

// ---------------------------- LED Mapping Configuration ----------------------------

struct LEDMappingConfig {
    // User-adjustable parameters
    float wind_scale_numerator = 12.0;      // Wind speed scaling: maps 0-13 m/s to 0-12 LEDs (single-strip config)
    float wind_scale_denominator = 13.0;
    float mps_to_knots_factor = 1.94384;    // Conversion constant: m/s to knots
    uint8_t wave_height_divisor = 25;       // Wave height scaling: cm per LED (25cm = 1 LED)
    float threshold_brightness_multiplier = 1.4;  // Brightness boost when threshold exceeded (60% brighter)

    // Helper: Calculate wind speed LEDs from m/s (used by all wind speed calculations)
    int calculateWindLEDs(float windSpeed_mps) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            WIND_SPEED_LENGTH - 2  // Reserve LED 30 for status, LED 17 for wind direction
        );
    }

    // Helper: Calculate wave height LEDs from centimeters (used by updateSurfDisplay)
    int calculateWaveLEDsFromCm(int waveHeight_cm) const {
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

// Global LED mapping configuration instance
LEDMappingConfig ledMapping;

// Forward declarations
void setupHTTPEndpoints();
bool fetchSurfDataFromServer();
bool processSurfData(const String &jsonData);
void updateSurfDisplay();  // Now reads from global state, no parameters needed
void handleSurfDataUpdate();
void handleStatusRequest();
void handleTestRequest();
void handleLEDTestRequest();
void handleDeviceInfoRequest();
void handleManualFetchRequest();
void handleDiscoveryTest();
void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots);
void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm);
void updateBlinkingAnimation();

// ---------------------------- Theme Functions ----------------------------
CHSV getWindSpeedColor(String theme);
CHSV getWaveHeightColor(String theme);
CHSV getWavePeriodColor(String theme);

// ---------------------------- Color Maps ----------------------------

CHSV colorMap[] = {
    CHSV(120, 255, 125), CHSV(130, 255, 200), CHSV(140, 255, 255), CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(190, 255, 255), CHSV(200, 255, 200),
    CHSV(210, 255, 255), CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(110, 255, 255), CHSV(0, 0, 255)
};

CHSV colorMapWave[] = {
    CHSV(95, 255, 125),  CHSV(95, 255, 200),  CHSV(140, 255, 255), CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(190, 255, 255), CHSV(200, 255, 200),
    CHSV(210, 255, 255), CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(85, 255, 255),  CHSV(85, 255, 255)
};

CHSV colorMapWind[] = {
    CHSV(85, 255, 125),  CHSV(90, 255, 200),  CHSV(95, 255, 255),  CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(87, 255, 255),  CHSV(90, 255, 200),
    CHSV(95, 255, 255),  CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(85, 255, 255),  CHSV(85, 255, 255)
};

// ---------------------------- Theme Color Functions ----------------------------

String currentTheme = "classic_surf";  // Default theme

struct ThemeColors {
    CHSV wave_color;
    CHSV wind_color;
    CHSV period_color;
};

ThemeColors getThemeColors(String theme) {
    // 5 LED themes with completely distinct colors (minimal red)
    if (theme == "classic_surf") {
        return {{160, 255, 200}, {0, 50, 255}, {60, 255, 200}}; // Blue waves, white wind, yellow period
    } else if (theme == "vibrant_mix") {
        return {{240, 255, 200}, {85, 255, 200}, {160, 255, 200}}; // Purple waves, green wind, blue period
    } else if (theme == "tropical_paradise") {
        return {{85, 255, 200}, {140, 255, 200}, {200, 255, 200}}; // Green waves, cyan wind, magenta period
    } else if (theme == "ocean_sunset") {
        return {{160, 255, 220}, {20, 255, 220}, {212, 255, 220}}; // Blue waves, orange wind, pink period
    } else if (theme == "electric_vibes") {
        return {{140, 255, 240}, {60, 255, 240}, {240, 255, 240}}; // Cyan waves, yellow wind, purple period
    } else if (theme == "dark") {
        // Legacy dark theme
        return {{135, 255, 255}, {24, 250, 240}, {85, 155, 205}};
    } else {
        // Legacy day theme / fallback - now defaults to classic_surf
        return {{160, 255, 200}, {0, 50, 255}, {60, 255, 200}};
    }
}

CHSV getWindSpeedColor(String theme) {
    return getThemeColors(theme).wind_color;
}

CHSV getWaveHeightColor(String theme) {
    return getThemeColors(theme).wave_color;
}

CHSV getWavePeriodColor(String theme) {
    return getThemeColors(theme).period_color;
}


// ---------------------------- WiFi Credential Functions ----------------------------

void saveCredentials(const char* newSSID, const char* newPassword) {
    preferences.begin("wifi-creds", false);
    preferences.putString("ssid", newSSID);
    preferences.putString("password", newPassword);
    preferences.end();
    Serial.println("✅ WiFi credentials saved to NVRAM");
}

void loadCredentials() {
    preferences.begin("wifi-creds", false);
    String storedSSID = preferences.getString("ssid", ssid);
    String storedPassword = preferences.getString("password", password);
    preferences.end();

    storedSSID.toCharArray(ssid, sizeof(ssid));
    storedPassword.toCharArray(password, sizeof(password));

    Serial.printf("📝 Loaded credentials - SSID: %s\n", ssid);
}

// ---------------------------- Button Press Functions ----------------------------

void set_config_mode_and_restart() {
    if (digitalRead(BUTTON_PIN) == LOW) {
        Serial.println("🔘 Button pressed - setting config mode flag");

        // Visual feedback: Turn all LEDs blue
        fill_solid(leds, TOTAL_LEDS, CRGB::Blue);
        FastLED.show();

        // Set flag in NVRAM to enter AP mode on next boot
        preferences.begin("wifi-creds", false);
        preferences.putInt("button_pressed", 1);
        preferences.end();

        delay(500);
        Serial.println("🔄 Restarting to enter configuration mode...");
        ESP.restart();
    }
}

void checkButtonAndEnterAP() {
    preferences.begin("wifi-creds", false);
    int bootFlag = preferences.getInt("button_pressed", 0);

    if (bootFlag == 1) {
        Serial.println("🔘 Boot flag detected - entering AP mode");

        // Clear the flag immediately
        preferences.putInt("button_pressed", 0);
        preferences.end();

        // Visual feedback: Blue LEDs
        fill_solid(leds, TOTAL_LEDS, CRGB::Blue);
        FastLED.show();

        // Enter configuration mode
        startConfigMode();

        // Stay in AP mode indefinitely until configured
        while (true) {
            server.handleClient();
            delay(10);
        }
    }
    preferences.end();
}

// ---------------------------- LED Status Functions ----------------------------

void blinkStatusLED(CRGB color)
{
    static unsigned long lastStatusUpdate = 0;
    static float statusPhase = 0.0;

    // Update status LED at slower timing (every 20ms for slower pace)
    if (millis() - lastStatusUpdate >= 20) {
        statusPhase += 0.05; // Much slower: ~1.25-second cycle
        if (statusPhase >= 2 * PI) statusPhase = 0.0;
        lastStatusUpdate = millis();
    }

    // Gentler breathing pattern
    float brightnessFactor = 0.7 + 0.3 * sin(statusPhase);
    int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(MAX_BRIGHTNESS * brightnessFactor));

    // Convert RGB to HSV for brightness control
    CHSV hsvColor = rgb2hsv_approximate(color);
    hsvColor.val = adjustedBrightness;

    // *** CHANGE: Use STATUS_LED_INDEX (30) instead of leds_center[0] ***
    leds[STATUS_LED_INDEX] = hsvColor;
    FastLED.show();
}

void blinkBlueLED()  { blinkStatusLED(CRGB::Blue);  }   // Connecting to WiFi
void blinkGreenLED() { blinkStatusLED(CRGB::Green); }   // Connected and operational
void blinkRedLED()   { blinkStatusLED(CRGB::Red);   }   // Error state
void blinkYellowLED(){ blinkStatusLED(CRGB::Yellow);}   // Configuration mode

void clearLEDs() {
    FastLED.clear();
    FastLED.show();
}

void setStatusLED(CRGB color) {
    leds[STATUS_LED_INDEX] = color;
    FastLED.show();
}

// ---------------------------- LED Control Functions (MODIFIED FOR SINGLE STRIP) ----------------------------

// *** NEW: Wave Height Strip (LEDs 1-14, forward) ***
void updateWaveHeightLEDs(int numActiveLeds, CHSV color) {
    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        int index = WAVE_HEIGHT_START + i;
        if (i < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

// *** NEW: Wave Height Strip with Blinking (threshold exceeded) ***
void updateBlinkingWaveHeightLEDs(int numActiveLeds, CHSV baseColor) {
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        int index = WAVE_HEIGHT_START + i;

        if (i < numActiveLeds) {
            // Calculate wave position
            float wavePhase = blinkPhase * waveConfig.wave_speed - (i * 2.0 * PI / waveConfig.wave_length_side);
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

            leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

// *** NEW: Wave Period Strip (LEDs 33-46, forward) ***
void updateWavePeriodLEDs(int numActiveLeds, CHSV color) {
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        int index = WAVE_PERIOD_START + i;
        if (i < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

// *** NEW: Wind Speed Strip (LEDs 30-17, REVERSE) ***
void updateWindSpeedLEDs(int numActiveLeds, CHSV color) {
    // Wind strip runs BACKWARDS: 30 (bottom) -> 17 (top)
    // Skip LED 30 (status) and LED 17 (wind direction)

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_START - i;  // Count backwards from 30
        int ledPosition = i - 1;  // Logical position (0-based)

        if (ledPosition < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

// *** NEW: Wind Speed Strip with Blinking (threshold exceeded) ***
void updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor) {
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    // Wind strip runs BACKWARDS: 30 -> 17
    // Skip LED 30 (status) and LED 17 (wind direction)

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_START - i;  // Count backwards
        int ledPosition = i - 1;  // Logical position

        if (ledPosition < numActiveLeds) {
            // Calculate wave position
            float wavePhase = blinkPhase * waveConfig.wave_speed - (ledPosition * 2.0 * PI / waveConfig.wave_length_center);
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

            leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

// *** MODIFIED: Threshold functions to use new LED mapping ***
void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots) {
    // Skip all LED updates during quiet hours - quiet hours mode already set the display
    if (lastSurfData.quietHoursActive) return;

    // Convert wind speed from m/s to knots for threshold comparison
    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed_mps);

    if (windSpeedInKnots < windSpeedThreshold_knots) {
        // NORMAL MODE: Theme-based wind speed visualization
        updateWindSpeedLEDs(windSpeedLEDs, getWindSpeedColor(currentTheme));
    } else {
        // ALERT MODE: Blinking theme-based wind speed LEDs
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
    }
}

void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm) {
    // Skip all LED updates during quiet hours - quiet hours mode already set the display
    if (lastSurfData.quietHoursActive) return;

    if (waveHeight_cm < waveThreshold_cm) {
        // NORMAL MODE: Theme-based wave height visualization
        updateWaveHeightLEDs(waveHeightLEDs, getWaveHeightColor(currentTheme));
    } else {
        // ALERT MODE: Blinking theme-based wave height LEDs
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
    }
}

void updateBlinkingAnimation() {
    // Only update blinking if we have valid surf data and thresholds are exceeded
    if (!lastSurfData.dataReceived) return;

    // Skip all blinking during quiet hours (sleep time)
    if (lastSurfData.quietHoursActive) return;

    // Update timing once per call
    unsigned long currentMillis = millis();
    if (currentMillis - lastBlinkUpdate >= 5) { // 200 FPS for ultra-smooth animation
        blinkPhase += 0.0419; // 1.5-second cycle (slower threshold alerts)
        lastBlinkUpdate = currentMillis;
    }

    bool needsUpdate = false;

    // Check if wind speed threshold is exceeded
    float windSpeedInKnots = ledMapping.windSpeedToKnots(lastSurfData.windSpeed);
    if (windSpeedInKnots >= lastSurfData.windSpeedThreshold) {
        int windSpeedLEDs = ledMapping.calculateWindLEDs(lastSurfData.windSpeed);
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
        needsUpdate = true;
    }

    // Check if wave height threshold is exceeded (lastSurfData.waveHeight is in METERS)
    if (lastSurfData.waveHeight >= lastSurfData.waveThreshold) {
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(lastSurfData.waveHeight);
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
        needsUpdate = true;
    }

    // Only call FastLED.show() if we updated blinking LEDs
    if (needsUpdate) {
        FastLED.show();
    }
}

void setWindDirection(int windDirection) {
    Serial.printf("🐛 DEBUG: Wind direction = %d°\n", windDirection);

    // *** CHANGE: Use WIND_DIRECTION_INDEX (17) instead of leds_center[last] ***
    // Wind direction color coding (ALWAYS consistent for navigation)
    if ((windDirection >= 0 && windDirection <= 10) || (windDirection >= 300 && windDirection <= 360)) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Green;   // North - Green
    } else if (windDirection > 10 && windDirection <= 180) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Yellow;  // East - Yellow
    } else if (windDirection > 180 && windDirection <= 250) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Red;     // South - Red
    } else if (windDirection > 250 && windDirection < 300) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Blue;    // West - Blue
    }
}

void performLEDTest() {
    Serial.println("🧪 Running LED test sequence...");

    // Test each visual strip section with different colors
    Serial.println("   Testing Wave Height strip (LEDs 1-14)...");
    updateWaveHeightLEDs(WAVE_HEIGHT_LENGTH, CHSV(160, 255, 255));  // Blue
    FastLED.show();
    delay(1000);

    Serial.println("   Testing Wave Period strip (LEDs 33-46)...");
    updateWavePeriodLEDs(WAVE_PERIOD_LENGTH, CHSV(60, 255, 255));   // Yellow
    FastLED.show();
    delay(1000);

    Serial.println("   Testing Wind Speed strip (LEDs 30-17)...");
    updateWindSpeedLEDs(WIND_SPEED_LENGTH - 2, CHSV(0, 50, 255));   // White
    FastLED.show();
    delay(1000);

    Serial.println("   Testing status LED (LED 30)...");
    leds[STATUS_LED_INDEX] = CRGB::Green;
    FastLED.show();
    delay(1000);

    Serial.println("   Testing wind direction LED (LED 17)...");
    leds[WIND_DIRECTION_INDEX] = CRGB::Red;
    FastLED.show();
    delay(1000);

    // Rainbow test on entire strip
    Serial.println("   Running rainbow test on all LEDs...");
    for (int hue = 0; hue < 256; hue += 5) {
        fill_solid(leds, TOTAL_LEDS, CHSV(hue, 255, 255));
        FastLED.show();
        delay(20);
    }

    clearLEDs();
    Serial.println("✅ LED test completed");
}

// ---------------------------- WiFi Functions (UNCHANGED) ----------------------------

bool connectToWiFi() {
    Serial.println("🔄 Attempting WiFi connection...");
    WiFi.mode(WIFI_STA);
    loadCredentials();
    WiFi.begin(ssid, password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_TIMEOUT) {
        Serial.print(".");
        blinkBlueLED();
        delay(500);
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi Connected!");
        Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("📶 SSID: %s\n", WiFi.SSID().c_str());
        Serial.printf("💪 Signal Strength: %d dBm\n", WiFi.RSSI());

        setupHTTPEndpoints();
        return true;
    } else {
        Serial.println("\n❌ WiFi connection failed");
        return false;
    }
}

void startConfigMode() {
    configure_wifi = true;
    WiFi.disconnect(true);
    WiFi.mode(WIFI_AP);
    WiFi.softAP("SurfLamp-Setup", "surf123456");

    Serial.println("🔧 Configuration mode started");
    Serial.printf("📍 AP IP: %s\n", WiFi.softAPIP().toString().c_str());
    Serial.println("📱 Connect to 'SurfLamp-Setup' network");
    Serial.println("🌐 Password: surf123456");

    apStartTime = millis();

    // Configuration web interface
    server.on("/", HTTP_GET, []() {
        String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
        html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
        html += "<title>Surf Lamp Setup</title>";
        html += "<style>body{font-family:Arial;margin:40px;background:#f0f8ff;}";
        html += ".container{max-width:400px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 4px 6px rgba(0,0,0,0.1);}";
        html += "h1{color:#0066cc;text-align:center;}input{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px;}";
        html += "button{width:100%;padding:12px;background:#0066cc;color:white;border:none;border-radius:5px;font-size:16px;cursor:pointer;}";
        html += "button:hover{background:#0052a3;}</style></head><body>";
        html += "<div class='container'><h1>🌊 Surf Lamp Setup</h1>";
        html += "<form action='/save' method='POST'>";
        html += "<label>WiFi Network:</label><input type='text' name='ssid' placeholder='Enter WiFi SSID' required>";
        html += "<label>Password:</label><input type='password' name='password' placeholder='Enter WiFi Password' required>";
        html += "<button type='submit'>🚀 Connect to WiFi</button>";
        html += "</form></div></body></html>";

        server.send(200, "text/html", html);
    });

    server.on("/save", HTTP_POST, []() {
        if (server.hasArg("ssid") && server.hasArg("password")) {
            String newSSID = server.arg("ssid");
            String newPassword = server.arg("password");

            saveCredentials(newSSID.c_str(), newPassword.c_str());

            String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
            html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
            html += "<title>Connecting...</title>";
            html += "<style>body{font-family:Arial;text-align:center;margin:40px;background:#f0f8ff;}</style>";
            html += "</head><body><h1>🔄 Connecting to WiFi...</h1>";
            html += "<p>Surf Lamp is connecting to your network.</p>";
            html += "<p>This page will close automatically.</p></body></html>";

            server.send(200, "text/html", html);

            delay(2000);

            // Attempt connection with new credentials
            WiFi.softAPdisconnect(true);
            WiFi.mode(WIFI_STA);
            WiFi.begin(newSSID.c_str(), newPassword.c_str());

            Serial.printf("🔄 Connecting to: %s\n", newSSID.c_str());

            int attempts = 0;
            while (WiFi.status() != WL_CONNECTED && attempts < 20) {
                delay(1000);
                Serial.print(".");
                attempts++;
            }

            if (WiFi.status() == WL_CONNECTED) {
                Serial.println("\n✅ Connected to new WiFi!");
                Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());
                configure_wifi = false;
                setupHTTPEndpoints();
            } else {
                Serial.println("\n❌ Failed to connect to new WiFi");
                startConfigMode(); // Restart config mode
            }
        } else {
            server.send(400, "text/html", "<h1>❌ Error: Missing WiFi credentials</h1>");
        }
    });

    server.begin();
    Serial.println("🌐 Configuration server started");
}

void handleAPTimeout() {
    if (configure_wifi && (millis() - apStartTime > AP_TIMEOUT)) {
        Serial.println("⏰ AP mode timeout - retrying WiFi connection");
        configure_wifi = false;

        while (!connectToWiFi()) {
            Serial.println("🔄 Retrying WiFi connection in 5 seconds...");
            delay(5000);
        }
    }
}

// ---------------------------- HTTP Server Endpoints (UNCHANGED) ----------------------------

void setupHTTPEndpoints() {
    // Main endpoint for receiving surf data from background processor
    server.on("/api/update", HTTP_POST, handleSurfDataUpdate);

    // Status endpoint for monitoring
    server.on("/api/status", HTTP_GET, handleStatusRequest);

    // Test endpoint for manual testing
    server.on("/api/test", HTTP_GET, handleTestRequest);

    // LED test endpoint
    server.on("/api/led-test", HTTP_GET, handleLEDTestRequest);

    // Device info endpoint
    server.on("/api/info", HTTP_GET, handleDeviceInfoRequest);

    // Manual surf data fetch endpoint
    server.on("/api/fetch", HTTP_GET, handleManualFetchRequest);

    server.on("/api/discovery-test", HTTP_GET, handleDiscoveryTest);


    server.begin();
    Serial.println("🌐 HTTP server started with endpoints:");
    Serial.println("   POST /api/update    - Receive surf data");
    Serial.println("   GET  /api/discovery-test - Test server discovery");
    Serial.println("   GET  /api/status    - Device status");
    Serial.println("   GET  /api/test      - Connection test");
    Serial.println("   GET  /api/led-test  - LED test");
    Serial.println("   GET  /api/info      - Device information");
    Serial.println("   GET  /api/fetch     - Manual surf data fetch");
}

void handleSurfDataUpdate() {
    Serial.println("📥 Received surf data request");

    if (!server.hasArg("plain")) {
        server.send(400, "application/json", "{\"ok\":false}");
        Serial.println("❌ No JSON data in request");
        return;
    }

    String jsonData = server.arg("plain");
    Serial.println("📋 Raw JSON data:");
    Serial.println(jsonData);

    if (processSurfData(jsonData)) {
        server.send(200, "application/json", "{\"ok\":true}");
        Serial.println("✅ Surf data processed successfully");
    } else {
        server.send(400, "application/json", "{\"ok\":false}");
        Serial.println("❌ Failed to process surf data");
    }
}

void handleStatusRequest() {
    DynamicJsonDocument statusDoc(1024);

    statusDoc["arduino_id"] = ARDUINO_ID;
    statusDoc["status"] = "online";
    statusDoc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
    statusDoc["ip_address"] = WiFi.localIP().toString();
    statusDoc["ssid"] = WiFi.SSID();
    statusDoc["signal_strength"] = WiFi.RSSI();
    statusDoc["uptime_ms"] = millis();
    statusDoc["free_heap"] = ESP.getFreeHeap();
    statusDoc["chip_model"] = ESP.getChipModel();
    statusDoc["firmware_version"] = "2.0.0-single-strip";

    // Last surf data
    statusDoc["last_surf_data"]["received"] = lastSurfData.dataReceived;
    statusDoc["last_surf_data"]["wave_height_m"] = lastSurfData.waveHeight;
    statusDoc["last_surf_data"]["wave_period_s"] = lastSurfData.wavePeriod;
    statusDoc["last_surf_data"]["wind_speed_mps"] = lastSurfData.windSpeed;
    statusDoc["last_surf_data"]["wind_direction_deg"] = lastSurfData.windDirection;
    statusDoc["last_surf_data"]["wave_threshold_cm"] = lastSurfData.waveThreshold;
    statusDoc["last_surf_data"]["wind_speed_threshold_knots"] = lastSurfData.windSpeedThreshold;
    statusDoc["last_surf_data"]["quiet_hours_active"] = lastSurfData.quietHoursActive;
    statusDoc["last_surf_data"]["last_update_ms"] = lastSurfData.lastUpdate;

    // Fetch timing information
    statusDoc["fetch_info"]["last_fetch_ms"] = lastDataFetch;
    statusDoc["fetch_info"]["fetch_interval_ms"] = FETCH_INTERVAL;
    statusDoc["fetch_info"]["time_since_last_fetch_ms"] = millis() - lastDataFetch;
    statusDoc["fetch_info"]["time_until_next_fetch_ms"] = FETCH_INTERVAL - (millis() - lastDataFetch);

    // LED calculation debug info
    if (lastSurfData.dataReceived) {
        int windSpeedLEDs = ledMapping.calculateWindLEDs(lastSurfData.windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(lastSurfData.waveHeight);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(lastSurfData.wavePeriod);

        statusDoc["led_calculations"]["wind_speed_leds"] = windSpeedLEDs;
        statusDoc["led_calculations"]["wind_formula"] = "windSpeed * " + String(ledMapping.wind_scale_numerator) + " / " + String(ledMapping.wind_scale_denominator);
        statusDoc["led_calculations"]["wind_calculation"] = String(lastSurfData.windSpeed) + " * " + String(ledMapping.wind_scale_numerator) + " / " + String(ledMapping.wind_scale_denominator) + " = " + String(lastSurfData.windSpeed * ledMapping.wind_scale_numerator / ledMapping.wind_scale_denominator);
        statusDoc["led_calculations"]["wave_height_leds"] = waveHeightLEDs;
        statusDoc["led_calculations"]["wave_period_leds"] = wavePeriodLEDs;
        statusDoc["led_calculations"]["wind_speed_knots"] = ledMapping.windSpeedToKnots(lastSurfData.windSpeed);
        statusDoc["led_calculations"]["wind_threshold_exceeded"] = ledMapping.windSpeedToKnots(lastSurfData.windSpeed) >= lastSurfData.windSpeedThreshold;
    }

    String statusJson;
    serializeJson(statusDoc, statusJson);

    server.send(200, "application/json", statusJson);
    Serial.println("📊 Status request served");
}

void handleTestRequest() {
    DynamicJsonDocument testDoc(256);
    testDoc["status"] = "ok";
    testDoc["message"] = "Arduino is responding";
    testDoc["arduino_id"] = ARDUINO_ID;
    testDoc["timestamp"] = millis();

    String testJson;
    serializeJson(testDoc, testJson);

    server.send(200, "application/json", testJson);
    Serial.println("🧪 Test request served");
}

void handleLEDTestRequest() {
    Serial.println("🧪 LED test requested via HTTP");
    performLEDTest();

    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LED test completed\"}");
}

void handleDeviceInfoRequest() {
    DynamicJsonDocument infoDoc(512);

    infoDoc["device_name"] = "Surf Lamp (Single Strip)";
    infoDoc["arduino_id"] = ARDUINO_ID;
    infoDoc["model"] = ESP.getChipModel();
    infoDoc["revision"] = ESP.getChipRevision();
    infoDoc["cores"] = ESP.getChipCores();
    infoDoc["flash_size"] = ESP.getFlashChipSize();
    infoDoc["psram_size"] = ESP.getPsramSize();
    infoDoc["firmware_version"] = "2.0.0-single-strip";
    infoDoc["led_strips"]["wave_height"] = WAVE_HEIGHT_LENGTH;
    infoDoc["led_strips"]["wave_period"] = WAVE_PERIOD_LENGTH;
    infoDoc["led_strips"]["wind_speed"] = WIND_SPEED_LENGTH;
    infoDoc["led_strips"]["total"] = TOTAL_LEDS;

    String infoJson;
    serializeJson(infoDoc, infoJson);

    server.send(200, "application/json", infoJson);
    Serial.println("ℹ️ Device info request served");
}

void handleDiscoveryTest() {
    Serial.println("🧪 Discovery test requested");

    bool result = serverDiscovery.forceDiscovery();
    String current = serverDiscovery.getCurrentServer();

    String response = "{\"server\":\"" + current + "\"}";
    server.send(200, "application/json", response);
}

void handleManualFetchRequest() {
    Serial.println("🔄 Manual surf data fetch requested");

    if (fetchSurfDataFromServer()) {
        lastDataFetch = millis();
        server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Surf data fetched successfully\"}");
        Serial.println("✅ Manual fetch successful");
    } else {
        server.send(500, "application/json", "{\"status\":\"error\",\"message\":\"Failed to fetch surf data\"}");
        Serial.println("❌ Manual fetch failed");
    }
}

// ---------------------------- Surf Data Fetching (UNCHANGED) ----------------------------

bool fetchSurfDataFromServer() {
    String apiServer = serverDiscovery.getApiServer();
    if (apiServer.length() == 0) {
        Serial.println("❌ No API server available for fetching data");
        return false;
    }

    HTTPClient http;
    WiFiClientSecure client;

    String url = "https://" + apiServer + "/api/arduino/" + String(ARDUINO_ID) + "/data";
    Serial.println("🌐 Fetching surf data from: " + url);

    client.setInsecure();

    http.begin(client, url);
    http.setTimeout(15000);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        http.end();

        Serial.println("📥 Received surf data from server");
        return processSurfData(payload);
    } else {
        Serial.printf("❌ HTTP error fetching surf data: %d (%s)\n", httpCode, http.errorToString(httpCode).c_str());
        http.end();
        return false;
    }
}

// ---------------------------- Surf Data Processing (UNCHANGED) ----------------------------

bool processSurfData(const String &jsonData) {
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, jsonData);

    if (error) {
        Serial.printf("❌ JSON parsing failed: %s\n", error.c_str());
        return false;
    }

    // Extract values using the correct keys sent by the server
    int wave_height_cm = doc["wave_height_cm"] | 0;
    float wave_period_s = doc["wave_period_s"] | 0.0;
    int wind_speed_mps = doc["wind_speed_mps"] | 0;
    int wind_direction_deg = doc["wind_direction_deg"] | 0;
    int wave_threshold_cm = doc["wave_threshold_cm"] | 100;
    int wind_speed_threshold_knots = doc["wind_speed_threshold_knots"] | 15;
    bool quiet_hours_active = doc["quiet_hours_active"] | false;
    String led_theme = doc["led_theme"] | "day";

    // Update theme if changed
    if (led_theme != currentTheme) {
        currentTheme = led_theme;
        Serial.printf("🎨 LED theme updated to: %s\n", currentTheme.c_str());
    }

    Serial.println("🌊 Surf Data Received:");
    Serial.printf("   Wave Height: %d cm\n", wave_height_cm);
    Serial.printf("   Wave Period: %.1f s\n", wave_period_s);
    Serial.printf("   Wind Speed: %d m/s\n", wind_speed_mps);
    Serial.printf("   Wind Direction: %d°\n", wind_direction_deg);
    Serial.printf("   Wave Threshold: %d cm\n", wave_threshold_cm);
    Serial.printf("   Wind Speed Threshold: %d knots\n", wind_speed_threshold_knots);
    Serial.printf("   Quiet Hours Active: %s\n", quiet_hours_active ? "true" : "false");
    Serial.printf("   LED Theme: %s\n", currentTheme.c_str());

    // Calculate LED counts for logging
    int windSpeedLEDs = ledMapping.calculateWindLEDs(wind_speed_mps);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(wave_height_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wave_period_s);

    // Log timestamp and LED counts
    Serial.printf("⏰ Timestamp: %lu ms (uptime)\n", millis());
    Serial.printf("💡 LEDs Active - Wind: %d, Wave: %d, Period: %d\n", windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs);

    // *** DECOUPLED ARCHITECTURE: Only update state, don't trigger display ***
    // Store all data in global state (converting height and threshold to meters for consistency)
    lastSurfData.waveHeight = wave_height_cm / 100.0;
    lastSurfData.wavePeriod = wave_period_s;
    lastSurfData.windSpeed = wind_speed_mps;
    lastSurfData.windDirection = wind_direction_deg;
    lastSurfData.waveThreshold = wave_threshold_cm / 100.0;  // Convert cm to meters for consistent comparison
    lastSurfData.windSpeedThreshold = wind_speed_threshold_knots;
    lastSurfData.quietHoursActive = quiet_hours_active;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    lastSurfData.needsDisplayUpdate = true;  // Signal to loop() that display needs refresh

    return true;
}


void updateSurfDisplay() {
    // *** DECOUPLED ARCHITECTURE: Read from global state instead of parameters ***
    if (!lastSurfData.dataReceived) {
        Serial.println("⚠️ No surf data available to display");
        return;
    }

    // Convert stored data back to the units needed for display
    int waveHeight_cm = static_cast<int>(lastSurfData.waveHeight * 100);
    float wavePeriod = lastSurfData.wavePeriod;
    int windSpeed = static_cast<int>(lastSurfData.windSpeed);
    int windDirection = lastSurfData.windDirection;
    int waveThreshold_cm = static_cast<int>(lastSurfData.waveThreshold * 100);
    int windSpeedThreshold_knots = lastSurfData.windSpeedThreshold;

    // Check for quiet hours - show only the highest LED that would normally be on
    if (lastSurfData.quietHoursActive) {
        FastLED.setBrightness(BRIGHTNESS * 0.3); // Dim to 30% during quiet hours

        // Calculate how many LEDs would be on during daytime
        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

        // Turn off all LEDs first
        FastLED.clear();

        // *** MODIFIED: Light only the top LED using correct indices ***
        // Wind: top = lowest index in reverse strip (LED 18 if 11 LEDs active)
        if (windSpeedLEDs > 0) {
            int topWindIndex = WIND_SPEED_START - windSpeedLEDs;
            leds[topWindIndex] = getWindSpeedColor(currentTheme);
        }
        // Wave height: top = highest index (LED 14 if 14 LEDs active)
        if (waveHeightLEDs > 0) {
            int topWaveIndex = WAVE_HEIGHT_START + waveHeightLEDs - 1;
            leds[topWaveIndex] = getWaveHeightColor(currentTheme);
        }
        // Wave period: top = highest index (LED 46 if 14 LEDs active)
        if (wavePeriodLEDs > 0) {
            int topPeriodIndex = WAVE_PERIOD_START + wavePeriodLEDs - 1;
            leds[topPeriodIndex] = getWavePeriodColor(currentTheme);
        }

        FastLED.show();
        Serial.println("🌙 Quiet hours: Only top LEDs active");
        return;
    }

    // Calculate LED counts based on surf data using centralized mapping configuration
    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

    // Set wind direction indicator
    setWindDirection(windDirection);

    // Set wave period LEDs with theme color
    updateWavePeriodLEDs(wavePeriodLEDs, getWavePeriodColor(currentTheme));

    // Apply threshold logic for wind speed and wave height
    applyWindSpeedThreshold(windSpeedLEDs, windSpeed, windSpeedThreshold_knots);
    applyWaveHeightThreshold(waveHeightLEDs, waveHeight_cm, waveThreshold_cm);

    FastLED.show();

    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d° [Wave Threshold: %dcm, Wind Threshold: %dkts]\n",
                  windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, windDirection, waveThreshold_cm, windSpeedThreshold_knots);
}


// ---------------------------- Setup Function ----------------------------

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌊 ========================================");
    Serial.println("🌊 SURF LAMP - SINGLE STRIP VERSION");
    Serial.println("🌊 ========================================");
    Serial.printf("🔧 Arduino ID: %d\n", ARDUINO_ID);
    Serial.printf("📍 LED Configuration:\n");
    Serial.printf("   Wave Height (Right): LEDs %d-%d (%d total)\n", WAVE_HEIGHT_START, WAVE_HEIGHT_END, WAVE_HEIGHT_LENGTH);
    Serial.printf("   Wave Period (Left):  LEDs %d-%d (%d total)\n", WAVE_PERIOD_START, WAVE_PERIOD_END, WAVE_PERIOD_LENGTH);
    Serial.printf("   Wind Speed (Center): LEDs %d-%d (%d total, REVERSE)\n", WIND_SPEED_START, WIND_SPEED_END, WIND_SPEED_LENGTH);
    Serial.printf("   Status LED:  %d\n", STATUS_LED_INDEX);
    Serial.printf("   Wind Dir LED: %d\n", WIND_DIRECTION_INDEX);
    Serial.printf("   Total LEDs:   %d\n", TOTAL_LEDS);
    Serial.println();

    // Initialize button
    pinMode(BUTTON_PIN, INPUT_PULLUP);

    // *** CHANGE: Initialize single LED strip ***
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    Serial.println("💡 Single LED strip initialized");

    // LED startup test
    performLEDTest();

    // Initialize preferences
    preferences.begin("wifi-creds", false);

    // Visual feedback: Green LED for 10 seconds - user can press button during this time
    Serial.println("🟢 Green LED active - press BOOT button within 10 seconds to enter config mode");
    fill_solid(leds, TOTAL_LEDS, CRGB::Green);
    FastLED.show();

    unsigned long greenStart = millis();

    // Check if button was pressed in previous boot
    checkButtonAndEnterAP();

    // Wait 10 seconds for button press
    while (millis() - greenStart < 10000) {
        if (digitalRead(BUTTON_PIN) == LOW) {
            set_config_mode_and_restart();
            break;
        }
        delay(10);
    }

    // Turn off green LEDs
    fill_solid(leds, TOTAL_LEDS, CRGB::Black);
    FastLED.show();
    Serial.println("⏱️ Button press window closed");

    // Attempt WiFi connection
    if (!connectToWiFi()) {
        Serial.println("🔧 Starting configuration mode...");
        startConfigMode();
    } else {
        Serial.println("🚀 Surf Lamp ready for operation!");
        Serial.printf("📍 Device accessible at: http://%s\n", WiFi.localIP().toString().c_str());

        // Try to fetch surf data immediately on startup
        Serial.println("🔄 Attempting initial surf data fetch...");
        if (fetchSurfDataFromServer()) {
            Serial.println("✅ Initial surf data fetch successful");
            lastDataFetch = millis();
        } else {
            Serial.println("⚠️ Initial surf data fetch failed, will retry later");
        }
    }
}

// ---------------------------- Main Loop (UNCHANGED) ----------------------------

void loop() {
    // Check for button press to enter config mode (check every 1 second)
    static unsigned long lastButtonCheck = 0;
    unsigned long now = millis();

    if (now - lastButtonCheck >= 1000) {
        lastButtonCheck = now;
        if (digitalRead(BUTTON_PIN) == LOW) {
            Serial.println("🔘 Button pressed during runtime - setting config mode flag");
            preferences.begin("wifi-creds", false);
            preferences.putInt("button_pressed", 1);
            preferences.end();
            delay(500);
            Serial.println("🔄 Restarting to enter configuration mode...");
            ESP.restart();
        }
    }

    // Handle HTTP requests
    server.handleClient();

    // Handle configuration mode timeout
    handleAPTimeout();

    // WiFi status management
    if (WiFi.status() != WL_CONNECTED) {
        if (!configure_wifi) {
            blinkRedLED();
            static unsigned long lastReconnectAttempt = 0;
            if (millis() - lastReconnectAttempt > 30000) { // Try every 30 seconds
                Serial.println("🔄 Attempting WiFi reconnection...");
                connectToWiFi();
                lastReconnectAttempt = millis();
            }
        } else {
            blinkYellowLED(); // Configuration mode
        }
    } else {
        // Connected and operational
        if (configure_wifi) {
            configure_wifi = false;
            Serial.println("✅ Exited configuration mode");
        }

        // Periodically fetch surf data from discovered server
        if (millis() - lastDataFetch > FETCH_INTERVAL) {
            Serial.println("🔄 Time to fetch new surf data...");
            if (fetchSurfDataFromServer()) {
                Serial.println("✅ Surf data fetch successful");
                lastDataFetch = millis();
            } else {
                Serial.println("❌ Surf data fetch failed, will retry later");
                lastDataFetch = millis(); // Still update to avoid rapid retries
            }
        }

        // *** DECOUPLED ARCHITECTURE: Check if display needs update ***
        if (lastSurfData.needsDisplayUpdate) {
            Serial.println("🔄 Detected state change, updating display...");
            updateSurfDisplay();
            lastSurfData.needsDisplayUpdate = false;  // Clear the flag
        }

        // Update blinking LEDs if any thresholds are exceeded
        updateBlinkingAnimation();

        // Status indication based on data freshness
        if (lastSurfData.dataReceived && (millis() - lastSurfData.lastUpdate < 1800000)) { // 30 minutes
            blinkGreenLED(); // Fresh data
        } else {
            blinkStatusLED(CRGB::Blue); // No recent data
        }
    }

    delay(5); // Small delay to prevent excessive CPU usage
}
