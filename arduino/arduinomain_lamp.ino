
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
    unsigned long lastUpdate = 0;
    bool dataReceived = false;
} lastSurfData;


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

String currentTheme = "day";  // Default theme

CHSV getWindSpeedColor(String theme) {
    if (theme == "dark") {
        return CHSV(30, 255, 255);  // Orange
    } else {
        return CHSV(120, 255, 255); // Green
    }
}

CHSV getWaveHeightColor(String theme) {
    if (theme == "dark") {
        return CHSV(240, 255, 255); // Blue
    } else {
        return CHSV(240, 255, 255); // Blue
    }
}

CHSV getWavePeriodColor(String theme) {
    if (theme == "dark") {
        return CHSV(280, 255, 255); // Purple
    } else {
        return CHSV(0, 30, 255);    // White with a dash of red
    }
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

void blinkStatusLED(CRGB color) {
    // Use wave-like breathing pattern with shared blinkPhase and 20% dimmer
    float brightnessFactor = 0.76 + 0.2 * sin(blinkPhase); // 0.8 * (0.95 + 0.25 * sin) = 20% dimmer
    int adjustedBrightness = min(204, (int)(255 * brightnessFactor)); // Max 204 (80% of 255)

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
    // Use shared timing from updateBlinkingAnimation
    float brightnessFactor = 0.95 + 0.25 * sin(blinkPhase);
    int adjustedBrightness = min(255, (int)(baseColor.val * brightnessFactor));

    for (int i = 0; i < segmentLen; i++) {
        if (i < numActiveLeds) {
            leds[i] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void updateBlinkingCenterLEDs(int numActiveLeds, CHSV baseColor) {
    // Use shared blinkPhase, no timing update here
    float brightnessFactor = 0.95 + 0.25 * sin(blinkPhase);
    int adjustedBrightness = min(255, (int)(baseColor.val * brightnessFactor));

    // Start from LED 1, skip LED 0
    for (int i = 1; i < NUM_LEDS_CENTER - 1; i++) {
        if (i < numActiveLeds + 1) {
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
    float windSpeedInKnots = windSpeed_mps * 1.94384;

    if (windSpeedInKnots >= windSpeedThreshold_knots) {
        // ALERT MODE: Blinking theme-based wind speed LEDs (starting from second LED)
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingCenterLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, min(255, (int)(255 * 1.6)))); // Blinking theme color
    } else {
        // NORMAL MODE: Theme-based wind speed visualization
        updateLEDsOneColor(windSpeedLEDs, NUM_LEDS_CENTER - 2, &leds_center[1], getWindSpeedColor(currentTheme));
    }
}

void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm) {
    if (waveHeight_cm >= waveThreshold_cm) {
        // ALERT MODE: Blinking theme-based wave height LEDs
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingLEDs(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, CHSV(themeColor.hue, themeColor.sat, min(255, (int)(255 * 1.6)))); // Blinking theme color
    } else {
        // NORMAL MODE: Theme-based wave height visualization
        updateLEDsOneColor(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, getWaveHeightColor(currentTheme));
    }
}

void updateBlinkingAnimation() {
    // Only update blinking if we have valid surf data and thresholds are exceeded
    if (!lastSurfData.dataReceived) return;

    // Update timing once per call
    unsigned long currentMillis = millis();
    if (currentMillis - lastBlinkUpdate >= 5) { // 200 FPS for ultra-smooth animation
        blinkPhase += 0.2094; // 0.3-second cycle (2π/30 = 0.2094)
        if (blinkPhase >= 2 * PI) blinkPhase = 0.0;
        lastBlinkUpdate = currentMillis;
    }

    bool needsUpdate = false;

    // Check if wind speed threshold is exceeded
    float windSpeedInKnots = lastSurfData.windSpeed * 1.94384;
    if (windSpeedInKnots >= lastSurfData.windSpeedThreshold) {
        int windSpeedLEDs = constrain(static_cast<int>(lastSurfData.windSpeed * 10.0 / 22.0), 1, NUM_LEDS_CENTER - 2);
        CHSV themeColor = getWindSpeedColor(currentTheme);
        updateBlinkingCenterLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, min(255, (int)(255 * 1.6))));
        needsUpdate = true;
    }

    // Check if wave height threshold is exceeded
    if (lastSurfData.waveHeight >= lastSurfData.waveThreshold) {
        int waveHeightLEDs = constrain(static_cast<int>(lastSurfData.waveHeight / 25) + 1, 0, NUM_LEDS_RIGHT);
        CHSV themeColor = getWaveHeightColor(currentTheme);
        updateBlinkingLEDs(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, CHSV(themeColor.hue, themeColor.sat, min(255, (int)(255 * 1.6))));
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
    if (windDirection < 45 || windDirection >= 315) {
        leds_center[northLED] = CRGB::Green;   // North - Green
    } else if (windDirection >= 45 && windDirection < 135) {
        leds_center[northLED] = CRGB::Yellow;  // East - Yellow
    } else if (windDirection >= 135 && windDirection < 225) {
        leds_center[northLED] = CRGB::Red;     // South - Red
    } else if (windDirection >= 225 && windDirection < 315) {
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
    statusDoc["last_surf_data"]["last_update_ms"] = lastSurfData.lastUpdate;
    
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
    Serial.printf("   LED Theme: %s\n", currentTheme.c_str());
    
    // Update LEDs with the new data
    updateSurfDisplay(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg, wave_threshold_cm, wind_speed_threshold_knots);
    
    // Store data for status reporting (converting height back to meters for consistency if needed)
    lastSurfData.waveHeight = wave_height_cm / 100.0;
    lastSurfData.wavePeriod = wave_period_s;
    lastSurfData.windSpeed = wind_speed_mps;
    lastSurfData.windDirection = wind_direction_deg;
    lastSurfData.waveThreshold = wave_threshold_cm;
    lastSurfData.windSpeedThreshold = wind_speed_threshold_knots;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    
    return true;
}


void updateSurfDisplay(int waveHeight_cm, float wavePeriod, int windSpeed, int windDirection, int waveThreshold_cm, int windSpeedThreshold_knots) {
    // Calculate LED counts based on surf data
    // Scale wind speed to use full LED range (0-22 m/s maps to 0-18 LEDs)
    int windSpeedLEDs = constrain(static_cast<int>(windSpeed * 10.0 / 22.0), 1, NUM_LEDS_CENTER - 2);
    int waveHeightLEDs = constrain(static_cast<int>(waveHeight_cm / 25) + 1, 0, NUM_LEDS_RIGHT);
    int wavePeriodLEDs = constrain(static_cast<int>(wavePeriod), 0, NUM_LEDS_LEFT);
    
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
    
    delay(100); // Small delay to prevent excessive CPU usage
}
