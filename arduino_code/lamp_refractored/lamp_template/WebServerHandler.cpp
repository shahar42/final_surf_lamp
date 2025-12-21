/*
 * WEB SERVER HANDLER - IMPLEMENTATION
 *
 * HTTP endpoint handlers for surf lamp.
 */

#include "WebServerHandler.h"
#include "LedController.h"
#include "ServerDiscovery.h"
#include "SunsetCalculator.h"

// Global timing variables (defined here, declared extern in header)
unsigned long lastDataFetch = 0;
const unsigned long FETCH_INTERVAL = 780000; // 13 minutes
const unsigned long DATA_STALENESS_THRESHOLD = 1800000; // 30 minutes (2 missed fetches + grace period)

// File-static server reference (set in setupHTTPEndpoints)
static WebServer* webServer = nullptr;

// File-static server discovery reference (set in main .ino, accessed via extern)
extern ServerDiscovery serverDiscovery;

// Sunset calculator (defined in main .ino)
extern SunsetCalculator sunsetCalc;

// WiFi diagnostic state (accessed via extern from WiFiHandler)
extern String lastWiFiError;
extern uint8_t lastDisconnectReason;

// ---------------- SERVER SETUP ----------------

void setupHTTPEndpoints(WebServer& server) {
    webServer = &server;  // Store reference for handlers

    // Main endpoint for receiving surf data from background processor
    server.on("/api/update", HTTP_POST, handleSurfDataUpdate);

    // Status endpoint for monitoring
    server.on("/api/status", HTTP_GET, handleStatusRequest);

    // Test endpoint for manual testing
    server.on("/api/test", HTTP_GET, handleTestRequest);

    // LED test endpoint
    server.on("/api/led-test", HTTP_GET, handleLEDTestRequest);

    // Status LED error state test endpoint
    server.on("/api/status-led-test", HTTP_GET, handleStatusLEDTestRequest);

    // Device info endpoint
    server.on("/api/info", HTTP_GET, handleDeviceInfoRequest);

    // Manual surf data fetch endpoint
    server.on("/api/fetch", HTTP_GET, handleManualFetchRequest);

    // WiFi diagnostics endpoint
    server.on("/api/wifi-diagnostics", HTTP_GET, handleWiFiDiagnostics);

    // Server discovery test endpoint
    server.on("/api/discovery-test", HTTP_GET, handleDiscoveryTest);

    server.begin();
    Serial.println("🌐 HTTP server started with endpoints:");
    Serial.println("   POST /api/update          - Receive surf data");
    Serial.println("   GET  /api/discovery-test  - Test server discovery");
    Serial.println("   GET  /api/status          - Device status");
    Serial.println("   GET  /api/test            - Connection test");
    Serial.println("   GET  /api/led-test        - LED test");
    Serial.println("   GET  /api/status-led-test - Test all error LED states");
    Serial.println("   GET  /api/info            - Device information");
    Serial.println("   GET  /api/fetch           - Manual surf data fetch");
    Serial.println("   GET  /api/wifi-diagnostics - WiFi connection diagnostics");
}

// ---------------- ENDPOINT HANDLERS ----------------

void handleSurfDataUpdate() {
    Serial.println("📥 Received surf data request");

    if (!webServer->hasArg("plain")) {
        webServer->send(400, "application/json", "{\"ok\":false}");
        Serial.println("❌ No JSON data in request");
        return;
    }

    String jsonData = webServer->arg("plain");
    Serial.println("📋 Raw JSON data:");
    Serial.println(jsonData);

    if (processSurfData(jsonData)) {
        webServer->send(200, "application/json", "{\"ok\":true}");
        Serial.println("✅ Surf data processed successfully");
    } else {
        webServer->send(400, "application/json", "{\"ok\":false}");
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
    statusDoc["firmware_version"] = "3.0.0-modular-template";

    // Last surf data
    statusDoc["last_surf_data"]["received"] = lastSurfData.dataReceived;
    statusDoc["last_surf_data"]["wave_height_m"] = lastSurfData.waveHeight;
    statusDoc["last_surf_data"]["wave_period_s"] = lastSurfData.wavePeriod;
    statusDoc["last_surf_data"]["wind_speed_mps"] = lastSurfData.windSpeed;
    statusDoc["last_surf_data"]["wind_direction_deg"] = lastSurfData.windDirection;
    statusDoc["last_surf_data"]["wave_threshold_m"] = lastSurfData.waveThreshold;
    statusDoc["last_surf_data"]["wind_speed_threshold_knots"] = lastSurfData.windSpeedThreshold;
    statusDoc["last_surf_data"]["quiet_hours_active"] = lastSurfData.quietHoursActive;
    statusDoc["last_surf_data"]["off_hours_active"] = lastSurfData.offHoursActive;
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

    webServer->send(200, "application/json", statusJson);
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

    webServer->send(200, "application/json", testJson);
    Serial.println("🧪 Test request served");
}

void handleLEDTestRequest() {
    Serial.println("🧪 LED test requested via HTTP");
    performLEDTest();

    webServer->send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LED test completed\"}");
}

void handleStatusLEDTestRequest() {
    Serial.println("🧪 Status LED test requested via HTTP");
    testAllStatusLEDStates();

    webServer->send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Status LED test completed\"}");
}

void handleDeviceInfoRequest() {
    DynamicJsonDocument infoDoc(512);

    infoDoc["device_name"] = "Surf Lamp (Modular Template)";
    infoDoc["arduino_id"] = ARDUINO_ID;
    infoDoc["model"] = ESP.getChipModel();
    infoDoc["revision"] = ESP.getChipRevision();
    infoDoc["cores"] = ESP.getChipCores();
    infoDoc["flash_size"] = ESP.getFlashChipSize();
    infoDoc["psram_size"] = ESP.getPsramSize();
    infoDoc["firmware_version"] = "3.0.0-modular-template";
    infoDoc["led_strips"]["wave_height"] = WAVE_HEIGHT_LENGTH;
    infoDoc["led_strips"]["wave_period"] = WAVE_PERIOD_LENGTH;
    infoDoc["led_strips"]["wind_speed"] = WIND_SPEED_LENGTH;
    infoDoc["led_strips"]["total"] = TOTAL_LEDS;

    String infoJson;
    serializeJson(infoDoc, infoJson);

    webServer->send(200, "application/json", infoJson);
    Serial.println("ℹ️ Device info request served");
}

void handleDiscoveryTest() {
    Serial.println("🧪 Discovery test requested");

    bool result = serverDiscovery.forceDiscovery();
    String current = serverDiscovery.getCurrentServer();

    String response = "{\"server\":\"" + current + "\"}";
    webServer->send(200, "application/json", response);
}

void handleManualFetchRequest() {
    Serial.println("🔄 Manual surf data fetch requested");

    if (fetchSurfDataFromServer()) {
        lastDataFetch = millis();
        webServer->send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Surf data fetched successfully\"}");
        Serial.println("✅ Manual fetch successful");
    } else {
        webServer->send(500, "application/json", "{\"status\":\"error\",\"message\":\"Failed to fetch surf data\"}");
        Serial.println("❌ Manual fetch failed");
    }
}

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

    webServer->send(200, "application/json", response);
    Serial.println("🔍 WiFi diagnostics request served");
}

// ---------------- DATA PROCESSING ----------------

bool processSurfData(const String& jsonData) {
    DynamicJsonDocument doc(JSON_CAPACITY);
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
    float brightness_multiplier = doc["brightness_multiplier"] | 0.6;
    String led_theme = doc["led_theme"] | "classic_surf";

    // V2 API: Extract location coordinates for autonomous sunset calculation
    float latitude = doc["latitude"] | 0.0;
    float longitude = doc["longitude"] | 0.0;
    int8_t tz_offset = doc["tz_offset"] | 0;

    // Update coordinates in sunset calculator (writes to flash only if changed)
    if (latitude != 0.0 && longitude != 0.0) {
        sunsetCalc.updateCoordinates(latitude, longitude, tz_offset);
    }

    Serial.println("🌊 Surf Data Received:");
    Serial.printf("   Wave Height: %d cm\n", wave_height_cm);
    Serial.printf("   Wave Period: %.1f s\n", wave_period_s);
    Serial.printf("   Wind Speed: %d m/s\n", wind_speed_mps);
    Serial.printf("   Wind Direction: %d°\n", wind_direction_deg);
    Serial.printf("   Wave Threshold: %d cm\n", wave_threshold_cm);
    Serial.printf("   Wind Speed Threshold: %d knots\n", wind_speed_threshold_knots);
    Serial.printf("   Quiet Hours Active: %s\n", quiet_hours_active ? "true" : "false");
    Serial.printf("   Off Hours Active: %s\n", off_hours_active ? "true" : "false");
    Serial.printf("   Brightness Multiplier: %.1f\n", brightness_multiplier);
    Serial.printf("   LED Theme: %s\n", led_theme.c_str());

    // Calculate LED counts for logging
    int windSpeedLEDs = ledMapping.calculateWindLEDs(wind_speed_mps);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(wave_height_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wave_period_s);

    // Log timestamp and LED counts
    Serial.printf("⏰ Timestamp: %lu ms (uptime)\n", millis());
    Serial.printf("💡 LEDs Active - Wind: %d, Wave: %d, Period: %d\n", windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs);

    // Update global state (converting height and threshold to meters for consistency)
    lastSurfData.waveHeight = wave_height_cm / 100.0;
    lastSurfData.wavePeriod = wave_period_s;
    lastSurfData.windSpeed = wind_speed_mps;
    lastSurfData.windDirection = wind_direction_deg;
    lastSurfData.waveThreshold = wave_threshold_cm / 100.0;  // Convert cm to meters for consistent comparison
    lastSurfData.windSpeedThreshold = wind_speed_threshold_knots;
    lastSurfData.quietHoursActive = quiet_hours_active;
    lastSurfData.offHoursActive = off_hours_active;
    lastSurfData.brightnessMultiplier = brightness_multiplier;
    lastSurfData.theme = led_theme;
    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;
    lastSurfData.needsDisplayUpdate = true;  // Signal to loop() that display needs refresh

    return true;
}

bool fetchSurfDataFromServer() {
    String apiServer = serverDiscovery.getApiServer();
    if (apiServer.length() == 0) {
        Serial.println("❌ No API server available for fetching data");
        return false;
    }

    HTTPClient http;
    WiFiClientSecure client;

    String url = "https://" + apiServer + "/api/arduino/v2/" + String(ARDUINO_ID) + "/data";
    Serial.println("🌐 Fetching surf data from: " + url);

    client.setInsecure();

    http.begin(client, url);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();

        // Extract Date header for time synchronization
        String dateHeader = http.header("Date");
        http.end();

        if (dateHeader.length() > 0) {
            Serial.println("📅 HTTP Date: " + dateHeader);
            sunsetCalc.parseAndUpdateTime(dateHeader);
            sunsetCalc.calculateSunset();
        }

        Serial.println("📥 Received surf data from server");
        return processSurfData(payload);
    } else {
        Serial.printf("❌ HTTP error fetching surf data: %d (%s)\n", httpCode, http.errorToString(httpCode).c_str());
        http.end();
        return false;
    }
}
