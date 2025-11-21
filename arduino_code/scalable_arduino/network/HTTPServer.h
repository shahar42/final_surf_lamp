/**
 * HTTPServer.h
 *
 * Provides HTTP REST API endpoints for device control and monitoring.
 *
 * ENDPOINTS:
 * - POST /api/update      - Receive surf data updates
 * - GET  /api/status      - Device status and metrics
 * - GET  /api/test        - Connection test
 * - GET  /api/led-test    - Trigger LED test sequence
 * - GET  /api/info        - Device hardware information
 * - GET  /api/fetch       - Manual surf data fetch
 * - GET  /api/discovery-test - Test server discovery
 * - GET  /                - WiFi configuration page (config mode only)
 * - POST /save            - Save WiFi credentials (config mode only)
 *
 * RESPONSIBILITIES:
 * - HTTP request handling
 * - JSON response formatting
 * - WiFi configuration web interface
 * - Publishing events for received commands
 *
 * EVENTS PUBLISHED:
 * - EVENT_DATA_RECEIVED (on /api/update)
 * - EVENT_LED_TEST_REQUESTED
 * - EVENT_MANUAL_FETCH_REQUESTED
 */

#ifndef HTTP_SERVER_H
#define HTTP_SERVER_H

#include <WebServer.h>
#include <ArduinoJson.h>
#include "../core/EventBus.h"
#include "../data/SurfDataModel.h"
#include "../config/SystemConfig.h"

// Forward declarations for dependencies
class WiFiManager;
class DataFetcher;
class ServerDiscovery;

class HTTPServer {
private:
    WebServer server;
    EventBus& eventBus;
    WiFiManager* wifiManager;
    DataFetcher* dataFetcher;
    ServerDiscovery* serverDiscovery;
    SurfData* surfData;
    int arduinoId;

public:
    /**
     * Constructor
     * @param events Reference to the global EventBus
     * @param deviceId Arduino device ID
     */
    HTTPServer(EventBus& events, int deviceId)
        : server(80), eventBus(events), arduinoId(deviceId),
          wifiManager(nullptr), dataFetcher(nullptr),
          serverDiscovery(nullptr), surfData(nullptr) {
        Serial.println("🌐 HTTPServer initialized");
    }

    /**
     * Inject dependencies (called after all components are created)
     */
    void setDependencies(WiFiManager* wifi, DataFetcher* fetcher,
                        ServerDiscovery* discovery, SurfData* data) {
        wifiManager = wifi;
        dataFetcher = fetcher;
        serverDiscovery = discovery;
        surfData = data;
    }

    /**
     * Setup HTTP endpoints and start server
     */
    void begin() {
        setupOperationalEndpoints();
        server.begin();
        Serial.println("🌐 HTTPServer: Operational endpoints ready");
    }

    /**
     * Setup configuration mode endpoints
     */
    void beginConfigMode() {
        setupConfigEndpoints();
        server.begin();
        Serial.println("🌐 HTTPServer: Config mode endpoints ready");
    }

    /**
     * Handle incoming HTTP requests (call in loop)
     */
    void handleClient() {
        server.handleClient();
    }

private:
    /**
     * Setup operational mode endpoints
     */
    void setupOperationalEndpoints() {
        server.on("/api/update", HTTP_POST, [this]() { handleSurfDataUpdate(); });
        server.on("/api/status", HTTP_GET, [this]() { handleStatusRequest(); });
        server.on("/api/test", HTTP_GET, [this]() { handleTestRequest(); });
        server.on("/api/led-test", HTTP_GET, [this]() { handleLEDTestRequest(); });
        server.on("/api/info", HTTP_GET, [this]() { handleDeviceInfoRequest(); });
        server.on("/api/fetch", HTTP_GET, [this]() { handleManualFetchRequest(); });
        server.on("/api/discovery-test", HTTP_GET, [this]() { handleDiscoveryTest(); });

        Serial.println("📋 HTTPServer endpoints:");
        Serial.println("   POST /api/update - Receive surf data");
        Serial.println("   GET  /api/status - Device status");
        Serial.println("   GET  /api/test - Connection test");
    }

    /**
     * Setup WiFi configuration mode endpoints
     */
    void setupConfigEndpoints() {
        server.on("/", HTTP_GET, [this]() { handleConfigPage(); });
        server.on("/save", HTTP_POST, [this]() { handleSaveCredentials(); });
    }

    /**
     * Handle POST /api/update - Receive surf data
     */
    void handleSurfDataUpdate() {
        Serial.println("📥 HTTPServer: Received /api/update");

        if (!server.hasArg("plain")) {
            server.send(400, "application/json", "{\"ok\":false,\"error\":\"no data\"}");
            return;
        }

        String jsonData = server.arg("plain");
        Serial.println("📋 Received " + String(jsonData.length()) + " bytes");

        // Publish event for DataProcessor to handle
        eventBus.publish(EVENT_DATA_RECEIVED, (void*)jsonData.c_str());

        server.send(200, "application/json", "{\"ok\":true}");
    }

    /**
     * Handle GET /api/status - Device status
     */
    void handleStatusRequest() {
        DynamicJsonDocument doc(1024);

        doc["arduino_id"] = arduinoId;
        doc["status"] = "online";
        doc["wifi_connected"] = wifiManager ? wifiManager->isConnected() : false;
        doc["ip_address"] = wifiManager ? wifiManager->getIPAddress() : "";
        doc["ssid"] = wifiManager ? wifiManager->getSSID() : "";
        doc["signal_strength"] = wifiManager ? wifiManager->getRSSI() : 0;
        doc["uptime_ms"] = millis();
        doc["free_heap"] = ESP.getFreeHeap();
        doc["firmware_version"] = SystemConfig::FIRMWARE_VERSION;

        if (surfData && surfData->isValid()) {
            doc["surf_data"]["wave_height_m"] = surfData->waveHeight;
            doc["surf_data"]["wave_period_s"] = surfData->wavePeriod;
            doc["surf_data"]["wind_speed_mps"] = surfData->windSpeed;
            doc["surf_data"]["wind_direction_deg"] = surfData->windDirection;
            doc["surf_data"]["last_update_ms"] = surfData->lastUpdate;
            doc["surf_data"]["quiet_hours"] = surfData->quietHoursActive;
        }

        String response;
        serializeJson(doc, response);
        server.send(200, "application/json", response);
        Serial.println("📊 HTTPServer: Served /api/status");
    }

    /**
     * Handle GET /api/test - Connection test
     */
    void handleTestRequest() {
        DynamicJsonDocument doc(256);
        doc["status"] = "ok";
        doc["message"] = "Arduino responding";
        doc["arduino_id"] = arduinoId;
        doc["timestamp"] = millis();

        String response;
        serializeJson(doc, response);
        server.send(200, "application/json", response);
        Serial.println("🧪 HTTPServer: Served /api/test");
    }

    /**
     * Handle GET /api/led-test - Trigger LED test
     */
    void handleLEDTestRequest() {
        Serial.println("🧪 HTTPServer: LED test requested");
        eventBus.publish(EVENT_LED_TEST_REQUESTED, nullptr);
        server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"LED test started\"}");
    }

    /**
     * Handle GET /api/info - Device information
     */
    void handleDeviceInfoRequest() {
        DynamicJsonDocument doc(512);

        doc["device_name"] = "Surf Lamp (Modular Architecture)";
        doc["arduino_id"] = arduinoId;
        doc["model"] = ESP.getChipModel();
        doc["revision"] = ESP.getChipRevision();
        doc["cores"] = ESP.getChipCores();
        doc["flash_size"] = ESP.getFlashChipSize();
        doc["firmware_version"] = SystemConfig::FIRMWARE_VERSION;
        doc["led_count"] = SystemConfig::TOTAL_LEDS;

        String response;
        serializeJson(doc, response);
        server.send(200, "application/json", response);
        Serial.println("ℹ️ HTTPServer: Served /api/info");
    }

    /**
     * Handle GET /api/fetch - Manual surf data fetch
     */
    void handleManualFetchRequest() {
        Serial.println("🔄 HTTPServer: Manual fetch requested");

        if (dataFetcher && dataFetcher->fetchSurfData()) {
            server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Data fetched\"}");
        } else {
            server.send(500, "application/json", "{\"status\":\"error\",\"message\":\"Fetch failed\"}");
        }
    }

    /**
     * Handle GET /api/discovery-test - Test server discovery
     */
    void handleDiscoveryTest() {
        if (!serverDiscovery) {
            server.send(500, "application/json", "{\"error\":\"No discovery service\"}");
            return;
        }

        serverDiscovery->forceDiscovery();
        String currentServer = serverDiscovery->getCurrentServer();

        String response = "{\"server\":\"" + currentServer + "\"}";
        server.send(200, "application/json", response);
        Serial.println("🧪 HTTPServer: Served /api/discovery-test");
    }

    /**
     * Handle GET / - WiFi configuration page
     */
    void handleConfigPage() {
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
    }

    /**
     * Handle POST /save - Save WiFi credentials
     */
    void handleSaveCredentials() {
        if (!server.hasArg("ssid") || !server.hasArg("password")) {
            server.send(400, "text/html", "<h1>❌ Missing credentials</h1>");
            return;
        }

        String newSSID = server.arg("ssid");
        String newPassword = server.arg("password");

        if (wifiManager) {
            wifiManager->saveCredentials(newSSID.c_str(), newPassword.c_str());
        }

        String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
        html += "<title>Connecting...</title>";
        html += "<style>body{font-family:Arial;text-align:center;margin:40px;background:#f0f8ff;}</style>";
        html += "</head><body><h1>🔄 Connecting to WiFi...</h1>";
        html += "<p>Surf Lamp is connecting to your network.</p></body></html>";

        server.send(200, "text/html", html);

        // Trigger WiFi reconnection event
        eventBus.publish(EVENT_WIFI_CONNECT_REQUEST, nullptr);
    }
};

#endif // HTTP_SERVER_H
