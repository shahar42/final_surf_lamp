#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <HTTPClient.h>

// ---------------------------- Configuration ----------------------------
#define BUTTON_PIN 0  // ESP32 boot button
#define LED_PIN_CENTER 4
#define LED_PIN_SIDE 2
#define LED_PIN_SIDE_LEFT 5

#define NUM_LEDS_RIGHT 9
#define NUM_LEDS_LEFT 9
#define NUM_LEDS_CENTER 12
#define BRIGHTNESS 100
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

#define WIFI_TIMEOUT 30  // Timeout for WiFi connection in seconds

// Device Configuration
const int ARDUINO_ID = 4433;  // ✨ CHANGE THIS for each Arduino device
const char* FLASK_APP_URL = "https://your-flask-app.onrender.com";  // ✨ CHANGE THIS to your Flask URL

// Global Variables
Preferences preferences;
WebServer server(80);
bool configure_wifi = false;
unsigned long apStartTime = 0;
const unsigned long AP_TIMEOUT = 60000;  // 60 seconds timeout

// Wi-Fi credentials (defaults)
char ssid[32] = "Your_SSID";
char password[64] = "Your_Password";

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
    unsigned long lastUpdate = 0;
    bool dataReceived = false;
} lastSurfData;

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

void blinkStatusLED(CRGB color, int delayMs = 500) {
    static unsigned long lastBlinkTime = 0;
    static bool ledOn = false;
    unsigned long currentMillis = millis();

    if (currentMillis - lastBlinkTime >= delayMs) {
        lastBlinkTime = currentMillis;
        ledOn = !ledOn;
        leds_center[0] = ledOn ? color : CRGB::Black;
        FastLED.show();
    }
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

void updateLEDsOneColor(int numActiveLeds, int segmentLen, CRGB* leds, CHSV color) {
    for (int i = 0; i < segmentLen; i++) {
        if (i < numActiveLeds) {
            leds[i] = color;
        } else {
            leds[i] = CRGB::Black;
        }
    }
}

void setWindDirection(int windDirection) {
    int northLED = NUM_LEDS_CENTER - 1;

    // Wind direction color coding
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

void updateSurfDisplay(float waveHeight, float wavePeriod, float windSpeed, int windDirection, float waveThreshold = 1.0) {
    // Calculate LED counts based on surf data
    int windSpeedLEDs = constrain(static_cast<int>(windSpeed * 1.3) + 1, 0, NUM_LEDS_CENTER - 1);
    int waveHeightLEDs = constrain(static_cast<int>((waveHeight * 100) / 25) + 1, 0, NUM_LEDS_RIGHT);
    int wavePeriodLEDs = constrain(static_cast<int>(wavePeriod), 0, NUM_LEDS_LEFT);
    
    // Set wind direction and wind speed (always normal)
    setWindDirection(windDirection);
    updateLEDs(windSpeedLEDs, NUM_LEDS_CENTER - 1, leds_center, colorMapWind);
    updateLEDs(wavePeriodLEDs, NUM_LEDS_LEFT, leds_side_left, colorMap);
    
    // THRESHOLD LOGIC FOR WAVE HEIGHT LEDs ONLY
    if (waveHeight >= waveThreshold) {
        // ALERT MODE: 60% brighter wave height LEDs
        for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
            int colorIndex = map(i, 0, NUM_LEDS_RIGHT - 1, 0, 23);
            if (i < waveHeightLEDs) {
                CHSV color = colorMapWave[colorIndex];
                color.val = min(255, color.val * 1.6); // 60% brighter
                leds_side_right[i] = color;
            } else {
                leds_side_right[i] = CRGB::Black;
            }
        }
    } else {
        // NORMAL MODE: Standard wave height visualization
        updateLEDs(waveHeightLEDs, NUM_LEDS_RIGHT, leds_side_right, colorMapWave);
    }
    
    FastLED.show();
    
    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d° [Threshold: %.1fm]\n", 
                  windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, windDirection, waveThreshold);
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
    // Only endpoint needed - receive surf data from background processor
    server.on("/api/update", HTTP_POST, handleSurfDataUpdate);
    
    server.begin();
    Serial.println("🌐 HTTP server started");
}

void handleSurfDataUpdate() {
    if (!server.hasArg("plain")) {
        server.send(400, "text/plain", "No data");
        return;
    }

    String jsonData = server.arg("plain");
    
    if (processSurfData(jsonData)) {
        server.send(200, "text/plain", "OK");
    } else {
        server.send(400, "text/plain", "Error");
    }
}


// ---------------------------- Surf Data Processing ----------------------------

bool processSurfData(const String &jsonData) {
    DynamicJsonDocument doc(512);
    if (deserializeJson(doc, jsonData)) return false;
    
    // Extract surf data
    float waveHeight = doc["wave_height_m"] | 0.0;
    float wavePeriod = doc["wave_period_s"] | 0.0;
    float windSpeed = doc["wind_speed_mps"] | 0.0;
    int windDirection = doc["wind_direction_deg"] | 0;
    float waveThreshold = doc["wave_threshold_m"] | 1.0;
    
    // Update LEDs
    updateSurfDisplay(waveHeight, wavePeriod, windSpeed, windDirection, waveThreshold);
    
    // Store for tracking
    lastSurfData.waveHeight = waveHeight;
    lastSurfData.wavePeriod = wavePeriod;
    lastSurfData.windSpeed = windSpeed;
    lastSurfData.windDirection = windDirection;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    
    // Send callback
    sendCallbackToFlask();
    
    return true;
}

void sendCallbackToFlask(float waveHeight, float wavePeriod, float windSpeed, int windDirection) {
    if (!WiFi.isConnected()) {
        Serial.println("⚠️ WiFi not connected - skipping callback");
        return;
    }

    HTTPClient http;
    String callbackURL = String(FLASK_APP_URL) + "/api/arduino/callback";
    
    Serial.printf("📤 Sending callback to: %s\n", callbackURL.c_str());
    
    http.begin(callbackURL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000); // 10 second timeout
    
    // Create simple callback payload - just acknowledgment
    DynamicJsonDocument callbackDoc(256);
    callbackDoc["arduino_id"] = ARDUINO_ID;
    callbackDoc["data_received"] = true;
    callbackDoc["local_ip"] = WiFi.localIP().toString();
    
    String callbackJson;
    serializeJson(callbackDoc, callbackJson);
    
    Serial.println("📋 Callback payload:");
    Serial.println(callbackJson);
    
    int httpCode = http.POST(callbackJson);
    
    if (httpCode > 0) {
        String response = http.getString();
        Serial.printf("📥 Flask response (%d): %s\n", httpCode, response.c_str());
        
        if (httpCode == 200) {
            Serial.println("✅ Callback sent successfully");
            setStatusLED(CRGB::Green);
        } else {
            Serial.printf("⚠️ Flask returned HTTP %d\n", httpCode);
            setStatusLED(CRGB::Orange);
        }
    } else {
        Serial.printf("❌ HTTP request failed: %s\n", http.errorToString(httpCode).c_str());
        setStatusLED(CRGB::Red);
    }
    
    http.end();
}

// ---------------------------- Setup Function ----------------------------

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n🌊 ========================================");
    Serial.println("🌊 SURF LAMP - HTTP SERVER ARCHITECTURE");
    Serial.println("🌊 ========================================");
    Serial.printf("🔧 Arduino ID: %d\n", ARDUINO_ID);
    Serial.printf("🌐 Flask URL: %s\n", FLASK_APP_URL);
    
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
        Serial.println("📥 Waiting for surf data from background processor...");
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
        
        // Status indication based on data freshness
        if (lastSurfData.dataReceived && (millis() - lastSurfData.lastUpdate < 1800000)) { // 30 minutes
            blinkGreenLED(); // Fresh data
        } else {
            blinkStatusLED(CRGB::Blue, 1000); // No recent data
        }
    }
    
    delay(100); // Small delay to prevent excessive CPU usage
}
