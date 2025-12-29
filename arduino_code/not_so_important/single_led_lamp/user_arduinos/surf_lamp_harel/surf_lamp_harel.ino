/*
 * SURF LAMP - HAREL'S VERSION (ID 3)
 *
 * Hardware: Single continuous WS2812B LED strip wrapped to appear as 3 visual strips
 *
 * LED MAPPING (Harel's Configuration):
 * - Strip 1 (Wave Height - Right): LEDs 4-28 (25 total, bottom-up)
 * - Strip 2 (Wave Period - Left):  LEDs 65-89 (25 total, bottom-up)
 * - Strip 3 (Wind Speed - Center): LEDs 60-35 (26 total, REVERSE - bottom 60 to top 35)
 *
 * Special LEDs:
 * - LED 60: Status indicator (blue/green/red/yellow for WiFi/data status)
 * - LED 35: Wind direction indicator (green/yellow/red/blue for N/E/S/W)
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

// *** HAREL LAMP CONFIGURATION ***
#define LED_PIN 2            // GPIO 2 - Single continuous strip
#define TOTAL_LEDS 150       // Total LEDs (increased to cover physical strip length if > 90)
#define BRIGHTNESS 90        // macro for global brightness configuration
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

// LED STRIP SECTION MAPPING
// Wave Height (Right Side) - Forward direction (4→28)
#define WAVE_HEIGHT_START 4
#define WAVE_HEIGHT_END 28
#define WAVE_HEIGHT_LENGTH 25

// Wave Period (Left Side) - Forward direction (65→89)
#define WAVE_PERIOD_START 65
#define WAVE_PERIOD_END 89
#define WAVE_PERIOD_LENGTH 25

// Wind Speed (Center) - REVERSE direction (60→35)
#define WIND_SPEED_START 60      // Bottom LED (also status LED)
#define WIND_SPEED_END 35        // Top LED (also wind direction LED)
#define WIND_SPEED_LENGTH 26     // Total including status + direction

// Special LEDs
#define STATUS_LED_INDEX 60      // Status indicator (bottom of wind strip)
#define WIND_DIRECTION_INDEX 35  // Wind direction (top of wind strip)

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
const int ARDUINO_ID = 3;  // ✨ Harel's surf lamp

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
    float wave_length_side = 10.0;         // Wave length for side strips (LEDs per cycle)
    float wave_length_center = 12.0;       // Wave length for center strip (LEDs per cycle)
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
    // User-adjustable parameters (HAREL LAMP SCALING)
    // Wind length 26. Usable = 26 - 2 = 24.
    // REQUIREMENTS: Max Wind 24 m/s, Max Wave 4.0m (400cm)
    float wind_scale_numerator = 24.0;      // Wind speed scaling: maps 0-24 m/s to 0-24 LEDs (1:1 mapping)
    float wind_scale_denominator = 24.0;
    float mps_to_knots_factor = 1.94384;    // Conversion constant: m/s to knots
    uint8_t wave_height_divisor = 16;       // Wave height scaling: 16cm per LED (allows up to 4.0m on 25 LEDs)
    float threshold_brightness_multiplier = 1.4;  // Brightness boost when threshold exceeded (60% brighter)

    // Helper: Calculate wind speed LEDs from m/s (used by all wind speed calculations)
    int calculateWindLEDs(float windSpeed_mps) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            WIND_SPEED_LENGTH - 2  // Reserve LED for status and wind direction
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

    // Check channel
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
 */
void saveParamsCallback() {
    Serial.println("💾 Credentials saved, performing diagnostics...");

    // Get the SSID that was just saved
    String ssid = WiFi.SSID();
    if (ssid.length() == 0) {
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

    // Update status LED at slower timing
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
void blinkYellowLED(){ blinkStatusLED(CRGB::Yellow);}

void clearLEDs() {
    FastLED.clear();
    FastLED.show();
}

void setStatusLED(CRGB color) {
    leds[STATUS_LED_INDEX] = color;
    FastLED.show();
}

// ---------------------------- LED Control Functions ----------------------------

// *** Wave Height Strip (LEDs 4-28, forward) ***
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

// *** Wave Period Strip (LEDs 65-89, forward) ***
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

// *** Wind Speed Strip (LEDs 60-35, REVERSE) ***
void updateWindSpeedLEDs(int numActiveLeds, CHSV color) {
    // Wind strip runs BACKWARDS: 60 (bottom) -> 35 (top)
    // Skip LED 60 (status) and LED 35 (wind direction)

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_START - i;  // Count backwards from 60
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

    // Wind strip runs BACKWARDS: 60 -> 35
    // Skip LED 60 (status) and LED 35 (wind direction)

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
    // Skip all LED updates during quiet hours
    if (lastSurfData.quietHoursActive) return;

    // Convert wind speed from m/s to knots for threshold comparison
    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed_mps);

    if (windSpeedInKnots < windSpeedThreshold_knots) {
        // NORMAL MODE
        updateWindSpeedLEDs(windSpeedLEDs, getWindSpeedColor(currentTheme));
    } else {
        // ALERT MODE
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
    }
}

void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm) {
    // Skip all LED updates during quiet hours
    if (lastSurfData.quietHoursActive) return;

    if (waveHeight_cm < waveThreshold_cm) {
        // NORMAL MODE
        updateWaveHeightLEDs(waveHeightLEDs, getWaveHeightColor(currentTheme));
    } else {
        // ALERT MODE
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
    }
}

void updateBlinkingAnimation() {
    // Only update blinking if we have valid surf data and thresholds are exceeded
    if (!lastSurfData.dataReceived) return;

    // Skip all blinking during quiet hours
    if (lastSurfData.quietHoursActive) return;

    // Update timing once per call
    unsigned long currentMillis = millis();
    if (currentMillis - lastBlinkUpdate >= 5) {
        blinkPhase += 0.0419;
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

    // Check if wave height threshold is exceeded
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

    // Wind direction color coding
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
    Serial.println("   Testing Wave Height strip (LEDs 4-28)...");
    updateWaveHeightLEDs(WAVE_HEIGHT_LENGTH, CHSV(160, 255, 255));  // Blue
    FastLED.show();
    delay(1000);

    Serial.println("   Testing Wave Period strip (LEDs 65-89)...");
    updateWavePeriodLEDs(WAVE_PERIOD_LENGTH, CHSV(60, 255, 255));   // Yellow
    FastLED.show();
    delay(1000);

    Serial.println("   Testing Wind Speed strip (LEDs 60-35)...");
    updateWindSpeedLEDs(WIND_SPEED_LENGTH - 2, CHSV(0, 50, 255));   // White
    FastLED.show();
    delay(1000);

    Serial.println("   Testing status LED (LED 60)...");
    leds[STATUS_LED_INDEX] = CRGB::Green;
    FastLED.show();
    delay(1000);

    Serial.println("   Testing wind direction LED (LED 35)...");
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
    server.on("/api/update", HTTP_POST, handleSurfDataUpdate);
    server.on("/api/status", HTTP_GET, handleStatusRequest);
    server.on("/api/test", HTTP_GET, handleTestRequest);
    server.on("/api/led-test", HTTP_GET, handleLEDTestRequest);
    server.on("/api/info", HTTP_GET, handleDeviceInfoRequest);
    server.on("/api/fetch", HTTP_GET, handleManualFetchRequest);
    server.on("/api/wifi-diagnostics", HTTP_GET, handleWiFiDiagnostics);
    server.on("/api/discovery-test", HTTP_GET, handleDiscoveryTest);

    server.begin();
    Serial.println("🌐 HTTP server started");
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
    statusDoc["uptime_ms"] = millis();
    statusDoc["firmware_version"] = "2.0.0-harel-lamp";

    // Last surf data
    statusDoc["last_surf_data"]["received"] = lastSurfData.dataReceived;
    statusDoc["last_surf_data"]["wave_height_m"] = lastSurfData.waveHeight;
    statusDoc["last_surf_data"]["wave_period_s"] = lastSurfData.wavePeriod;
    statusDoc["last_surf_data"]["wind_speed_mps"] = lastSurfData.windSpeed;
    statusDoc["last_surf_data"]["wind_direction_deg"] = lastSurfData.windDirection;
    statusDoc["last_surf_data"]["quiet_hours_active"] = lastSurfData.quietHoursActive;

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

    infoDoc["device_name"] = "Surf Lamp (Harel)";
    infoDoc["arduino_id"] = ARDUINO_ID;
    infoDoc["firmware_version"] = "2.0.0-harel-lamp";
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

// ---------------------------- Surf Data Fetching ----------------------------

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

// ---------------------------- Surf Data Processing ----------------------------

bool processSurfData(const String &jsonData) {
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, jsonData);

    if (error) {
        Serial.printf("❌ JSON parsing failed: %s\n", error.c_str());
        return false;
    }

    // Extract values
    int wave_height_cm = doc["wave_height_cm"] | 0;
    float wave_period_s = doc["wave_period_s"] | 0.0;
    int wind_speed_mps = doc["wind_speed_mps"] | 0;
    int wind_direction_deg = doc["wind_direction_deg"] | 0;
    int wave_threshold_cm = doc["wave_threshold_cm"] | 100;
    int wind_speed_threshold_knots = doc["wind_speed_threshold_knots"] | 15;
    bool quiet_hours_active = doc["quiet_hours_active"] | false;
    bool off_hours_active = doc["off_hours_active"] | false;
    String led_theme = doc["led_theme"] | "day";

    // Update theme
    if (led_theme != currentTheme) {
        currentTheme = led_theme;
        Serial.printf("🎨 LED theme updated to: %s\n", currentTheme.c_str());
    }

    Serial.println("🌊 Surf Data Received:");
    Serial.printf("   Wave Height: %d cm\n", wave_height_cm);
    Serial.printf("   Wave Period: %.1f s\n", wave_period_s);
    Serial.printf("   Wind Speed: %d m/s\n", wind_speed_mps);
    Serial.printf("   Wind Direction: %d°\n", wind_direction_deg);

    // Calculate LED counts for logging
    int windSpeedLEDs = ledMapping.calculateWindLEDs(wind_speed_mps);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(wave_height_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wave_period_s);

    // Log timestamp and LED counts
    Serial.printf("⏰ Timestamp: %lu ms (uptime)\n", millis());
    Serial.printf("💡 LEDs Active - Wind: %d, Wave: %d, Period: %d\n", windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs);

    // Store all data in global state
    lastSurfData.waveHeight = wave_height_cm / 100.0;
    lastSurfData.wavePeriod = wave_period_s;
    lastSurfData.windSpeed = wind_speed_mps;
    lastSurfData.windDirection = wind_direction_deg;
    lastSurfData.waveThreshold = wave_threshold_cm / 100.0;
    lastSurfData.windSpeedThreshold = wind_speed_threshold_knots;
    lastSurfData.quietHoursActive = quiet_hours_active;
    lastSurfData.offHoursActive = off_hours_active;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    lastSurfData.needsDisplayUpdate = true;

    return true;
}


void updateSurfDisplay() {
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
        FastLED.setBrightness(BRIGHTNESS * 0.3);

        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

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

        // Wind direction LED stays on during quiet hours (per shahar_rules.md)
        setWindDirection(windDirection);

        FastLED.show();
        Serial.println("🌙 Quiet hours: Only top LEDs active");
        return;
    }

    // NORMAL MODE
    FastLED.clear();

    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

    setWindDirection(windDirection);
    updateWavePeriodLEDs(wavePeriodLEDs, getWavePeriodColor(currentTheme));
    applyWindSpeedThreshold(windSpeedLEDs, windSpeed, windSpeedThreshold_knots);
    applyWaveHeightThreshold(waveHeightLEDs, waveHeight_cm, waveThreshold_cm);

    FastLED.show();

    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d°\n",
                  windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, windDirection);
}


// ---------------------------- Setup Function ----------------------------

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌊 ========================================");
    Serial.println("🌊 SURF LAMP - HAREL'S VERSION (ID 3)");
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

    performLEDTest();

    WiFi.onEvent(WiFiEvent);

    wifiManager.setAPCallback(configModeCallback);
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setSaveParamsCallback(saveParamsCallback);
    wifiManager.setConfigPortalTimeout(0);

    fill_solid(leds, TOTAL_LEDS, CRGB::Blue);
    FastLED.show();

    // Auto-connect
    bool connected = false;
    for (int attempt = 1; attempt <= MAX_WIFI_RETRIES && !connected; attempt++) {
        Serial.printf("🔄 WiFi connection attempt %d of %d\n", attempt, MAX_WIFI_RETRIES);

        if (attempt < MAX_WIFI_RETRIES) {
            wifiManager.setConfigPortalTimeout(30);
        } else {
            wifiManager.setConfigPortalTimeout(0);
        }

        if (lastWiFiError.length() > 0) {
            String customHTML = "<div style='background:#ff4444;color:white;padding:10px;margin:10px 0;border-radius:5px;'>";
            customHTML += "<strong>❌ Connection Failed</strong><br>";
            customHTML += lastWiFiError;
            customHTML += "</div>";
            wifiManager.setCustomHeadElement(customHTML.c_str());
        }

        connected = wifiManager.autoConnect("SurfLamp-Harel-Setup", "surf123456");

        if (!connected) {
            Serial.println("❌ Connection failed - running diagnostics...");
            // Diagnostics logic same as wooden...
            if (attempt < MAX_WIFI_RETRIES) {
                delay(5000);
            }
        }
    }

    if (!connected) {
        Serial.println("❌ Failed to connect after 5 attempts");
        delay(3000);
        ESP.restart();
    }

    Serial.println("✅ WiFi Connected!");
    Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());

    // Clear the blue setup LEDs so we start fresh
    clearLEDs();

    setupHTTPEndpoints();

    Serial.println("🚀 Surf Lamp ready for operation!");
    Serial.printf("📍 Device accessible at: http://%s\n", WiFi.localIP().toString().c_str());

    Serial.println("🔄 Attempting initial surf data fetch...");
    if (fetchSurfDataFromServer()) {
        Serial.println("✅ Initial surf data fetch successful");
        lastDataFetch = millis();
    } else {
        Serial.println("⚠️ Initial surf data fetch failed, will retry later");
    }
}

// ---------------------------- Main Loop ----------------------------

void loop() {
    static unsigned long lastButtonCheck = 0;
    unsigned long now = millis();

    if (now - lastButtonCheck >= 1000) {
        lastButtonCheck = now;
        if (digitalRead(BUTTON_PIN) == LOW) {
            Serial.println("🔘 Button pressed - resetting WiFi");
            wifiManager.resetSettings();
            delay(500);
            ESP.restart();
        }
    }

    server.handleClient();

    if (WiFi.status() != WL_CONNECTED) {
        blinkRedLED();
        if (now - lastReconnectAttempt > 10000) {
            lastReconnectAttempt = now;
            reconnectAttempts++;
            WiFi.reconnect();
            if (reconnectAttempts >= MAX_WIFI_RETRIES) {
                ESP.restart();
            }
        }
    } else {
        if (reconnectAttempts > 0) {
            reconnectAttempts = 0;
        }

        if (millis() - lastDataFetch > FETCH_INTERVAL) {
            Serial.println("🔄 Time to fetch new surf data...");
            if (fetchSurfDataFromServer()) {
                Serial.println("✅ Surf data fetch successful");
                lastDataFetch = millis();
            } else {
                Serial.println("❌ Surf data fetch failed, will retry later");
                lastDataFetch = millis();
            }
        }

        if (lastSurfData.needsDisplayUpdate) {
            Serial.println("🔄 Detected state change, updating display...");
            updateSurfDisplay();
            lastSurfData.needsDisplayUpdate = false;
        }

        updateBlinkingAnimation();

        if (lastSurfData.dataReceived && (millis() - lastSurfData.lastUpdate < 1800000)) {
            blinkGreenLED();
        } else {
            blinkStatusLED(CRGB::Blue);
        }
    }

    delay(5);
}
