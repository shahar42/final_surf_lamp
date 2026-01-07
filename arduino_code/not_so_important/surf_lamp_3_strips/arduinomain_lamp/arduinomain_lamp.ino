
#include <WiFi.h>
#include <WebServer.h>
#include <WiFiManager.h>  // WiFiManager library for robust WiFi configuration
#include <ArduinoJson.h>
#include <FastLED.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "soc/soc.h"           // For brownout detector disable
#include "soc/rtc_cntl_reg.h"  // For brownout detector disable

#include "ServerDiscovery.h"

// Global instances
ServerDiscovery serverDiscovery;
WiFiManager wifiManager;

// ---------------------------- Configuration ----------------------------
#define BUTTON_PIN 0  // ESP32 boot button
#define LED_PIN_CENTER 4
#define LED_PIN_SIDE 2
#define LED_PIN_SIDE_LEFT 5

#define NUM_LEDS_RIGHT 14
#define NUM_LEDS_LEFT 14
#define NUM_LEDS_CENTER 15
#define BRIGHTNESS 30  // Ultra-low for weak USB sources (60→30, was originally 100)
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

#define WIFI_TIMEOUT 30  // Timeout for WiFi connection in seconds

// System Constants (non-LED related)
#define MAX_BRIGHTNESS 255           // Maximum LED brightness value
#define HTTP_TIMEOUT_MS 15000        // HTTP request timeout in milliseconds
#define JSON_CAPACITY 1024           // JSON document capacity for Arduino data

// NOTE: LED calculation constants (wind scale, wave divisor, threshold multiplier)
// are now in LEDMappingConfig struct (see lines 104-152)

// Device Configuration
const int ARDUINO_ID = 5;  // CHANGE THIS for each Arduino device

// Global Variables
WebServer server(80);
unsigned long lastDataFetch = 0;
const unsigned long FETCH_INTERVAL = 780000; // 13 minutes
bool shouldStartConfigPortal = false;

// WiFi reconnection tracking
const int MAX_WIFI_RETRIES = 5;
int reconnectAttempts = 0;
unsigned long lastReconnectAttempt = 0;

// Blinking state variables
unsigned long lastBlinkUpdate = 0;
const unsigned long BLINK_INTERVAL = 1500; // 1.5 seconds for slow smooth blink
float blinkPhase = 0.0; // Phase for smooth sine wave blinking

// LED Arrays
CRGB leds_center[NUM_LEDS_CENTER];
CRGB leds_side_right[NUM_LEDS_RIGHT];
CRGB leds_side_left[NUM_LEDS_LEFT];

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
} lastSurfData;


// ---------------------------- Wave Animation Configuration ----------------------------

struct WaveConfig {
    // User-adjustable parameters
    uint8_t brightness_min_percent = 50;   // Minimum brightness during wave (0-100%)
    uint8_t brightness_max_percent = 110;  // Maximum brightness during wave (0-100%)
    float wave_length_side = 6.0;          // Wave length for side strips (LEDs per cycle)
    float wave_length_center = 8.0;        // Wave length for center strip (LEDs per cycle)
    float wave_speed = 1;                // Wave speed multiplier

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
    float wind_scale_numerator = 13.0;      // Wind speed scaling: maps 0-38 knots (19.55 m/s) to 0-13 LEDs
    float wind_scale_denominator = 15.433;
    float mps_to_knots_factor = 1.94384;    // Conversion constant: m/s to knots
    uint8_t wave_height_divisor = 25;       // Wave height scaling: cm per LED (25cm = 1 LED)
    float threshold_brightness_multiplier = 1.4;  // Brightness boost when threshold exceeded (60% brighter)

    // Helper: Calculate wind speed LEDs from m/s (used by all wind speed calculations)
    int calculateWindLEDs(float windSpeed_mps) const {
        return constrain(
            static_cast<int>(windSpeed_mps * wind_scale_numerator / wind_scale_denominator),
            1,
            NUM_LEDS_CENTER - 2  // Reserve LED 0 for wind direction, top LED for status
        );
    }

    // Helper: Calculate wave height LEDs from centimeters (used by updateSurfDisplay)
    int calculateWaveLEDsFromCm(int waveHeight_cm) const {
        return constrain(
            static_cast<int>(waveHeight_cm / wave_height_divisor) + 1,  // +1 ensures at least 1 LED
            0,
            NUM_LEDS_RIGHT
        );
    }

    // Helper: Calculate wave height LEDs from meters (used by status endpoint)
    int calculateWaveLEDsFromMeters(float waveHeight_m) const {
        return calculateWaveLEDsFromCm(static_cast<int>(waveHeight_m * 100));  // Convert m to cm
    }

    // Helper: Calculate wave period LEDs (1:1 mapping: seconds to LEDs)
    int calculateWavePeriodLEDs(float wavePeriod_s) const {
        return constrain(static_cast<int>(wavePeriod_s), 0, NUM_LEDS_LEFT);
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
void updateSurfDisplay(int waveHeight_cm, float wavePeriod, int windSpeed, int windDirection, int waveThreshold_cm = 100, int windSpeedThreshold_knots = 15);
void handleSurfDataUpdate();
void handleStatusRequest();
void handleTestRequest();
void handleLEDTestRequest();
void handleDeviceInfoRequest();
void handleManualFetchRequest();
void handleDiscoveryTest();
void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots);
void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm);
void updateBlinkingLEDs(int numActiveLeds, int segmentLen, CRGB* leds, CHSV baseColor);
void updateBlinkingCenterLEDs(int numActiveLeds, CHSV baseColor);
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


// ---------------------------- WiFiManager Callback Functions ----------------------------

void configModeCallback(WiFiManager *myWiFiManager) {
    Serial.println("🔧 Config mode started");
    Serial.println("📱 AP: SurfLamp-Setup");

    // Blue LEDs for configuration mode
    for (int i = 0; i < NUM_LEDS_CENTER; i++) leds_center[i] = CRGB::Blue;
    for (int i = 0; i < NUM_LEDS_RIGHT; i++) leds_side_right[i] = CRGB::Blue;
    for (int i = 0; i < NUM_LEDS_LEFT; i++) leds_side_left[i] = CRGB::Blue;
    FastLED.show();
}

void saveConfigCallback() {
    Serial.println("✅ Config saved!");
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

    leds_center[0] = hsvColor;
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
    leds_center[0] = color;
    FastLED.show();
}

// ---------------------------- LED Control Functions ----------------------------

void updateLEDs(int numActiveLeds, int segmentLen, CRGB* leds, CHSV* colorMap) {
    for (int i = 0; i < segmentLen; i++) {
        int colorIndex = map(i, 0, segmentLen - 1, 0, 23); // Map to color array size
        if (i < numActiveLeds) {
            leds[i] = CHSV(colorMap[colorIndex].hue, colorMap[colorIndex].sat, colorMap[colorIndex].val);
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void updateBlinkingLEDs(int numActiveLeds, int segmentLen, CRGB* leds, CHSV baseColor) {
    // Enhanced wave effect: traveling wave from bottom (LED 0) to top
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    for (int i = 0; i < segmentLen; i++) {
        if (i < numActiveLeds) {
            // Calculate wave position: wave travels up from LED 0
            float wavePhase = blinkPhase * waveConfig.wave_speed - (i * 2.0 * PI / waveConfig.wave_length_side);

            // Create traveling wave that smoothly oscillates between min and max brightness
            // Map sin output from [-1, 1] to [minBrightness, maxBrightness]
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);

            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));
            leds[i] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void updateBlinkingCenterLEDs(int numActiveLeds, CHSV baseColor) {
    // Enhanced wave effect for center LEDs: traveling wave from bottom (LED 1) to top
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    // Start from LED 1, skip LED 0 (reserved for wind direction)
    for (int i = 1; i < NUM_LEDS_CENTER - 1; i++) {
        if (i < numActiveLeds + 1) {
            // Calculate wave position: wave travels up from LED 1
            float wavePhase = blinkPhase * waveConfig.wave_speed - ((i - 1) * 2.0 * PI / waveConfig.wave_length_center);

            // Create traveling wave that smoothly oscillates between min and max brightness
            // Map sin output from [-1, 1] to [minBrightness, maxBrightness]
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);

            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));
            leds_center[i] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds_center[i] = CRGB::Black;
        }
    }
}

void updateLEDsOneColor(int numActiveLeds, int segmentLen, CRGB* leds, CHSV color) {
    for (int i = 0; i < segmentLen; i++) {
        if (i < numActiveLeds) {
            leds[i] = color;
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots) {
    // Convert wind speed from m/s to knots for threshold comparison
    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed_mps);

    // Check if quiet hours are active - disable threshold blinking during sleep time
    if (lastSurfData.quietHoursActive || windSpeedInKnots < windSpeedThreshold_knots) {
        // NORMAL MODE: Theme-based wind speed visualization (no blinking during quiet hours)
        updateLEDsOneColor(windSpeedLEDs, NUM_LEDS_CENTER - 2, &leds_center[1], getWindSpeedColor(currentTheme));
    } else {
        // ALERT MODE: Blinking theme-based wind speed LEDs (starting from second LED)
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingCenterLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness())); // Blinking theme color
    }
}

void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm) {
    // Check if quiet hours are active - disable threshold blinking during sleep time
    if (lastSurfData.quietHoursActive || waveHeight_cm < waveThreshold_cm) {
        // NORMAL MODE: Theme-based wave height visualization (no blinking during quiet hours)
        updateLEDsOneColor(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, getWaveHeightColor(currentTheme));
    } else {
        // ALERT MODE: Blinking theme-based wave height LEDs
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingLEDs(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness())); // Blinking theme color
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
        // Don't wrap blinkPhase - sin() is naturally periodic, wrapping causes discontinuity
        lastBlinkUpdate = currentMillis;
    }

    bool needsUpdate = false;

    // Check if wind speed threshold is exceeded
    float windSpeedInKnots = ledMapping.windSpeedToKnots(lastSurfData.windSpeed);
    if (windSpeedInKnots >= lastSurfData.windSpeedThreshold) {
        int windSpeedLEDs = ledMapping.calculateWindLEDs(lastSurfData.windSpeed);
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingCenterLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
        needsUpdate = true;
    }

    // Check if wave height threshold is exceeded
    // BOTH values are in METERS (float) - see SurfData struct declaration for details
    // Example: 1.35m >= 1.0m → TRUE → triggers blinking animation
    if (lastSurfData.waveHeight >= lastSurfData.waveThreshold) {
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(lastSurfData.waveHeight);
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingLEDs(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
        needsUpdate = true;
    }

    // Only call FastLED.show() if we updated blinking LEDs
    if (needsUpdate) {
        FastLED.show();
    }
}

void setWindDirection(int windDirection) {
    Serial.printf("🐛 DEBUG: Wind direction = %d°\n", windDirection);
    int northLED = NUM_LEDS_CENTER - 1;

    // Wind direction color coding (ALWAYS consistent for navigation)
    if ((windDirection >= 0 && windDirection <= 10) || (windDirection >= 300 && windDirection <= 360)) {
        leds_center[northLED] = CRGB::Green;   // North - Green
    } else if (windDirection > 10 && windDirection <= 180) {
        leds_center[northLED] = CRGB::Yellow;  // East - Yellow
    } else if (windDirection > 180 && windDirection <= 250) {
        leds_center[northLED] = CRGB::Red;     // South - Red
    } else if (windDirection > 250 && windDirection < 300) {
        leds_center[northLED] = CRGB::Blue;    // West - Blue
    }
}

void performLEDTest() {
    Serial.println("🧪 Running LED test sequence...");
    
    // Test each strip with different colors
    updateLEDs(NUM_LEDS_CENTER, NUM_LEDS_CENTER, leds_center, colorMapWind);
    updateLEDs(NUM_LEDS_RIGHT, NUM_LEDS_RIGHT, leds_side_right, colorMapWave);
    updateLEDs(NUM_LEDS_LEFT, NUM_LEDS_LEFT, leds_side_left, colorMap);
    FastLED.show();
    
    delay(2000);
    
    // Rainbow test
    for (int hue = 0; hue < 256; hue += 5) {
        fill_solid(leds_center, NUM_LEDS_CENTER, CHSV(hue, 255, 255));
        fill_solid(leds_side_right, NUM_LEDS_RIGHT, CHSV(hue + 85, 255, 255));
        fill_solid(leds_side_left, NUM_LEDS_LEFT, CHSV(hue + 170, 255, 255));
        FastLED.show();
        delay(20);
    }
    
    clearLEDs();
    Serial.println("✅ LED test completed");
}

// ---------------------------- WiFi Functions ----------------------------
// WiFi management is now handled by WiFiManager library
// See configModeCallback() and saveConfigCallback() above

// ---------------------------- HTTP Server Endpoints ----------------------------

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
    statusDoc["firmware_version"] = "1.0.0";
    
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
    
    infoDoc["device_name"] = "Surf Lamp";
    infoDoc["arduino_id"] = ARDUINO_ID;
    infoDoc["model"] = ESP.getChipModel();
    infoDoc["revision"] = ESP.getChipRevision();
    infoDoc["cores"] = ESP.getChipCores();
    infoDoc["flash_size"] = ESP.getFlashChipSize();
    infoDoc["psram_size"] = ESP.getPsramSize();
    infoDoc["firmware_version"] = "1.0.0";
    infoDoc["led_strips"]["center"] = NUM_LEDS_CENTER;
    infoDoc["led_strips"]["right"] = NUM_LEDS_RIGHT;
    infoDoc["led_strips"]["left"] = NUM_LEDS_LEFT;
    
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
    
    // V1 Payload specific fields
    bool sunset_animation = doc["sunset_animation"] | false;
    int day_of_year = doc["day_of_year"] | 0;

    // Update theme if changed
    if (led_theme != currentTheme) {
        currentTheme = led_theme;
        Serial.printf("🎨 LED theme updated to: %s\n", currentTheme.c_str());
    }
    
    if (sunset_animation) {
        Serial.printf("🌅 Sunset animation trigger received (Day %d) - Animation skipped per config\n", day_of_year);
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

    // Store hours state BEFORE updating display (critical: updateSurfDisplay checks this!)
    lastSurfData.quietHoursActive = quiet_hours_active;
    lastSurfData.offHoursActive = off_hours_active;

    // Update LEDs with the new data
    updateSurfDisplay(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg, wave_threshold_cm, wind_speed_threshold_knots);

    // Store remaining data for status reporting (converting height and threshold to meters for consistency)
    // CRITICAL: These conversions rely on waveHeight and waveThreshold being declared as FLOAT
    // in the SurfData struct. If they were int, division would truncate (e.g., 50/100=0)
    lastSurfData.waveHeight = wave_height_cm / 100.0;        // cm → meters (e.g., 135cm → 1.35m)
    lastSurfData.wavePeriod = wave_period_s;
    lastSurfData.windSpeed = wind_speed_mps;
    lastSurfData.windDirection = wind_direction_deg;
    lastSurfData.waveThreshold = wave_threshold_cm / 100.0;  // cm → meters (e.g., 50cm → 0.5m) - MUST match waveHeight units!
    lastSurfData.windSpeedThreshold = wind_speed_threshold_knots;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    
    return true;
}


void updateSurfDisplay(int waveHeight_cm, float wavePeriod, int windSpeed, int windDirection, int waveThreshold_cm, int windSpeedThreshold_knots) {
    // OFF HOURS: Lamp completely off (top priority)
    if (lastSurfData.offHoursActive) {
        FastLED.clear();
        FastLED.show();
        Serial.println("🔴 Off hours active - lamp turned OFF");
        return;
    }

    // QUIET HOURS: Only top LED of each strip (secondary priority)
    if (lastSurfData.quietHoursActive) {
        // Calculate how many LEDs would be on during daytime
        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

        // Turn off all LEDs first
        FastLED.clear();

        // Light only the top LED that would normally be on (highest index)
        // CENTER: no -1 because normal mode uses &leds_center[1], so top = windSpeedLEDs
        // SIDES: -1 because normal mode uses leds_side[0], so top = LEDs - 1
        if (windSpeedLEDs > 0) leds_center[windSpeedLEDs] = getWindSpeedColor(currentTheme);
        if (waveHeightLEDs > 0) leds_side_right[waveHeightLEDs - 1] = getWaveHeightColor(currentTheme);
        if (wavePeriodLEDs > 0) leds_side_left[wavePeriodLEDs - 1] = getWavePeriodColor(currentTheme);

        // Keep wind direction LED on for navigation (always useful)
        setWindDirection(windDirection);

        FastLED.show();
        Serial.println("🌙 Quiet hours: Only top LEDs active + wind direction");
        return;
    }

    // Calculate LED counts based on surf data using centralized mapping configuration
    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

    // Set wind direction indicator
    setWindDirection(windDirection);

    // Set wave period LEDs with theme color
    updateLEDsOneColor(wavePeriodLEDs, NUM_LEDS_LEFT, leds_side_left, getWavePeriodColor(currentTheme));

    // Apply threshold logic for wind speed and wave height
    applyWindSpeedThreshold(windSpeedLEDs, windSpeed, windSpeedThreshold_knots);
    applyWaveHeightThreshold(waveHeightLEDs, waveHeight_cm, waveThreshold_cm);

    FastLED.show();

    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d° [Wave Threshold: %dcm, Wind Threshold: %dkts]\n",
                  windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, windDirection, waveThreshold_cm, windSpeedThreshold_knots);
}


// ---------------------------- Setup Function ----------------------------

void setup() {
    // Disable brownout detector for low-power USB compatibility
    // WARNING: Only use with stable power sources - allows operation below 2.43V
    #ifdef ESP32
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    #endif

    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌊 ========================================");
    Serial.println("🌊 SURF LAMP - HTTP SERVER ARCHITECTURE");
    Serial.println("🌊 ========================================");
    Serial.printf("🔧 Arduino ID: %d\n", ARDUINO_ID);
    
    // Initialize button
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    
    // Initialize LED strips
    FastLED.addLeds<LED_TYPE, LED_PIN_CENTER, COLOR_ORDER>(leds_center, NUM_LEDS_CENTER);
    FastLED.addLeds<LED_TYPE, LED_PIN_SIDE, COLOR_ORDER>(leds_side_right, NUM_LEDS_RIGHT);
    FastLED.addLeds<LED_TYPE, LED_PIN_SIDE_LEFT, COLOR_ORDER>(leds_side_left, NUM_LEDS_LEFT);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.setMaxPowerInVoltsAndMilliamps(5, 1000); // Limit to 1A at 5V for USB compatibility
    FastLED.clear();
    FastLED.show();
    
    Serial.println("💡 LED strips initialized");

    // LED startup test - DISABLED for production (high power draw)
    // performLEDTest(); // Enable only for testing with adequate power supply

    // PRODUCTION MODE: WiFi credentials are saved and persist across reboots
    // To reset WiFi: press and hold BOOT button for 1 second
    // wifiManager.resetSettings();  // DISABLED - only enable for testing
    // Serial.println("🗑️ [TEST MODE] WiFi credentials cleared - will start config portal");

    // WiFiManager setup - simple and clean
    wifiManager.setAPCallback(configModeCallback);
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setConfigPortalTimeout(0); // No timeout - wait indefinitely

    // Visual feedback: Blue LEDs during any config
    for (int i = 0; i < NUM_LEDS_CENTER; i++) leds_center[i] = CRGB::Blue;
    for (int i = 0; i < NUM_LEDS_RIGHT; i++) leds_side_right[i] = CRGB::Blue;
    for (int i = 0; i < NUM_LEDS_LEFT; i++) leds_side_left[i] = CRGB::Blue;
    FastLED.show();

    // Auto-connect with retry logic
    bool connected = false;
    for (int attempt = 1; attempt <= MAX_WIFI_RETRIES && !connected; attempt++) {
        Serial.printf("🔄 WiFi connection attempt %d of %d\n", attempt, MAX_WIFI_RETRIES);

        // Set timeout: 30 seconds for retry attempts, indefinite for last attempt
        if (attempt < MAX_WIFI_RETRIES) {
            wifiManager.setConfigPortalTimeout(30); // 30 second timeout per attempt
        } else {
            wifiManager.setConfigPortalTimeout(0); // Last attempt: wait indefinitely in config portal
        }

        connected = wifiManager.autoConnect("SurfLamp-Setup", "surf123456");

        if (!connected && attempt < MAX_WIFI_RETRIES) {
            Serial.println("⏳ Waiting 5 seconds before retry...");
            delay(5000);
        }
    }

    if (!connected) {
        Serial.println("❌ Failed to connect after 5 attempts - restarting");
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

// ---------------------------- Main Loop ----------------------------

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
