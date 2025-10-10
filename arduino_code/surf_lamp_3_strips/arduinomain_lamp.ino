
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
#define LED_PIN_CENTER 4
#define LED_PIN_SIDE 2
#define LED_PIN_SIDE_LEFT 5

#define NUM_LEDS_RIGHT 15
#define NUM_LEDS_LEFT 15
#define NUM_LEDS_CENTER 20
#define BRIGHTNESS 100
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
const int ARDUINO_ID = 4433;  // ✨ CHANGE THIS for each Arduino device

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

// LED Arrays
CRGB leds_center[NUM_LEDS_CENTER];
CRGB leds_side_right[NUM_LEDS_RIGHT];
CRGB leds_side_left[NUM_LEDS_LEFT];

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
    float wind_scale_numerator = 18.0;      // Wind speed scaling: maps 0-13 m/s to 0-18 LEDs
    float wind_scale_denominator = 13.0;
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

    // Check if wave height threshold is exceeded (lastSurfData.waveHeight is in METERS)
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

    // Store quiet hours state BEFORE updating display (critical: updateSurfDisplay checks this!)
    lastSurfData.quietHoursActive = quiet_hours_active;

    // Update LEDs with the new data
    updateSurfDisplay(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg, wave_threshold_cm, wind_speed_threshold_knots);

    // Store remaining data for status reporting (converting height and threshold to meters for consistency)
    lastSurfData.waveHeight = wave_height_cm / 100.0;
    lastSurfData.wavePeriod = wave_period_s;
    lastSurfData.windSpeed = wind_speed_mps;
    lastSurfData.windDirection = wind_direction_deg;
    lastSurfData.waveThreshold = wave_threshold_cm / 100.0;  // Convert cm to meters for consistent comparison
    lastSurfData.windSpeedThreshold = wind_speed_threshold_knots;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    
    return true;
}


void updateSurfDisplay(int waveHeight_cm, float wavePeriod, int windSpeed, int windDirection, int waveThreshold_cm, int windSpeedThreshold_knots) {
    // Check for quiet hours - show only the highest LED that would normally be on
    if (lastSurfData.quietHoursActive) {
        // Calculate how many LEDs would be on during daytime
        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

        // Turn off all LEDs first
        FastLED.clear();

        // Light only the top LED that would normally be on (highest index)
        if (windSpeedLEDs > 0) leds_center[windSpeedLEDs - 1] = getWindSpeedColor(currentTheme);
        if (waveHeightLEDs > 0) leds_side_right[waveHeightLEDs - 1] = getWaveHeightColor(currentTheme);
        if (wavePeriodLEDs > 0) leds_side_left[wavePeriodLEDs - 1] = getWavePeriodColor(currentTheme);

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
    FastLED.clear();
    FastLED.show();
    
    Serial.println("💡 LED strips initialized");
    
    // LED startup test
    performLEDTest();
    
    // Initialize preferences
    preferences.begin("wifi-creds", false);
    
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

// ---------------------------- Main Loop ----------------------------

void loop() {
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
