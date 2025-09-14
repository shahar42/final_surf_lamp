/*
 * Surf Lamp - HTTP Server Architecture
 *
 * Description: ESP32-based surf condition display using LED strips
 * Author: Surf Lamp Team
 * Version: 1.0.0
 *
 * This code implements a WiFi-connected surf condition display that:
 * - Connects to WiFi and serves HTTP API endpoints
 * - Fetches surf data from a backend server
 * - Displays wave height, wind speed, and wave period on LED strips
 * - Provides threshold-based alerting with blinking LEDs
 * - Supports WiFi configuration via captive portal
 */

// ============================================================================
// LIBRARY DEPENDENCIES
// ============================================================================
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "ServerDiscovery.h"

// ============================================================================
// HARDWARE CONFIGURATION CONSTANTS
// ============================================================================
const int BUTTON_PIN = 0;              // ESP32 boot button
const int LED_PIN_CENTER = 4;          // Center LED strip pin
const int LED_PIN_SIDE = 2;            // Right LED strip pin
const int LED_PIN_SIDE_LEFT = 5;       // Left LED strip pin

const int NUM_LEDS_RIGHT = 9;          // Right strip LED count
const int NUM_LEDS_LEFT = 9;           // Left strip LED count
const int NUM_LEDS_CENTER = 12;        // Center strip LED count
const int BRIGHTNESS = 100;            // LED brightness level
const int LED_TYPE = WS2812B;          // LED strip type
const int COLOR_ORDER = GRB;           // LED color order

// ============================================================================
// NETWORK CONFIGURATION CONSTANTS
// ============================================================================
const int WIFI_TIMEOUT = 30;           // WiFi connection timeout (seconds)
const unsigned long AP_TIMEOUT = 60000;         // AP mode timeout (ms)
const unsigned long FETCH_INTERVAL = 900000;    // Data fetch interval (15 minutes)
const unsigned long BLINK_INTERVAL = 1500;      // LED blink interval (ms)

// ============================================================================
// DEVICE CONFIGURATION
// ============================================================================
const int ARDUINO_ID = 4433;           // Unique device identifier

// ============================================================================
// DEFAULT WIFI CREDENTIALS
// ============================================================================
char wifiSsid[32] = "Sunrise";
char wifiPassword[64] = "4085429360";

// ============================================================================
// GLOBAL OBJECTS AND INSTANCES
// ============================================================================
ServerDiscovery serverDiscovery;       // Global discovery instance
Preferences preferences;               // NVRAM preferences storage
WebServer httpServer(80);              // HTTP server instance

// LED strip arrays
CRGB ledsCenterStrip[NUM_LEDS_CENTER];
CRGB ledsSideRight[NUM_LEDS_RIGHT];
CRGB ledsSideLeft[NUM_LEDS_LEFT];

// ============================================================================
// APPLICATION STATE VARIABLES
// ============================================================================
bool isConfigureWifiMode = false;
unsigned long apModeStartTime = 0;
unsigned long lastDataFetchTime = 0;
unsigned long lastBlinkUpdateTime = 0;
float blinkAnimationPhase = 0.0;

// ============================================================================
// SURF DATA STRUCTURE
// ============================================================================
struct SurfDataState {
    float waveHeight = 0.0;             // Wave height in meters
    float wavePeriod = 0.0;             // Wave period in seconds
    float windSpeed = 0.0;              // Wind speed in m/s
    int windDirection = 0;              // Wind direction in degrees
    int waveThreshold = 100;            // Wave height threshold (cm)
    int windSpeedThreshold = 15;        // Wind speed threshold (knots)
    unsigned long lastUpdate = 0;       // Last update timestamp
    bool dataReceived = false;          // Data received flag
} currentSurfData;

// ============================================================================
// LED COLOR MAPS
// ============================================================================
const CHSV BASE_COLOR_MAP[] = {
    CHSV(120, 255, 125), CHSV(130, 255, 200), CHSV(140, 255, 255), CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(190, 255, 255), CHSV(200, 255, 200),
    CHSV(210, 255, 255), CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(110, 255, 255), CHSV(0, 0, 255)
};

const CHSV WAVE_COLOR_MAP[] = {
    CHSV(95, 255, 125),  CHSV(95, 255, 200),  CHSV(140, 255, 255), CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(190, 255, 255), CHSV(200, 255, 200),
    CHSV(210, 255, 255), CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(85, 255, 255),  CHSV(85, 255, 255)
};

const CHSV WIND_COLOR_MAP[] = {
    CHSV(85, 255, 125),  CHSV(90, 255, 200),  CHSV(95, 255, 255),  CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(87, 255, 255),  CHSV(90, 255, 200),
    CHSV(95, 255, 255),  CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(85, 255, 255),  CHSV(85, 255, 255)
};

// ============================================================================
// FUNCTION FORWARD DECLARATIONS
// ============================================================================

// WiFi credential management
void saveWifiCredentials(const char* newSsid, const char* newPassword);
void loadWifiCredentials();
bool connectToWifi();
void startWifiConfigurationMode();
void handleAccessPointTimeout();

// LED control functions
void clearAllLeds();
void setStatusLed(CRGB color);
void blinkStatusLed(CRGB color, int delayMs = 500);
void blinkBlueLed();
void blinkGreenLed();
void blinkRedLed();
void blinkYellowLed();
void performLedTestSequence();

// LED display functions
void updateLedsWithColorMap(int numActiveLeds, int segmentLength, CRGB* leds, const CHSV* colorMap);
void updateLedsWithSingleColor(int numActiveLeds, int segmentLength, CRGB* leds, CHSV color);
void updateBlinkingLeds(int numActiveLeds, int segmentLength, CRGB* leds, CHSV baseColor);
void updateBlinkingCenterLeds(int numActiveLeds, CHSV baseColor);
void updateBlinkingAnimation();
void setWindDirectionIndicator(int windDirection);

// Surf data processing
bool fetchSurfDataFromServer();
bool processSurfDataJson(const String &jsonData);
void updateSurfDisplay(int waveHeightCm, float wavePeriod, int windSpeed, int windDirection, int waveThresholdCm, int windSpeedThresholdKnots);
void applyWindSpeedThreshold(int windSpeedLeds, int windSpeedMps, int windSpeedThresholdKnots);
void applyWaveHeightThreshold(int waveHeightLeds, int waveHeightCm, int waveThresholdCm);

// HTTP server endpoints
void setupHttpEndpoints();
void handleSurfDataUpdateRequest();
void handleStatusRequest();
void handleTestRequest();
void handleLedTestRequest();
void handleDeviceInfoRequest();
void handleManualFetchRequest();
void handleDiscoveryTestRequest();

// Setup and initialization
void initializeLedStrips();
void initializeHardware();
void attemptInitialDataFetch();

// ============================================================================
// WIFI CREDENTIAL MANAGEMENT FUNCTIONS
// ============================================================================

void saveWifiCredentials(const char* newSsid, const char* newPassword) {
    if (!newSsid || !newPassword) {
        Serial.println("❌ Invalid WiFi credentials provided");
        return;
    }

    preferences.begin("wifi-creds", false);
    preferences.putString("ssid", newSsid);
    preferences.putString("password", newPassword);
    preferences.end();
    Serial.println("✅ WiFi credentials saved to NVRAM");
}

void loadWifiCredentials() {
    preferences.begin("wifi-creds", false);
    String storedSsid = preferences.getString("ssid", wifiSsid);
    String storedPassword = preferences.getString("password", wifiPassword);
    preferences.end();

    storedSsid.toCharArray(wifiSsid, sizeof(wifiSsid));
    storedPassword.toCharArray(wifiPassword, sizeof(wifiPassword));

    Serial.printf("📝 Loaded credentials - SSID: %s\n", wifiSsid);
}

bool connectToWifi() {
    Serial.println("🔄 Attempting WiFi connection...");
    WiFi.mode(WIFI_STA);
    loadWifiCredentials();
    WiFi.begin(wifiSsid, wifiPassword);

    int connectionAttempts = 0;
    while (WiFi.status() != WL_CONNECTED && connectionAttempts < WIFI_TIMEOUT) {
        Serial.print(".");
        blinkBlueLed();
        delay(500);
        connectionAttempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi Connected!");
        Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("📶 SSID: %s\n", WiFi.SSID().c_str());
        Serial.printf("💪 Signal Strength: %d dBm\n", WiFi.RSSI());

        setupHttpEndpoints();
        return true;
    } else {
        Serial.println("\n❌ WiFi connection failed");
        return false;
    }
}

void startWifiConfigurationMode() {
    isConfigureWifiMode = true;
    WiFi.disconnect(true);
    WiFi.mode(WIFI_AP);
    WiFi.softAP("SurfLamp-Setup", "surf123456");

    Serial.println("🔧 Configuration mode started");
    Serial.printf("📍 AP IP: %s\n", WiFi.softAPIP().toString().c_str());
    Serial.println("📱 Connect to 'SurfLamp-Setup' network");
    Serial.println("🌐 Password: surf123456");

    apModeStartTime = millis();

    httpServer.on("/", HTTP_GET, []() {
        String htmlResponse = createConfigurationWebPage();
        httpServer.send(200, "text/html", htmlResponse);
    });

    httpServer.on("/save", HTTP_POST, []() {
        handleWifiCredentialsSave();
    });

    httpServer.begin();
    Serial.println("🌐 Configuration server started");
}

String createConfigurationWebPage() {
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

    return html;
}

void handleWifiCredentialsSave() {
    if (!httpServer.hasArg("ssid") || !httpServer.hasArg("password")) {
        httpServer.send(400, "text/html", "<h1>❌ Error: Missing WiFi credentials</h1>");
        return;
    }

    String newSsid = httpServer.arg("ssid");
    String newPassword = httpServer.arg("password");

    saveWifiCredentials(newSsid.c_str(), newPassword.c_str());

    String html = createConnectingResponsePage();
    httpServer.send(200, "text/html", html);

    delay(2000);

    attemptConnectionWithNewCredentials(newSsid, newPassword);
}

String createConnectingResponsePage() {
    String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
    html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
    html += "<title>Connecting...</title>";
    html += "<style>body{font-family:Arial;text-align:center;margin:40px;background:#f0f8ff;}</style>";
    html += "</head><body><h1>🔄 Connecting to WiFi...</h1>";
    html += "<p>Surf Lamp is connecting to your network.</p>";
    html += "<p>This page will close automatically.</p></body></html>";

    return html;
}

void attemptConnectionWithNewCredentials(const String& newSsid, const String& newPassword) {
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_STA);
    WiFi.begin(newSsid.c_str(), newPassword.c_str());

    Serial.printf("🔄 Connecting to: %s\n", newSsid.c_str());

    int connectionAttempts = 0;
    while (WiFi.status() != WL_CONNECTED && connectionAttempts < 20) {
        delay(1000);
        Serial.print(".");
        connectionAttempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ Connected to new WiFi!");
        Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());
        isConfigureWifiMode = false;
        setupHttpEndpoints();
    } else {
        Serial.println("\n❌ Failed to connect to new WiFi");
        startWifiConfigurationMode();
    }
}

void handleAccessPointTimeout() {
    if (isConfigureWifiMode && (millis() - apModeStartTime > AP_TIMEOUT)) {
        Serial.println("⏰ AP mode timeout - retrying WiFi connection");
        isConfigureWifiMode = false;

        while (!connectToWifi()) {
            Serial.println("🔄 Retrying WiFi connection in 5 seconds...");
            delay(5000);
        }
    }
}

// ============================================================================
// LED STATUS AND CONTROL FUNCTIONS
// ============================================================================

void blinkStatusLed(CRGB color, int delayMs) {
    static unsigned long lastBlinkTime = 0;
    static bool isLedOn = false;
    unsigned long currentTime = millis();

    if (currentTime - lastBlinkTime >= delayMs) {
        lastBlinkTime = currentTime;
        isLedOn = !isLedOn;
        ledsCenterStrip[0] = isLedOn ? color : CRGB::Black;
        FastLED.show();
    }
}

void blinkBlueLed()   { blinkStatusLed(CRGB::Blue);   }
void blinkGreenLed()  { blinkStatusLed(CRGB::Green);  }
void blinkRedLed()    { blinkStatusLed(CRGB::Red);    }
void blinkYellowLed() { blinkStatusLed(CRGB::Yellow); }

void clearAllLeds() {
    FastLED.clear();
    FastLED.show();
}

void setStatusLed(CRGB color) {
    ledsCenterStrip[0] = color;
    FastLED.show();
}

// ============================================================================
// LED DISPLAY FUNCTIONS
// ============================================================================

void updateLedsWithColorMap(int numActiveLeds, int segmentLength, CRGB* leds, const CHSV* colorMap) {
    if (!leds || !colorMap || numActiveLeds < 0 || segmentLength < 0) {
        return;
    }

    for (int i = 0; i < segmentLength; i++) {
        int colorIndex = map(i, 0, segmentLength - 1, 0, 23);
        if (i < numActiveLeds) {
            leds[i] = CHSV(colorMap[colorIndex].hue, colorMap[colorIndex].sat, colorMap[colorIndex].val);
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void updateBlinkingLeds(int numActiveLeds, int segmentLength, CRGB* leds, CHSV baseColor) {
    if (!leds || numActiveLeds < 0 || segmentLength < 0) {
        return;
    }

    float brightnessFactor = 0.95 + 0.25 * sin(blinkAnimationPhase);
    int adjustedBrightness = min(255, (int)(baseColor.val * brightnessFactor));

    for (int i = 0; i < segmentLength; i++) {
        if (i < numActiveLeds) {
            leds[i] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void updateBlinkingCenterLeds(int numActiveLeds, CHSV baseColor) {
    if (numActiveLeds < 0) {
        return;
    }

    float brightnessFactor = 0.95 + 0.25 * sin(blinkAnimationPhase);
    int adjustedBrightness = min(255, (int)(baseColor.val * brightnessFactor));

    for (int i = 1; i < NUM_LEDS_CENTER - 1; i++) {
        if (i < numActiveLeds + 1) {
            ledsCenterStrip[i] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            ledsCenterStrip[i] = CRGB::Black;
        }
    }
}

void updateLedsWithSingleColor(int numActiveLeds, int segmentLength, CRGB* leds, CHSV color) {
    if (!leds || numActiveLeds < 0 || segmentLength < 0) {
        return;
    }

    for (int i = 0; i < segmentLength; i++) {
        if (i < numActiveLeds) {
            leds[i] = color;
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void applyWindSpeedThreshold(int windSpeedLeds, int windSpeedMps, int windSpeedThresholdKnots) {
    if (windSpeedLeds < 0 || windSpeedMps < 0 || windSpeedThresholdKnots < 0) {
        return;
    }

    float windSpeedInKnots = windSpeedMps * 1.94384;

    if (windSpeedInKnots >= windSpeedThresholdKnots) {
        updateBlinkingCenterLeds(windSpeedLeds, CHSV(120, 255, min(255, (int)(255 * 1.6))));
    } else {
        updateLedsWithSingleColor(windSpeedLeds, NUM_LEDS_CENTER - 2, ledsCenterStrip, CHSV(120, 255, 255));
    }
}

void applyWaveHeightThreshold(int waveHeightLeds, int waveHeightCm, int waveThresholdCm) {
    if (waveHeightLeds < 0 || waveHeightCm < 0 || waveThresholdCm < 0) {
        return;
    }

    if (waveHeightCm >= waveThresholdCm) {
        updateBlinkingLeds(waveHeightLeds, NUM_LEDS_RIGHT, ledsSideRight, CHSV(0, 0, min(255, (int)(255 * 1.6))));
    } else {
        updateLedsWithSingleColor(waveHeightLeds, NUM_LEDS_RIGHT, ledsSideRight, CHSV(0, 0, 255));
    }
}

void updateBlinkingAnimation() {
    if (!currentSurfData.dataReceived) {
        return;
    }

    unsigned long currentTime = millis();
    if (currentTime - lastBlinkUpdateTime >= 5) {
        blinkAnimationPhase += 0.2094;
        if (blinkAnimationPhase >= 2 * PI) {
            blinkAnimationPhase = 0.0;
        }
        lastBlinkUpdateTime = currentTime;
    }

    bool needsUpdate = false;

    float windSpeedInKnots = currentSurfData.windSpeed * 1.94384;
    if (windSpeedInKnots >= currentSurfData.windSpeedThreshold) {
        int windSpeedLeds = constrain(static_cast<int>(currentSurfData.windSpeed * (1.94384 / 2.0)) + 1, 0, NUM_LEDS_CENTER - 2);
        updateBlinkingCenterLeds(windSpeedLeds, CHSV(120, 255, min(255, (int)(255 * 1.6))));
        needsUpdate = true;
    }

    if (currentSurfData.waveHeight >= currentSurfData.waveThreshold) {
        int waveHeightLeds = constrain(static_cast<int>(currentSurfData.waveHeight / 25) + 1, 0, NUM_LEDS_RIGHT);
        updateBlinkingLeds(waveHeightLeds, NUM_LEDS_RIGHT, ledsSideRight, CHSV(0, 0, min(255, (int)(255 * 1.6))));
        needsUpdate = true;
    }

    if (needsUpdate) {
        FastLED.show();
    }
}

void setWindDirectionIndicator(int windDirection) {
    if (windDirection < 0 || windDirection >= 360) {
        return;
    }

    Serial.printf("🐛 DEBUG: Wind direction = %d°\n", windDirection);
    int northLedIndex = NUM_LEDS_CENTER - 1;

    if (windDirection < 45 || windDirection >= 315) {
        ledsCenterStrip[northLedIndex] = CRGB::Green;
    } else if (windDirection >= 45 && windDirection < 135) {
        ledsCenterStrip[northLedIndex] = CRGB::Yellow;
    } else if (windDirection >= 135 && windDirection < 225) {
        ledsCenterStrip[northLedIndex] = CRGB::Red;
    } else if (windDirection >= 225 && windDirection < 315) {
        ledsCenterStrip[northLedIndex] = CRGB::Blue;
    }
}

void performLedTestSequence() {
    Serial.println("🧪 Running LED test sequence...");

    updateLedsWithColorMap(NUM_LEDS_CENTER, NUM_LEDS_CENTER, ledsCenterStrip, WIND_COLOR_MAP);
    updateLedsWithColorMap(NUM_LEDS_RIGHT, NUM_LEDS_RIGHT, ledsSideRight, WAVE_COLOR_MAP);
    updateLedsWithColorMap(NUM_LEDS_LEFT, NUM_LEDS_LEFT, ledsSideLeft, BASE_COLOR_MAP);
    FastLED.show();

    delay(2000);

    for (int hue = 0; hue < 256; hue += 5) {
        fill_solid(ledsCenterStrip, NUM_LEDS_CENTER, CHSV(hue, 255, 255));
        fill_solid(ledsSideRight, NUM_LEDS_RIGHT, CHSV(hue + 85, 255, 255));
        fill_solid(ledsSideLeft, NUM_LEDS_LEFT, CHSV(hue + 170, 255, 255));
        FastLED.show();
        delay(20);
    }

    clearAllLeds();
    Serial.println("✅ LED test completed");
}

// ============================================================================
// SURF DATA FETCHING AND PROCESSING
// ============================================================================

bool fetchSurfDataFromServer() {
    String apiServer = serverDiscovery.getApiServer();
    if (apiServer.length() == 0) {
        Serial.println("❌ No API server available for fetching data");
        return false;
    }

    HTTPClient httpClient;
    WiFiClientSecure secureClient;

    String apiUrl = "https://" + apiServer + "/api/arduino/" + String(ARDUINO_ID) + "/data";
    Serial.println("🌐 Fetching surf data from: " + apiUrl);

    secureClient.setInsecure();
    httpClient.begin(secureClient, apiUrl);
    httpClient.setTimeout(15000);

    int httpResponseCode = httpClient.GET();

    if (httpResponseCode == HTTP_CODE_OK) {
        String responsePayload = httpClient.getString();
        httpClient.end();

        Serial.println("📥 Received surf data from server");
        return processSurfDataJson(responsePayload);
    } else {
        Serial.printf("❌ HTTP error fetching surf data: %d (%s)\n",
                     httpResponseCode, httpClient.errorToString(httpResponseCode).c_str());
        httpClient.end();
        return false;
    }
}

bool processSurfDataJson(const String &jsonData) {
    if (jsonData.length() == 0) {
        Serial.println("❌ Empty JSON data received");
        return false;
    }

    DynamicJsonDocument jsonDocument(1024);
    DeserializationError parseError = deserializeJson(jsonDocument, jsonData);

    if (parseError) {
        Serial.printf("❌ JSON parsing failed: %s\n", parseError.c_str());
        return false;
    }

    int waveHeightCm = jsonDocument["wave_height_cm"] | 0;
    float wavePeriodS = jsonDocument["wave_period_s"] | 0.0;
    int windSpeedMps = jsonDocument["wind_speed_mps"] | 0;
    int windDirectionDeg = jsonDocument["wind_direction_deg"] | 0;
    int waveThresholdCm = jsonDocument["wave_threshold_cm"] | 100;
    int windSpeedThresholdKnots = jsonDocument["wind_speed_threshold_knots"] | 15;

    Serial.println("🌊 Surf Data Received:");
    Serial.printf("   Wave Height: %d cm\n", waveHeightCm);
    Serial.printf("   Wave Period: %.1f s\n", wavePeriodS);
    Serial.printf("   Wind Speed: %d m/s\n", windSpeedMps);
    Serial.printf("   Wind Direction: %d°\n", windDirectionDeg);
    Serial.printf("   Wave Threshold: %d cm\n", waveThresholdCm);
    Serial.printf("   Wind Speed Threshold: %d knots\n", windSpeedThresholdKnots);

    updateSurfDisplay(waveHeightCm, wavePeriodS, windSpeedMps, windDirectionDeg,
                     waveThresholdCm, windSpeedThresholdKnots);

    currentSurfData.waveHeight = waveHeightCm / 100.0;
    currentSurfData.wavePeriod = wavePeriodS;
    currentSurfData.windSpeed = windSpeedMps;
    currentSurfData.windDirection = windDirectionDeg;
    currentSurfData.waveThreshold = waveThresholdCm;
    currentSurfData.windSpeedThreshold = windSpeedThresholdKnots;
    currentSurfData.lastUpdate = millis();
    currentSurfData.dataReceived = true;

    return true;
}

void updateSurfDisplay(int waveHeightCm, float wavePeriod, int windSpeed, int windDirection,
                      int waveThresholdCm, int windSpeedThresholdKnots) {
    if (waveHeightCm < 0 || wavePeriod < 0 || windSpeed < 0 || windDirection < 0) {
        Serial.println("❌ Invalid surf data parameters");
        return;
    }

    int windSpeedLeds = constrain(static_cast<int>(windSpeed * (1.94384 / 2.0)) + 1, 0, NUM_LEDS_CENTER - 2);
    int waveHeightLeds = constrain(static_cast<int>(waveHeightCm / 25) + 1, 0, NUM_LEDS_RIGHT);
    int wavePeriodLeds = constrain(static_cast<int>(wavePeriod), 0, NUM_LEDS_LEFT);

    setWindDirectionIndicator(windDirection);
    updateLedsWithSingleColor(wavePeriodLeds, NUM_LEDS_LEFT, ledsSideLeft, CHSV(60, 255, 255));

    applyWindSpeedThreshold(windSpeedLeds, windSpeed, windSpeedThresholdKnots);
    applyWaveHeightThreshold(waveHeightLeds, waveHeightCm, waveThresholdCm);

    FastLED.show();

    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d° [Wave Threshold: %dcm, Wind Threshold: %dkts]\n",
                  windSpeedLeds, waveHeightLeds, wavePeriodLeds, windDirection, waveThresholdCm, windSpeedThresholdKnots);
}

// ============================================================================
// HTTP SERVER ENDPOINTS
// ============================================================================

void setupHttpEndpoints() {
    httpServer.on("/api/update", HTTP_POST, handleSurfDataUpdateRequest);
    httpServer.on("/api/status", HTTP_GET, handleStatusRequest);
    httpServer.on("/api/test", HTTP_GET, handleTestRequest);
    httpServer.on("/api/led-test", HTTP_GET, handleLedTestRequest);
    httpServer.on("/api/info", HTTP_GET, handleDeviceInfoRequest);
    httpServer.on("/api/fetch", HTTP_GET, handleManualFetchRequest);
    httpServer.on("/api/discovery-test", HTTP_GET, handleDiscoveryTestRequest);

    httpServer.begin();
    Serial.println("🌐 HTTP server started with endpoints:");
    Serial.println("   POST /api/update    - Receive surf data");
    Serial.println("   GET  /api/discovery-test - Test server discovery");
    Serial.println("   GET  /api/status    - Device status");
    Serial.println("   GET  /api/test      - Connection test");
    Serial.println("   GET  /api/led-test  - LED test");
    Serial.println("   GET  /api/info      - Device information");
    Serial.println("   GET  /api/fetch     - Manual surf data fetch");
}

void handleSurfDataUpdateRequest() {
    Serial.println("📥 Received surf data request");

    if (!httpServer.hasArg("plain")) {
        httpServer.send(400, "application/json", "{\"ok\":false}");
        Serial.println("❌ No JSON data in request");
        return;
    }

    String jsonData = httpServer.arg("plain");
    Serial.println("📋 Raw JSON data:");
    Serial.println(jsonData);

    if (processSurfDataJson(jsonData)) {
        httpServer.send(200, "application/json", "{\"ok\":true}");
        Serial.println("✅ Surf data processed successfully");
    } else {
        httpServer.send(400, "application/json", "{\"ok\":false}");
        Serial.println("❌ Failed to process surf data");
    }
}

void handleStatusRequest() {
    DynamicJsonDocument statusDocument(1024);

    statusDocument["arduino_id"] = ARDUINO_ID;
    statusDocument["status"] = "online";
    statusDocument["wifi_connected"] = WiFi.status() == WL_CONNECTED;
    statusDocument["ip_address"] = WiFi.localIP().toString();
    statusDocument["ssid"] = WiFi.SSID();
    statusDocument["signal_strength"] = WiFi.RSSI();
    statusDocument["uptime_ms"] = millis();
    statusDocument["free_heap"] = ESP.getFreeHeap();
    statusDocument["chip_model"] = ESP.getChipModel();
    statusDocument["firmware_version"] = "1.0.0";

    statusDocument["last_surf_data"]["received"] = currentSurfData.dataReceived;
    statusDocument["last_surf_data"]["wave_height_m"] = currentSurfData.waveHeight;
    statusDocument["last_surf_data"]["wave_period_s"] = currentSurfData.wavePeriod;
    statusDocument["last_surf_data"]["wind_speed_mps"] = currentSurfData.windSpeed;
    statusDocument["last_surf_data"]["wind_direction_deg"] = currentSurfData.windDirection;
    statusDocument["last_surf_data"]["wave_threshold_cm"] = currentSurfData.waveThreshold;
    statusDocument["last_surf_data"]["wind_speed_threshold_knots"] = currentSurfData.windSpeedThreshold;
    statusDocument["last_surf_data"]["last_update_ms"] = currentSurfData.lastUpdate;

    String statusJson;
    serializeJson(statusDocument, statusJson);

    httpServer.send(200, "application/json", statusJson);
    Serial.println("📊 Status request served");
}

void handleTestRequest() {
    DynamicJsonDocument testDocument(256);
    testDocument["status"] = "ok";
    testDocument["message"] = "Arduino is responding";
    testDocument["arduino_id"] = ARDUINO_ID;
    testDocument["timestamp"] = millis();

    String testJson;
    serializeJson(testDocument, testJson);

    httpServer.send(200, "application/json", testJson);
    Serial.println("🧪 Test request served");
}

void handleLedTestRequest() {
    Serial.println("🧪 LED test requested via HTTP");
    performLedTestSequence();

    httpServer.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LED test completed\"}");
}

void handleDeviceInfoRequest() {
    DynamicJsonDocument infoDocument(512);

    infoDocument["device_name"] = "Surf Lamp";
    infoDocument["arduino_id"] = ARDUINO_ID;
    infoDocument["model"] = ESP.getChipModel();
    infoDocument["revision"] = ESP.getChipRevision();
    infoDocument["cores"] = ESP.getChipCores();
    infoDocument["flash_size"] = ESP.getFlashChipSize();
    infoDocument["psram_size"] = ESP.getPsramSize();
    infoDocument["firmware_version"] = "1.0.0";
    infoDocument["led_strips"]["center"] = NUM_LEDS_CENTER;
    infoDocument["led_strips"]["right"] = NUM_LEDS_RIGHT;
    infoDocument["led_strips"]["left"] = NUM_LEDS_LEFT;

    String infoJson;
    serializeJson(infoDocument, infoJson);

    httpServer.send(200, "application/json", infoJson);
    Serial.println("ℹ️ Device info request served");
}

void handleDiscoveryTestRequest() {
    Serial.println("🧪 Discovery test requested");

    bool discoveryResult = serverDiscovery.forceDiscovery();
    String currentServer = serverDiscovery.getCurrentServer();

    String response = "{\"server\":\"" + currentServer + "\"}";
    httpServer.send(200, "application/json", response);
}

void handleManualFetchRequest() {
    Serial.println("🔄 Manual surf data fetch requested");

    if (fetchSurfDataFromServer()) {
        lastDataFetchTime = millis();
        httpServer.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Surf data fetched successfully\"}");
        Serial.println("✅ Manual fetch successful");
    } else {
        httpServer.send(500, "application/json", "{\"status\":\"error\",\"message\":\"Failed to fetch surf data\"}");
        Serial.println("❌ Manual fetch failed");
    }
}

// ============================================================================
// INITIALIZATION FUNCTIONS
// ============================================================================

void initializeLedStrips() {
    FastLED.addLeds<LED_TYPE, LED_PIN_CENTER, COLOR_ORDER>(ledsCenterStrip, NUM_LEDS_CENTER);
    FastLED.addLeds<LED_TYPE, LED_PIN_SIDE, COLOR_ORDER>(ledsSideRight, NUM_LEDS_RIGHT);
    FastLED.addLeds<LED_TYPE, LED_PIN_SIDE_LEFT, COLOR_ORDER>(ledsSideLeft, NUM_LEDS_LEFT);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    Serial.println("💡 LED strips initialized");
}

void initializeHardware() {
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    initializeLedStrips();
    performLedTestSequence();
    preferences.begin("wifi-creds", false);
}

void attemptInitialDataFetch() {
    Serial.println("🔄 Attempting initial surf data fetch...");
    if (fetchSurfDataFromServer()) {
        Serial.println("✅ Initial surf data fetch successful");
        lastDataFetchTime = millis();
    } else {
        Serial.println("⚠️ Initial surf data fetch failed, will retry later");
    }
}

// ============================================================================
// MAIN SETUP FUNCTION
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌊 ========================================");
    Serial.println("🌊 SURF LAMP - HTTP SERVER ARCHITECTURE");
    Serial.println("🌊 ========================================");
    Serial.printf("🔧 Arduino ID: %d\n", ARDUINO_ID);

    initializeHardware();

    if (!connectToWifi()) {
        Serial.println("🔧 Starting configuration mode...");
        startWifiConfigurationMode();
    } else {
        Serial.println("🚀 Surf Lamp ready for operation!");
        Serial.printf("📍 Device accessible at: http://%s\n", WiFi.localIP().toString().c_str());
        attemptInitialDataFetch();
    }
}

// ============================================================================
// MAIN LOOP FUNCTION
// ============================================================================

void loop() {
    httpServer.handleClient();
    handleAccessPointTimeout();

    if (WiFi.status() != WL_CONNECTED) {
        handleWifiDisconnection();
    } else {
        handleWifiConnectedState();
    }

    delay(100);
}

// ============================================================================
// LOOP HELPER FUNCTIONS
// ============================================================================

void handleWifiDisconnection() {
    if (!isConfigureWifiMode) {
        blinkRedLed();
        static unsigned long lastReconnectAttempt = 0;
        if (millis() - lastReconnectAttempt > 30000) {
            Serial.println("🔄 Attempting WiFi reconnection...");
            connectToWifi();
            lastReconnectAttempt = millis();
        }
    } else {
        blinkYellowLed();
    }
}

void handleWifiConnectedState() {
    if (isConfigureWifiMode) {
        isConfigureWifiMode = false;
        Serial.println("✅ Exited configuration mode");
    }

    handlePeriodicDataFetch();
    updateBlinkingAnimation();
    handleStatusIndication();
}

void handlePeriodicDataFetch() {
    if (millis() - lastDataFetchTime > FETCH_INTERVAL) {
        Serial.println("🔄 Time to fetch new surf data...");
        if (fetchSurfDataFromServer()) {
            Serial.println("✅ Surf data fetch successful");
            lastDataFetchTime = millis();
        } else {
            Serial.println("❌ Surf data fetch failed, will retry later");
            lastDataFetchTime = millis();
        }
    }
}

void handleStatusIndication() {
    if (currentSurfData.dataReceived && (millis() - currentSurfData.lastUpdate < 1800000)) {
        blinkGreenLed();
    } else {
        blinkStatusLed(CRGB::Blue, 1000);
    }
}