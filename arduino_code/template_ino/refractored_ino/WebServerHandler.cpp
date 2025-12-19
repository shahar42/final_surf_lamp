#include "WebServerHandler.h"

// Helper instance for calculations
static LEDMappingConfig ledMapping;

WebServerHandler::WebServerHandler(SurfData& surfData, LedController& ledController, WiFiHandler& wifiHandler, ServerDiscovery& serverDiscovery)
    : server(80), _surfData(surfData), _ledController(ledController), _wifiHandler(wifiHandler), _serverDiscovery(serverDiscovery) {
}

void WebServerHandler::setup() {
    server.on("/api/update", HTTP_POST, [this]() { handleSurfDataUpdate(); });
    server.on("/api/status", HTTP_GET, [this]() { handleStatusRequest(); });
    server.on("/api/test", HTTP_GET, [this]() { handleTestRequest(); });
    server.on("/api/led-test", HTTP_GET, [this]() { handleLEDTestRequest(); });
    server.on("/api/status-led-test", HTTP_GET, [this]() { handleStatusLEDTestRequest(); });
    server.on("/api/info", HTTP_GET, [this]() { handleDeviceInfoRequest(); });
    server.on("/api/fetch", HTTP_GET, [this]() { handleManualFetchRequest(); });
    server.on("/api/wifi-diagnostics", HTTP_GET, [this]() { handleWiFiDiagnostics(); });
    server.on("/api/discovery-test", HTTP_GET, [this]() { handleDiscoveryTest(); });

    server.begin();
    Serial.println("🌐 HTTP server started");
}

void WebServerHandler::handleClient() {
    server.handleClient();
}

// ---------------------------- Handlers ----------------------------

void WebServerHandler::handleSurfDataUpdate() {
    if (!server.hasArg("plain")) {
        server.send(400, "application/json", "{\"ok\":false}");
        return;
    }
    if (processSurfData(server.arg("plain"))) {
        server.send(200, "application/json", "{\"ok\":true}");
    } else {
        server.send(400, "application/json", "{\"ok\":false}");
    }
}

void WebServerHandler::handleStatusRequest() {
    DynamicJsonDocument statusDoc(1024);

    statusDoc["arduino_id"] = ARDUINO_ID;
    statusDoc["status"] = "online";
    statusDoc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
    statusDoc["ip_address"] = WiFi.localIP().toString();
    statusDoc["uptime_ms"] = millis();
    statusDoc["free_heap"] = ESP.getFreeHeap();

    // Last surf data
    statusDoc["last_surf_data"]["received"] = _surfData.dataReceived;
    statusDoc["last_surf_data"]["wave_height_m"] = _surfData.waveHeight;
    statusDoc["last_surf_data"]["wave_period_s"] = _surfData.wavePeriod;
    statusDoc["last_surf_data"]["wind_speed_mps"] = _surfData.windSpeed;
    statusDoc["last_surf_data"]["quiet_hours_active"] = _surfData.quietHoursActive;

    // Fetch timing
    statusDoc["fetch_info"]["last_fetch_ms"] = lastDataFetch;
    statusDoc["fetch_info"]["time_since_last_fetch_ms"] = millis() - lastDataFetch;

    // Debug calcs
    if (_surfData.dataReceived) {
        int windSpeedLEDs = ledMapping.calculateWindLEDs(_surfData.windSpeed);
        statusDoc["led_calculations"]["wind_speed_leds"] = windSpeedLEDs;
    }

    String statusJson;
    serializeJson(statusDoc, statusJson);
    server.send(200, "application/json", statusJson);
}

void WebServerHandler::handleTestRequest() {
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Arduino is responding\"}");
}

void WebServerHandler::handleLEDTestRequest() {
    _ledController.performLEDTest();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LED test completed\"}");
}

void WebServerHandler::handleStatusLEDTestRequest() {
    _ledController.testAllStatusLEDStates();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Status LED test completed\"}");
}

void WebServerHandler::handleDeviceInfoRequest() {
    DynamicJsonDocument infoDoc(512);
    infoDoc["device_name"] = "Surf Lamp (Wooden)";
    infoDoc["arduino_id"] = ARDUINO_ID;
    infoDoc["firmware_version"] = "2.0.0-wooden-lamp-refactored";
    
    String infoJson;
    serializeJson(infoDoc, infoJson);
    server.send(200, "application/json", infoJson);
}

void WebServerHandler::handleManualFetchRequest() {
    if (fetchSurfDataFromServer()) {
        server.send(200, "application/json", "{\"status\":\"ok\"}");
    } else {
        server.send(500, "application/json", "{\"status\":\"error\"}");
    }
}

void WebServerHandler::handleWiFiDiagnostics() {
    DynamicJsonDocument doc(1024);
    doc["current_ssid"] = WiFi.SSID();
    doc["last_error"] = _wifiHandler.getLastWiFiError();
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void WebServerHandler::handleDiscoveryTest() {
    _serverDiscovery.forceDiscovery();
    String current = _serverDiscovery.getCurrentServer();
    server.send(200, "application/json", "{\"server\":\"" + current + "\"}");
}

// ---------------------------- Fetch Logic ----------------------------

bool WebServerHandler::fetchSurfDataFromServer() {
    String apiServer = _serverDiscovery.getApiServer();
    if (apiServer.length() == 0) return false;

    HTTPClient http;
    WiFiClientSecure client;
    String url = "https://" + apiServer + "/api/arduino/" + String(ARDUINO_ID) + "/data";

    client.setInsecure();
    http.begin(client, url);
    http.setTimeout(15000);

    int httpCode = http.GET();
    bool success = false;

    if (httpCode == HTTP_CODE_OK) {
        success = processSurfData(http.getString());
        if (success) lastDataFetch = millis();
    }
    http.end();
    return success;
}

bool WebServerHandler::processSurfData(const String& jsonData) {
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, jsonData);
    if (error) return false;

    _surfData.waveHeight = (doc["wave_height_cm"] | 0) / 100.0;
    _surfData.wavePeriod = doc["wave_period_s"] | 0.0;
    _surfData.windSpeed = doc["wind_speed_mps"] | 0;
    _surfData.windDirection = doc["wind_direction_deg"] | 0;
    _surfData.waveThreshold = (doc["wave_threshold_cm"] | 100) / 100.0;
    _surfData.windSpeedThreshold = doc["wind_speed_threshold_knots"] | 15;
    _surfData.quietHoursActive = doc["quiet_hours_active"] | false;
    _surfData.offHoursActive = doc["off_hours_active"] | false;
    _surfData.currentTheme = doc["led_theme"] | "day";
    
    _surfData.lastUpdate = millis();
    _surfData.dataReceived = true;
    _surfData.needsDisplayUpdate = true;

    return true;
}
