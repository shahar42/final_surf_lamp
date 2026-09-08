/*
 * WEB SERVER HANDLER 
 *
 * HTTP endpoint handlers for surf lamp.
 */

#include "WebServerHandler.h"
#include "LedController.h"
#include "ServerDiscovery.h"
#include "Themes.h"
#include "esp_Server_encoding.hpp"

// Global timing variables declared header
const unsigned long DATA_STALENESS_THRESHOLD = 1800000; // 30 minutes (2 missed fetches) used in lamp_template.ino

static WebServer* webServer = nullptr;

WiFiClientSecure globalHttpsClient;

extern ServerDiscovery serverDiscovery;

#include "my_linear_buffer.hpp"
extern AsyncSerialLogger asyncLogger;

extern String lastWiFiError;
extern uint8_t lastDisconnectReason;

// ---------------- SERVER SETUP ----------------

void setupHTTPEndpoints(WebServer& server) {
    webServer = &server;  

    // Main endpoint for receiving surf data from background processor
    server.on("/api/update", HTTP_POST, handleSurfDataUpdate);

    // Status endpoint for monitoring
    server.on("/api/status", HTTP_GET, handleStatusRequest);

    // Device info endpoint
    server.on("/api/info", HTTP_GET, handleDeviceInfoRequest);

    // WiFi diagnostics endpoint
    server.on("/api/wifi-diagnostics", HTTP_GET, handleWiFiDiagnostics);

    server.begin();
    asyncLogger.Log("HTTP server started");
}

// ---------------- ENDPOINT HANDLERS ----------------

void handleSurfDataUpdate() {
    asyncLogger.Log("Received surf data request");

    if (!webServer->hasArg("plain"))
    {
        webServer->send(400, "application/json", "{\"ok\":false}");
        asyncLogger.Log("No JSON data in request");
        return;
    }

    String jsonData = webServer->arg("plain");
    asyncLogger.Log("Raw JSON data:");
    asyncLogger.Log(jsonData.c_str());

    if (processSurfData(jsonData)) {
        webServer->send(200, "application/json", "{\"ok\":true}");
        asyncLogger.Log("Surf data processed successfully");
    } else {
        webServer->send(400, "application/json", "{\"ok\":false}");
        asyncLogger.Log("Failed to process surf data");
    }
}

void GetLastSurfData(DynamicJsonDocument& statusDoc)
{
    MutexGuard lock(surfDataMutex);
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
}

void GetLedDebug(DynamicJsonDocument& statusDoc)
{
    MutexGuard lock(surfDataMutex);
    if (lastSurfData.dataReceived)
    {
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
}

void handleStatusRequest() 
{
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
    GetLastSurfData(statusDoc);

    // Fetch timing information
    unsigned long intervalMs = FETCH_INTERVAL_MS.load();  // Atomic read
    unsigned long lastFetchMs = lastDataFetch.load();  // Atomic read
    statusDoc["fetch_info"]["last_fetch_ms"] = lastFetchMs;
    statusDoc["fetch_info"]["fetch_interval_ms"] = intervalMs;
    statusDoc["fetch_info"]["time_since_last_fetch_ms"] = millis() - lastFetchMs;
    statusDoc["fetch_info"]["time_until_next_fetch_ms"] = intervalMs - (millis() - lastFetchMs);

    // LED calculation debug info
    GetLedDebug(statusDoc);

    String statusJson;
    serializeJson(statusDoc, statusJson);

    webServer->send(200, "application/json", statusJson);
    asyncLogger.Log("Status request served");
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
    asyncLogger.Log("Device info request served");
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
    if (WiFi.status() == WL_CONNECTED) 
    {
        String ssid = WiFi.SSID();
        int numNetworks = WiFi.scanNetworks();

        for (int i = 0; i < numNetworks; i++) {
            if (WiFi.SSID(i) == ssid) 
            {
                doc["channel"] = WiFi.channel(i);
                doc["security_type"] = WiFi.encryptionType(i);
                break;
            }
        }
    }

    String response;
    serializeJson(doc, response);

    webServer->send(200, "application/json", response);
    asyncLogger.Log("WiFi diagnostics request served");
}



// ---------------- DATA PROCESSING ----------------

/// @brief Process surf conditions and configuration from a JSON payload.
/// @param jsonData JSON string containing surf conditions and configuration data for the lamp.
/// @return true if the JSON was parsed successfully and the data was applied.

void print_data_info()
{
    MutexGuard lock(surfDataMutex);
    int windSpeedLEDs = ledMapping.calculateWindLEDs(lastSurfData.windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(lastSurfData.waveHeight);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(lastSurfData.wavePeriod);

    char buf[128];
    asyncLogger.Log("Surf Data Received:");
    sprintf(buf, "   Wave Height: %d cm", lastSurfData.waveHeightCm());
    asyncLogger.Log(buf);
    sprintf(buf, "   Wave Period: %.1f s", lastSurfData.wavePeriod);
    asyncLogger.Log(buf);
    sprintf(buf, "   Wind Speed: %.1f m/s", lastSurfData.windSpeed);
    asyncLogger.Log(buf);
    sprintf(buf, "   Wind Direction: %d deg", lastSurfData.windDirection);
    asyncLogger.Log(buf);
    sprintf(buf, "   Wave Threshold: %d cm", lastSurfData.waveThresholdCm());
    asyncLogger.Log(buf);
    sprintf(buf, "   Wind Threshold: %d knots", lastSurfData.windSpeedThreshold);
    asyncLogger.Log(buf);
    sprintf(buf, "   Quiet Hours: %s", lastSurfData.quietHoursActive ? "true" : "false");
    asyncLogger.Log(buf);
    sprintf(buf, "   Off Hours: %s", lastSurfData.offHoursActive ? "true" : "false");
    asyncLogger.Log(buf);
    sprintf(buf, "   Brightness: %.1f", lastSurfData.brightnessMultiplier);
    asyncLogger.Log(buf);
    sprintf(buf, "   LED Theme: %s", themeIndexToName(lastSurfData.themeIndex));
    asyncLogger.Log(buf);
    sprintf(buf, "Timestamp: %lu ms (uptime)", lastSurfData.lastUpdate);
    asyncLogger.Log(buf);
    sprintf(buf, "LEDs Active - Wind: %d, Wave: %d, Period: %d", windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs);
    asyncLogger.Log(buf);
}

void UpdateGlobalState(int wave_height_cm, float wave_period_s, int wind_speed_mps,
                       int wind_direction_deg, int wave_threshold_cm, int wind_speed_threshold_knots,
                       bool quiet_hours_active, bool off_hours_active, float brightness_multiplier,
                       uint8_t theme_index, bool stale_data_warning)
{
    MutexGuard lock(surfDataMutex);
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
    lastSurfData.themeIndex = theme_index;

    lastSurfData.lastUpdate = millis();
    lastSurfData.dataReceived = true;

    // Clear all error flags first, then set specific ones if detected
    lastSurfData.invalidDataError = false;
    lastSurfData.serverUnreachableError = false;
    lastSurfData.jsonParseError = false;
    lastSurfData.partialDataError = false;
    lastSurfData.staleDataError = false;

    // Set server-side stale warning (only triggers visual alert if true)
    lastSurfData.staleDataWarning = stale_data_warning;
} 

bool processSurfData(const String& jsonData) 
{
    DynamicJsonDocument doc(JSON_CAPACITY);
    DeserializationError error = deserializeJson(doc, jsonData);

    bool is_data_valid = doc["data_available"] | true;

    if (error) {
        char buf[128];
        sprintf(buf, "JSON parsing failed: %s", error.c_str());
        asyncLogger.Log(buf);
        lastSurfData.jsonParseError = true;
        lastSurfData.needsDisplayUpdate.store(true);
        return false;
    }

    // Extract values using keys sent by the server
    int wave_height_cm = doc["wave_height_cm"] | SurfDataDefaults::WAVE_HEIGHT_CM;
    float wave_period_s = doc["wave_period_s"] | SurfDataDefaults::WAVE_PERIOD_S;
    int wind_speed_mps = doc["wind_speed_mps"] | SurfDataDefaults::WIND_SPEED_MPS;
    int wind_direction_deg = doc["wind_direction_deg"] | SurfDataDefaults::WIND_DIRECTION_DEG;
    int wave_threshold_cm = doc["wave_threshold_cm"] | SurfDataDefaults::WAVE_THRESHOLD_CM;
    int wind_speed_threshold_knots = doc["wind_speed_threshold_knots"] | SurfDataDefaults::WIND_SPEED_THRESHOLD_KNOTS;
    bool quiet_hours_active = doc["quiet_hours_active"] | SurfDataDefaults::QUIET_HOURS_ACTIVE;
    bool off_hours_active = doc["off_hours_active"] | SurfDataDefaults::OFF_HOURS_ACTIVE;
    float brightness_multiplier = doc["brightness_multiplier"] | SurfDataDefaults::BRIGHTNESS_MULTIPLIER;
    const char* led_theme_str = doc["led_theme"] | SurfDataDefaults::LED_THEME;
    uint8_t theme_index = themeNameToIndex(led_theme_str);
    bool stale_data_warning = doc["stale_data_warning"] | false;

    // Extract fetch interval from server (dynamic polling configuration)
    if (doc.containsKey("fetch_interval_ms")) {
        unsigned long new_interval = doc["fetch_interval_ms"];
        char buf[128];
        sprintf(buf, "Received fetch_interval: %lu min", new_interval / 60000);
        asyncLogger.Log(buf);
        if (new_interval >= 60000 && new_interval <= 3600000) { // Safety: 1 min to 1 hour
            unsigned long current_interval = FETCH_INTERVAL_MS.load();
            if (current_interval != new_interval) {
                FETCH_INTERVAL_MS.store(new_interval);
                sprintf(buf, "Fetch interval updated: %lu min -> %lu min", current_interval / 60000, new_interval / 60000);
                asyncLogger.Log(buf);
            } else {
                sprintf(buf, "Fetch interval unchanged: %lu min", new_interval / 60000);
                asyncLogger.Log(buf);
            }
        } else {
            sprintf(buf, "Fetch interval out of range: %lu min (ignoring, valid: 1-60 min)", new_interval / 60000);
            asyncLogger.Log(buf);
        }
    }

    // Error determination is the server's responsibility via the data_available flag.
    if (!is_data_valid) {
        asyncLogger.Log("SERVER: data_available=false — no surf data from API");
    }

    if (stale_data_warning) {
        asyncLogger.Log("SERVER WARNING: Data is stale (unchanged for > 60 mins)");
    }

    UpdateGlobalState(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg,
                      wave_threshold_cm, wind_speed_threshold_knots, quiet_hours_active,
                      off_hours_active, brightness_multiplier, theme_index, stale_data_warning);

    print_data_info();

    // Error determination is the server's responsibility via the data_available flag.
    if (!is_data_valid) {
        lastSurfData.invalidDataError = true;
    }

    lastSurfData.needsDisplayUpdate.store(true);  // Thread-safe signal to Core 1 loop()

    return true;
}

bool processBinarySurfData(const uint8_t* binaryData, size_t length) {
    if (length != 26) {
        char buf[64];
        sprintf(buf, "Binary protocol error: Expected 26 bytes, got %d", length);
        asyncLogger.Log(buf);
        lastSurfData.jsonParseError = true;
        lastSurfData.needsDisplayUpdate.store(true);
        return false;
    }

    // Parse SurfData (first 9 bytes: 8 data + 1 CRC)
    uint64_t surf_packed = 0;
    for (int i = 0; i < 8; i++) {
        surf_packed = (surf_packed << 8) | binaryData[i];
    }
    SurfDataPacket surf(surf_packed);

    // Validate surf CRC
    uint8_t surf_crc = binaryData[8];
    if (!surf.ValidateCRC(surf_crc)) {
        asyncLogger.Log("Surf data CRC validation FAILED - packet corrupted!");
        lastSurfData.jsonParseError = true;  // Reuse error flag
        lastSurfData.needsDisplayUpdate.store(true);
        return false;
    }

    // Parse SettingsData (bytes 9-25: 16 data + 1 CRC)
    uint64_t settings_data1 = 0, settings_data2 = 0;
    for (int i = 0; i < 8; i++) {
        settings_data1 = (settings_data1 << 8) | binaryData[9 + i];
        settings_data2 = (settings_data2 << 8) | binaryData[17 + i];
    }
    SettingsData settings(settings_data1, settings_data2);

    // Validate settings CRC
    uint8_t settings_crc = binaryData[25];
    if (!settings.ValidateCRC(settings_crc)) {
        asyncLogger.Log("Settings data CRC validation FAILED - packet corrupted!");
        lastSurfData.jsonParseError = true;
        lastSurfData.needsDisplayUpdate.store(true);
        return false;
    }

    asyncLogger.Log("Binary protocol: CRC validation PASSED");

    // Extract surf conditions
    int wave_height_cm = surf.GetWaveHeight();
    float wave_period_s = surf.GetWavePeriod();
    int wind_speed_mps = surf.GetWindSpeed();
    int wind_direction_deg = surf.GetWindDirection();
    int wave_threshold_cm = surf.GetWaveThreshold();
    int wind_speed_threshold_knots = surf.GetWindThreshold();
    bool quiet_hours_active = surf.GetQuietHours();
    bool off_hours_active = surf.GetOffHours();
    bool stale_data_warning = surf.GetStaleData();
    bool is_data_valid = surf.GetDataAvailable();

    // Extract settings
    float brightness_multiplier = settings.GetBrightness() / 100.0f;
    // Latitude/longitude/tz_offset are still carried by the V3 wire protocol
    // (SettingsData) but the lamp no longer consumes them.

    // Theme index directly from binary protocol (no string conversion needed)
    uint8_t theme_index = static_cast<uint8_t>(settings.GetLEDTheme());

    // Extract fetch interval
    unsigned long new_interval = settings.GetFetchIntervalMs();
    if (new_interval >= 60000 && new_interval <= 3600000) {
        unsigned long current_interval = FETCH_INTERVAL_MS.load();
        if (current_interval != new_interval) {
            FETCH_INTERVAL_MS.store(new_interval);
            char buf[128];
            sprintf(buf, "Fetch interval updated: %lu min -> %lu min", current_interval / 60000, new_interval / 60000);
            asyncLogger.Log(buf);
        }
    }

    // Update global state (same as JSON version)
    UpdateGlobalState(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg,
                      wave_threshold_cm, wind_speed_threshold_knots, quiet_hours_active,
                      off_hours_active, brightness_multiplier, theme_index, stale_data_warning);

    print_data_info();

    // Error determination is the server's responsibility via the data_available flag.
    // The Arduino trusts it — a 0 wave height on a calm day is valid data, not an error.
    if (!is_data_valid) {
        lastSurfData.invalidDataError = true;
    }

    lastSurfData.needsDisplayUpdate.store(true);

    char buf[128];
    sprintf(buf, "Binary packet decoded: wave=%dcm, wind=%dm/s, brightness=%.0f%%",
            wave_height_cm, wind_speed_mps, brightness_multiplier * 100);
    asyncLogger.Log(buf);

    return true;
}

String urlEncode(const String& str) {
    String encoded = "";
    for (int i = 0; i < str.length(); i++) {
        char c = str.charAt(i);
        if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~' || c == ',') {
            encoded += c;
        } else if (c == ' ') {
            encoded += "%20";
        } else {
            char hex[4];
            sprintf(hex, "%%%02X", (unsigned char)c);
            encoded += hex;
        }
    }
    return encoded;
}


bool sendHeartbeat() 
{
    String apiServer = serverDiscovery.getApiServer();
    if (apiServer.length() == 0) return false;

    // Use a fresh connection for heartbeat
    globalHttpsClient.stop();
    globalHttpsClient.setInsecure();

    HTTPClient http;
    String url = "https://" + apiServer + "/api/arduino/callback";
    
    http.begin(globalHttpsClient, url);
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.addHeader("Content-Type", "application/json");
    
    // Create JSON payload
    DynamicJsonDocument doc(128);
    doc["arduino_id"] = ARDUINO_ID;
    doc["data_received"] = true;
    doc["local_ip"] = WiFi.localIP().toString();
    
    String jsonPayload;
    serializeJson(doc, jsonPayload);
    
    asyncLogger.Log(("Sending heartbeat: " + url).c_str());
    int httpCode = http.POST(jsonPayload);

    bool success = false;
    if (httpCode == HTTP_CODE_OK) {
        asyncLogger.Log("Heartbeat acknowledged");
        success = true;
    } else {
        char buf[64];
        sprintf(buf, "Heartbeat failed: %d", httpCode);
        asyncLogger.Log(buf);
    }
    
    http.end();
    globalHttpsClient.stop();
    return success;
}

bool fetchSurfDataFromServer() {
    String apiServer = serverDiscovery.getApiServer();
    if (apiServer.length() == 0) {
        asyncLogger.Log("No API server available for fetching data");
        return false;
    }

    // Close any previous connection and prepare for reuse
    globalHttpsClient.stop();
    globalHttpsClient.setInsecure();

    HTTPClient http;
    String url = "https://" + apiServer + "/api/arduino/v3/" + String(ARDUINO_ID) + "/data";
    asyncLogger.Log(("Fetching surf data (V3 Binary Protocol): " + url).c_str());

    http.begin(globalHttpsClient, url);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        // Get binary payload size
        int payloadSize = http.getSize();
        char buf[128];
        sprintf(buf, "Received %d bytes from server", payloadSize);
        asyncLogger.Log(buf);

        // Read binary data
        uint8_t binaryBuffer[26];  // Fixed size for v3 protocol
        WiFiClient* stream = http.getStreamPtr();

        if (payloadSize == 26 && stream->readBytes(binaryBuffer, 26) == 26) {
            http.end();
            globalHttpsClient.stop();

            asyncLogger.Log("Processing binary surf data (26 bytes)");
            return processBinarySurfData(binaryBuffer, 26);
        } else {
            sprintf(buf, "Invalid payload size: expected 26 bytes, got %d", payloadSize);
            asyncLogger.Log(buf);
            http.end();
            globalHttpsClient.stop();
            lastSurfData.jsonParseError = true;
            lastSurfData.needsDisplayUpdate.store(true);
            return false;
        }
    } else {
        char buf[128];
        sprintf(buf, "HTTP error fetching surf data: %d (%s)", httpCode, http.errorToString(httpCode).c_str());
        asyncLogger.Log(buf);
        http.end();
        globalHttpsClient.stop();  // Explicit cleanup after failure

        // Mark server as unreachable
        lastSurfData.serverUnreachableError = true;
        lastSurfData.needsDisplayUpdate.store(true);

        return false;
    }
}
