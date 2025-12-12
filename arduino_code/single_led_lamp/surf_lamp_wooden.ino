/*
 * SURF LAMP - WOODEN LAMP VERSION
 *
 * Hardware: Single continuous WS2812B LED strip wrapped to appear as 3 visual strips
 *
 * LED MAPPING (Wooden Lamp Configuration):
 * - Strip 1 (Wave Height - Right): LEDs 11-49 (39 total, bottom-up)
 * - Strip 2 (Wave Period - Left):  LEDs 107-145 (39 total, bottom-up)
 * - Strip 3 (Wind Speed - Center): LEDs 101-59 (43 total, REVERSE - bottom 101 to top 59)
 *
 * Special LEDs:
 * - LED 101: Status indicator (blue/green/red/yellow for WiFi/data status)
 * - LED 59: Wind direction indicator (green/yellow/red/blue for N/E/S/W)
 *
 * CHANGES FROM SINGLE-STRIP VERSION:
 * - Larger LED strip (146 total vs 47)
 * - More LEDs per strip (38-43 vs 14)
 * - Different LED mapping indices
 * - Adjusted scaling factors for wind speed and wave height
 * - ALL OTHER LOGIC IDENTICAL (WiFi, server, thresholds, themes, etc.)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <WiFiManager.h>  // WiFiManager library for robust WiFi configuration
#include <ArduinoJson.h>
#include <FastLED.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

#include "ServerDiscovery.h"

// Global instances
ServerDiscovery serverDiscovery;
WiFiManager wifiManager;

// ---------------------------- Configuration ----------------------------
#define BUTTON_PIN 0  // ESP32 boot button

// *** WOODEN LAMP CONFIGURATION ***
#define LED_PIN 2            // GPIO 2 - Single continuous strip
#define TOTAL_LEDS 146       // Total LEDs in the strip (0-145)
#define BRIGHTNESS 90        //macro for global brighness configuration
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

// LED STRIP SECTION MAPPING
// Wave Height (Right Side) - Forward direction (11→49)
#define WAVE_HEIGHT_START 11
#define WAVE_HEIGHT_END 49
#define WAVE_HEIGHT_LENGTH 39

// Wave Period (Left Side) - Forward direction (107→145)
#define WAVE_PERIOD_START 107
#define WAVE_PERIOD_END 145
#define WAVE_PERIOD_LENGTH 39

// Wind Speed (Center) - REVERSE direction (101→59)
#define WIND_SPEED_START 101     // Bottom LED (also status LED)
#define WIND_SPEED_END 59        // Top LED (also wind direction LED)
#define WIND_SPEED_LENGTH 43     // Total including status + direction

// Special LEDs
#define STATUS_LED_INDEX 101     // Status indicator (bottom of wind strip)
#define WIND_DIRECTION_INDEX 59  // Wind direction (top of wind strip)

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
const int ARDUINO_ID = 2;  // ✨ Wooden surf lamp

// Global Variables
WebServer server(80);
unsigned long lastDataFetch = 0;
const unsigned long FETCH_INTERVAL = 780000; // 13 minutes

// WiFi reconnection tracking
const int MAX_WIFI_RETRIES = 5;
int reconnectAttempts = 0;
unsigned long lastReconnectAttempt = 0;

// WiFi diagnostics - stores last connection failure reason
String lastWiFiError = "";
uint8_t lastDisconnectReason = 0;

// Blinking state variables
unsigned long lastBlinkUpdate = 0;
const unsigned long BLINK_INTERVAL = 1500; // 1.5 seconds for slow smooth blink
float blinkPhase = 0.0; // Phase for smooth sine wave blinking

// *** SINGLE LED ARRAY ***
CRGB leds[TOTAL_LEDS];

// Last received surf data (for status reporting)
// CRITICAL: waveHeight and waveThreshold MUST both be float and both in METERS
// to ensure proper threshold comparison in updateBlinkingAnimation()
struct SurfData {
    float waveHeight = 0.0;        // Stored in METERS (converted from cm via /100.0)
    float wavePeriod = 0.0;
    float windSpeed = 0.0;
    int windDirection = 0;
    float waveThreshold = 1.0;     // Stored in METERS (converted from cm via /100.0) - MUST be float!
    int windSpeedThreshold = 15;
    bool quietHoursActive = false;
    bool offHoursActive = false;
    unsigned long lastUpdate = 0;
    bool dataReceived = false;
    bool needsDisplayUpdate = false;  // Flag to trigger display refresh
} lastSurfData;


// ---------------------------- Wave Animation Configuration ----------------------------

struct WaveConfig {
    // User-adjustable parameters
    uint8_t brightness_min_percent = 50;   // Minimum brightness during wave (0-100%)
    uint8_t brightness_max_percent = 110;  // Maximum brightness during wave (0-100%)
    float wave_length_side = 10.0;         // Wave length for side strips (LEDs per cycle) - adjusted for longer strips
    float wave_length_center = 12.0;       // Wave length for center strip (LEDs per cycle) - adjusted for longer strips
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
    // User-adjustable parameters (WOODEN LAMP SCALING)
    float wind_scale_numerator = 40.0;      // Wind speed scaling: maps 0-13 m/s to 0-40 LEDs (41 usable LEDs in wooden lamp)
    float wind_scale_denominator = 13.0;
    float mps_to_knots_factor = 1.94384;    // Conversion constant: m/s to knots
    uint8_t wave_height_divisor = 10;       // Wave height scaling: 10cm per LED (allows up to 3.9m on 39 LEDs)
    float threshold_brightness_multiplier = 1.4;  // Brightness boost when threshold exceeded (60% brighter)

    // Helper: Calculate wind speed LEDs from m/s (used by all wind speed calculations)
    int calculateWindLEDs(float windSpeed_mps) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            WIND_SPEED_LENGTH - 2  // Reserve LED 101 for status, LED 59 for wind direction
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


// ---------------------------- WiFi Diagnostic Functions ----------------------------

/**
 * Convert WiFi disconnect reason code to human-readable message
 * Based on ESP-IDF wifi_err_reason_t enum
 */
String getDisconnectReasonText(uint8_t reason) {
    switch(reason) {
        case 1:  return "Unspecified error";
        case 2:  return "Authentication expired - wrong password or security mode";
        case 3:  return "Deauthenticated (AP kicked device)";
        case 4:  return "Disassociated (inactive)";
        case 5:  return "Too many devices connected to AP";
        case 6:  return "Wrong password or WPA/WPA2 mismatch";
        case 7:  return "Wrong password";
        case 8:  return "Association expired (timeout)";
        case 15: return "4-way handshake timeout - likely wrong password";
        case 23: return "Too many authentication failures";
        case 201: return "Beacon timeout - AP disappeared or weak signal";
        case 202: return "No AP found with this SSID";
        case 203: return "Authentication failed - check password and security mode";
        case 204: return "Association failed - AP rejected connection";
        case 205: return "Handshake timeout - wrong password or security mismatch";
        default: return "Unknown error (code: " + String(reason) + ")";
    }
}

/**
 * WiFi event handler - captures connection and disconnection events with reason codes
 */
void WiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    switch(event) {
        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("✅ WiFi connected to AP");
            lastWiFiError = "";  // Clear error on success
            break;

        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            Serial.printf("✅ Got IP: %s\n", WiFi.localIP().toString().c_str());
            break;

        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            lastDisconnectReason = info.wifi_sta_disconnected.reason;
            lastWiFiError = getDisconnectReasonText(lastDisconnectReason);
            Serial.printf("❌ WiFi disconnected - Reason: %s\n", lastWiFiError.c_str());
            break;

        default:
            break;
    }
}

/**
 * Pre-scan WiFi diagnostics - checks if SSID exists, signal strength, and security mode
 * Returns detailed error message if issues detected, empty string if OK
 */
String diagnoseSSID(const char* targetSSID) {
    Serial.printf("🔍 Scanning for SSID: %s\n", targetSSID);

    int numNetworks = WiFi.scanNetworks();

    if (numNetworks == 0) {
        return "No WiFi networks found. Check if router is powered on and in range.";
    }

    Serial.printf("📡 Found %d networks\n", numNetworks);

    // Look for target SSID
    int bestSignalIndex = -1;
    int bestRSSI = -127;

    for (int i = 0; i < numNetworks; i++) {
        String ssid = WiFi.SSID(i);
        int rssi = WiFi.RSSI(i);
        wifi_auth_mode_t authMode = (wifi_auth_mode_t)WiFi.encryptionType(i);
        int channel = WiFi.channel(i);

        Serial.printf("   %d: %s (Ch %d, %d dBm, Auth %d)\n", i, ssid.c_str(), channel, rssi, authMode);

        if (ssid == targetSSID) {
            if (rssi > bestRSSI) {
                bestRSSI = rssi;
                bestSignalIndex = i;
            }
        }
    }

    if (bestSignalIndex == -1) {
        // SSID not found - most common user error
        return String("Network '") + targetSSID + "' not found. Check:\n" +
               "• Is SSID typed correctly (case-sensitive)?\n" +
               "• Is router's 2.4GHz band enabled? (ESP32 doesn't support 5GHz)\n" +
               "• Is router in range?";
    }

    // Found the network - check signal strength
    wifi_auth_mode_t authMode = (wifi_auth_mode_t)WiFi.encryptionType(bestSignalIndex);
    int channel = WiFi.channel(bestSignalIndex);

    Serial.printf("✅ Found target network:\n");
    Serial.printf("   Signal: %d dBm\n", bestRSSI);
    Serial.printf("   Channel: %d\n", channel);
    Serial.printf("   Security: %d\n", authMode);

    // Check signal strength
    if (bestRSSI < -85) {
        return String("Weak signal (") + bestRSSI + " dBm). Move lamp closer to router or use WiFi extender.";
    }

    // Check channel (ESP32 supports 1-13, some routers use 12-14 which may not work everywhere)
    if (channel > 11) {
        Serial.printf("⚠️ Warning: Channel %d may not be supported in all regions\n", channel);
    }

    // Check security mode
    if (authMode == WIFI_AUTH_WPA3_PSK) {
        return "Router uses WPA3 security. ESP32 requires WPA2. Change router to WPA2/WPA3 mixed mode.";
    }

    // All checks passed
    return "";
}

// ---------------------------- WiFiManager Callback Functions ----------------------------

void configModeCallback(WiFiManager *myWiFiManager) {
    Serial.println("🔧 Config mode started");
    Serial.println("📱 AP: SurfLamp-Setup");

    // Blue LEDs for configuration mode
    fill_solid(leds, TOTAL_LEDS, CRGB::Blue);
    FastLED.show();
}

void saveConfigCallback() {
    Serial.println("✅ Config saved!");
}

/**
 * Custom save parameters callback - runs BEFORE WiFiManager tries to connect
 * Performs pre-scan diagnostics and provides immediate feedback
 */
void saveParamsCallback() {
    Serial.println("💾 Credentials saved, performing diagnostics...");

    // Get the SSID that was just saved (WiFiManager stores it)
    String ssid = WiFi.SSID();
    if (ssid.length() == 0) {
        // WiFiManager hasn't connected yet, can't get SSID from WiFi object
        Serial.println("⏳ Will diagnose after connection attempt");
        return;
    }

    String diagnostic = diagnoseSSID(ssid.c_str());
    if (diagnostic.length() > 0) {
        lastWiFiError = diagnostic;
        Serial.printf("⚠️ Diagnostic warning: %s\n", diagnostic.c_str());
    }
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

// ---------------------------- LED Control Functions (WOODEN LAMP MAPPING) ----------------------------

// *** Wave Height Strip (LEDs 11-49, forward) ***
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

// *** Wave Height Strip with Blinking (threshold exceeded) ***
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

// *** Wave Period Strip (LEDs 107-145, forward) ***
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

// *** Wind Speed Strip (LEDs 101-59, REVERSE) ***
void updateWindSpeedLEDs(int numActiveLeds, CHSV color) {
    // Wind strip runs BACKWARDS: 101 (bottom) -> 59 (top)
    // Skip LED 101 (status) and LED 59 (wind direction)

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_START - i;  // Count backwards from 101
        int ledPosition = i - 1;  // Logical position (0-based)

        if (ledPosition < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

// *** Wind Speed Strip with Blinking (threshold exceeded) ***
void updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor) {
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    // Wind strip runs BACKWARDS: 101 -> 59
    // Skip LED 101 (status) and LED 59 (wind direction)

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

// *** Threshold functions ***
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
    Serial.println("   Testing Wave Height strip (LEDs 11-49)...");
    updateWaveHeightLEDs(WAVE_HEIGHT_LENGTH, CHSV(160, 255, 255));  // Blue
    FastLED.show();
    delay(1000);

    Serial.println("   Testing Wave Period strip (LEDs 107-145)...");
    updateWavePeriodLEDs(WAVE_PERIOD_LENGTH, CHSV(60, 255, 255));   // Yellow
    FastLED.show();
    delay(1000);

    Serial.println("   Testing Wind Speed strip (LEDs 101-59)...");
    updateWindSpeedLEDs(WIND_SPEED_LENGTH - 2, CHSV(0, 50, 255));   // White
    FastLED.show();
    delay(1000);

    Serial.println("   Testing status LED (LED 101)...");
    leds[STATUS_LED_INDEX] = CRGB::Green;
    FastLED.show();
    delay(1000);

    Serial.println("   Testing wind direction LED (LED 59)...");
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

// ---------------------------- HTTP Server Endpoints ----------------------------

void handleWiFiDiagnostics() {
    DynamicJsonDocument doc(1024);

    doc["current_ssid"] = WiFi.SSID();
    doc["connected"] = WiFi.status() == WL_CONNECTED;
    doc["ip_address"] = WiFi.localIP().toString();
    doc["signal_strength_dbm"] = WiFi.RSSI();
    doc["last_error"] = lastWiFiError;
    doc["last_disconnect_reason_code"] = lastDisconnectReason;

    // If connected, scan and show network details
    if (WiFi.status() == WL_CONNECTED) {
        String ssid = WiFi.SSID();
        int numNetworks = WiFi.scanNetworks();

        for (int i = 0; i < numNetworks; i++) {
            if (WiFi.SSID(i) == ssid) {
                doc["channel"] = WiFi.channel(i);
                doc["security_type"] = WiFi.encryptionType(i);
                break;
            }
        }
    }

    String response;
    serializeJson(doc, response);

    server.send(200, "application/json", response);
    Serial.println("🔍 WiFi diagnostics request served");
}

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

    // WiFi diagnostics endpoint
    server.on("/api/wifi-diagnostics", HTTP_GET, handleWiFiDiagnostics);

    server.on("/api/discovery-test", HTTP_GET, handleDiscoveryTest);


    server.begin();
    Serial.println("🌐 HTTP server started with endpoints:");
    Serial.println("   POST /api/update          - Receive surf data");
    Serial.println("   GET  /api/discovery-test  - Test server discovery");
    Serial.println("   GET  /api/status          - Device status");
    Serial.println("   GET  /api/test            - Connection test");
    Serial.println("   GET  /api/led-test        - LED test");
    Serial.println("   GET  /api/info            - Device information");
    Serial.println("   GET  /api/fetch           - Manual surf data fetch");
    Serial.println("   GET  /api/wifi-diagnostics - WiFi connection diagnostics");
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
    statusDoc["firmware_version"] = "2.0.0-wooden-lamp";

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

    infoDoc["device_name"] = "Surf Lamp (Wooden)";
    infoDoc["arduino_id"] = ARDUINO_ID;
    infoDoc["model"] = ESP.getChipModel();
    infoDoc["revision"] = ESP.getChipRevision();
    infoDoc["cores"] = ESP.getChipCores();
    infoDoc["flash_size"] = ESP.getFlashChipSize();
    infoDoc["psram_size"] = ESP.getPsramSize();
    infoDoc["firmware_version"] = "2.0.0-wooden-lamp";
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
    bool off_hours_active = doc["off_hours_active"] | false;
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
    lastSurfData.offHoursActive = off_hours_active;
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

    // OFF HOURS: Lamp completely off (top priority)
    if (lastSurfData.offHoursActive) {
        FastLED.clear();
        FastLED.show();
        Serial.println("🔴 Off hours active - lamp turned OFF");
        return;
    }

    // Convert stored data back to the units needed for display
    int waveHeight_cm = static_cast<int>(lastSurfData.waveHeight * 100);
    float wavePeriod = lastSurfData.wavePeriod;
    int windSpeed = static_cast<int>(lastSurfData.windSpeed);
    int windDirection = lastSurfData.windDirection;
    int waveThreshold_cm = static_cast<int>(lastSurfData.waveThreshold * 100);
    int windSpeedThreshold_knots = lastSurfData.windSpeedThreshold;

    // QUIET HOURS: Only top LED of each strip (secondary priority)
    if (lastSurfData.quietHoursActive) {
        FastLED.setBrightness(BRIGHTNESS * 0.3); // Dim to 30% during quiet hours

        // Calculate how many LEDs would be on during daytime
        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

        // Turn off all LEDs first
        FastLED.clear();

        // Light only the top LED using correct indices
        // Wind: top = lowest index in reverse strip
        if (windSpeedLEDs > 0) {
            int topWindIndex = WIND_SPEED_START - windSpeedLEDs;
            leds[topWindIndex] = getWindSpeedColor(currentTheme);
        }
        // Wave height: top = highest index
        if (waveHeightLEDs > 0) {
            int topWaveIndex = WAVE_HEIGHT_START + waveHeightLEDs - 1;
            leds[topWaveIndex] = getWaveHeightColor(currentTheme);
        }
        // Wave period: top = highest index
        if (wavePeriodLEDs > 0) {
            int topPeriodIndex = WAVE_PERIOD_START + wavePeriodLEDs - 1;
            leds[topPeriodIndex] = getWavePeriodColor(currentTheme);
        }

        FastLED.show();
        Serial.println("🌙 Quiet hours: Only top LEDs active");
        return;
    }

    // NORMAL MODE: Clear all LEDs first (including hidden LEDs between strips)
    FastLED.clear();

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
    Serial.println("🌊 SURF LAMP - WOODEN LAMP VERSION");
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

    // Initialize single LED strip
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    Serial.println("💡 Single LED strip initialized");

    // LED startup test
    performLEDTest();

    // Register WiFi event handlers BEFORE WiFiManager starts
    WiFi.onEvent(WiFiEvent);
    Serial.println("📡 WiFi event handlers registered");

    // WiFiManager setup with enhanced diagnostics
    wifiManager.setAPCallback(configModeCallback);
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setSaveParamsCallback(saveParamsCallback);  // NEW: Diagnostics callback
    wifiManager.setConfigPortalTimeout(0); // No timeout - wait indefinitely

    // Visual feedback: Blue LEDs during any config
    fill_solid(leds, TOTAL_LEDS, CRGB::Blue);
    FastLED.show();

    // Auto-connect with retry logic and enhanced diagnostics
    bool connected = false;
    for (int attempt = 1; attempt <= MAX_WIFI_RETRIES && !connected; attempt++) {
        Serial.printf("🔄 WiFi connection attempt %d of %d\n", attempt, MAX_WIFI_RETRIES);

        // Set timeout: 30 seconds for retry attempts, indefinite for last attempt
        if (attempt < MAX_WIFI_RETRIES) {
            wifiManager.setConfigPortalTimeout(30); // 30 second timeout per attempt
        } else {
            wifiManager.setConfigPortalTimeout(0); // Last attempt: wait indefinitely in config portal
        }

        // Inject error message into portal if we have one
        if (lastWiFiError.length() > 0) {
            String customHTML = "<div style='background:#ff4444;color:white;padding:10px;margin:10px 0;border-radius:5px;'>";
            customHTML += "<strong>❌ Connection Failed</strong><br>";
            customHTML += lastWiFiError;
            customHTML += "</div>";
            wifiManager.setCustomHeadElement(customHTML.c_str());
        }

        connected = wifiManager.autoConnect("SurfLamp-Setup", "surf123456");

        // If connection failed, run diagnostics to determine WHY
        if (!connected) {
            Serial.println("❌ Connection failed - running diagnostics...");

            // Get SSID from WiFiManager (it stores the last attempted SSID)
            String attemptedSSID = WiFi.SSID();
            if (attemptedSSID.length() == 0) {
                Serial.println("⚠️ No SSID stored - user may not have entered credentials");
            } else {
                Serial.printf("🔍 Diagnosing connection to: %s\n", attemptedSSID.c_str());

                // Run pre-scan diagnostics
                String diagnostic = diagnoseSSID(attemptedSSID.c_str());

                if (diagnostic.length() > 0) {
                    // Store for display in portal
                    lastWiFiError = diagnostic;
                    Serial.println("🔴 DIAGNOSTIC RESULT:");
                    Serial.println(diagnostic);
                    Serial.println("🔴 ==========================================");
                } else if (lastDisconnectReason != 0) {
                    // Store disconnect reason
                    Serial.println("🔴 DISCONNECT REASON:");
                    Serial.println(lastWiFiError);
                    Serial.println("🔴 ==========================================");
                }
            }

            if (attempt < MAX_WIFI_RETRIES) {
                Serial.println("⏳ Waiting 5 seconds before retry...");
                delay(5000);
            }
        }
    }

    if (!connected) {
        Serial.println("❌ Failed to connect after 5 attempts");
        Serial.println("📋 Final diagnostic summary:");
        Serial.printf("   Last SSID attempted: %s\n", WiFi.SSID().c_str());
        Serial.printf("   Last error: %s\n", lastWiFiError.c_str());
        Serial.printf("   Disconnect reason code: %d\n", lastDisconnectReason);
        Serial.println("🔄 Restarting to config portal...");
        delay(3000);
        ESP.restart();
    }

    Serial.println("✅ WiFi Connected!");
    Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());

    setupHTTPEndpoints();

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

// ---------------------------- Main Loop (UNCHANGED) ----------------------------

void loop() {
    // Check for button press to reset WiFi (check every 1 second)
    static unsigned long lastButtonCheck = 0;
    unsigned long now = millis();

    if (now - lastButtonCheck >= 1000) {
        lastButtonCheck = now;
        if (digitalRead(BUTTON_PIN) == LOW) {
            Serial.println("🔘 Button pressed - resetting WiFi");
            wifiManager.resetSettings(); // Wipe credentials
            delay(500);
            ESP.restart();
        }
    }

    // Handle HTTP requests
    server.handleClient();

    // WiFi status management
    if (WiFi.status() != WL_CONNECTED) {
        blinkRedLED();

        // Try to reconnect every 10 seconds
        if (now - lastReconnectAttempt > 10000) {
            lastReconnectAttempt = now;
            reconnectAttempts++;

            Serial.printf("🔄 WiFi disconnected - reconnection attempt %d of %d\n",
                          reconnectAttempts, MAX_WIFI_RETRIES);
            WiFi.reconnect();

            if (reconnectAttempts >= MAX_WIFI_RETRIES) {
                Serial.println("❌ Failed to reconnect after 5 attempts - restarting for config portal");
                delay(1000);
                ESP.restart(); // Will trigger config portal in setup
            }
        }
    } else {
        // Connected and operational

        // Reset reconnect counter when connected
        if (reconnectAttempts > 0) {
            Serial.println("✅ WiFi reconnected successfully");
            reconnectAttempts = 0;
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