/*
 * WEB SERVER HANDLER 
 *
 * HTTP endpoint handlers for surf lamp.
 */

#include "WebServerHandler.h"
#include "LedController.h"
#include "ServerDiscovery.h"
#include "SunsetCalculator.h"
#include "esp_Server_encoding.hpp"

// Global timing variables declared header
const unsigned long DATA_STALENESS_THRESHOLD = 1800000; // 30 minutes (2 missed fetches) used in lamp_template.ino

static WebServer* webServer = nullptr;

WiFiClientSecure globalHttpsClient;

extern ServerDiscovery serverDiscovery;

extern SunsetCalculator sunsetCalc;

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
    Serial.println("🌐 HTTP server started");
}

// ---------------- ENDPOINT HANDLERS ----------------

void handleSurfDataUpdate() {
    Serial.println("Received surf data request");

    if (!webServer->hasArg("plain")) 
    {
        webServer->send(400, "application/json", "{\"ok\":false}");
        Serial.println("No JSON data in request");
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

void GetLastSurfData(DynamicJsonDocument& statusDoc)
{
    LOCK_SURF_DATA();
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
    UNLOCK_SURF_DATA();
}

void GetLedDebug(DynamicJsonDocument& statusDoc)
{
    LOCK_SURF_DATA();
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
    UNLOCK_SURF_DATA();
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
    Serial.println("📊 Status request served");
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
    Serial.println("🔍 WiFi diagnostics request served");
}



// ---------------- DATA PROCESSING ----------------

/// @brief Process surf conditions and configuration from a JSON payload.
/// @param jsonData JSON string containing surf conditions and configuration data for the lamp.
/// @return true if the JSON was parsed successfully and the data was applied.

void print_data_info()
{
    LOCK_SURF_DATA();
    // Calculate LED counts for logging
    int windSpeedLEDs = ledMapping.calculateWindLEDs(lastSurfData.windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(lastSurfData.waveHeight);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(lastSurfData.wavePeriod);
    Serial.println("🌊 Surf Data Received:");
    Serial.printf("   Wave Height: %d cm\n", lastSurfData.waveHeightCm());
    Serial.printf("   Wave Period: %.1f s\n", lastSurfData.wavePeriod);
    Serial.printf("   Wind Speed: %.1f m/s\n", lastSurfData.windSpeed);
    Serial.printf("   Wind Direction: %d°\n", lastSurfData.windDirection);
    Serial.printf("   Wave Threshold: %d cm\n", lastSurfData.waveThresholdCm());
    Serial.printf("   Wind Speed Threshold: %d knots\n", lastSurfData.windSpeedThreshold);
    Serial.printf("   Quiet Hours Active: %s\n", lastSurfData.quietHoursActive ? "true" : "false");
    Serial.printf("   Off Hours Active: %s\n", lastSurfData.offHoursActive ? "true" : "false");
    Serial.printf("   Brightness Multiplier: %.1f\n", lastSurfData.brightnessMultiplier);
    Serial.printf("   LED Theme: %s\n", lastSurfData.theme);
    // Log timestamp and LED counts
    Serial.printf("⏰ Timestamp: %lu ms (uptime)\n", lastSurfData.lastUpdate);
    Serial.printf("💡 LEDs Active - Wind: %d, Wave: %d, Period: %d\n", windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs);
    UNLOCK_SURF_DATA();
}

void UpdateGlobalState(int wave_height_cm, float wave_period_s, int wind_speed_mps,
                       int wind_direction_deg, int wave_threshold_cm, int wind_speed_threshold_knots,
                       bool quiet_hours_active, bool off_hours_active, float brightness_multiplier,
                       const String& led_theme, bool stale_data_warning)
{
    LOCK_SURF_DATA();
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
    
    // Thread-safe string copy
    strncpy(lastSurfData.theme, led_theme.c_str(), sizeof(lastSurfData.theme) - 1);
    lastSurfData.theme[sizeof(lastSurfData.theme) - 1] = '\0';
    
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
    UNLOCK_SURF_DATA();
} 

bool processSurfData(const String& jsonData) 
{
    DynamicJsonDocument doc(JSON_CAPACITY);
    DeserializationError error = deserializeJson(doc, jsonData);

    bool is_data_valid = doc["data_available"] | true;

    if (error) {
        Serial.printf("❌ JSON parsing failed: %s\n", error.c_str());
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
    String led_theme = doc["led_theme"] | SurfDataDefaults::LED_THEME;
    bool stale_data_warning = doc["stale_data_warning"] | false;

    // V2 API: Extract location coordinates for sunset calculation
    float latitude = doc["latitude"] | 0.0;
    float longitude = doc["longitude"] | 0.0;
    int8_t tz_offset = doc["tz_offset"] | 0;

    // Update coordinates in sunset calculator (writes to flash only if changed)
    if (latitude != 0.0 && longitude != 0.0)
    {
        sunsetCalc.updateCoordinates(latitude, longitude, tz_offset);
    }

    // Extract fetch interval from server (dynamic polling configuration)
    if (doc.containsKey("fetch_interval_ms")) {
        unsigned long new_interval = doc["fetch_interval_ms"];
        Serial.printf("📡 Received fetch_interval: %lu min\n", new_interval / 60000);
        if (new_interval >= 60000 && new_interval <= 3600000) { // Safety: 1 min to 1 hour
            unsigned long current_interval = FETCH_INTERVAL_MS.load();
            if (current_interval != new_interval) {
                FETCH_INTERVAL_MS.store(new_interval);
                Serial.printf("✅ Fetch interval updated: %lu min → %lu min\n", current_interval / 60000, new_interval / 60000);
            } else {
                Serial.printf("ℹ️ Fetch interval unchanged: %lu min\n", new_interval / 60000);
            }
        } else {
            Serial.printf("⚠️ Fetch interval out of range: %lu min (ignoring, valid: 1-60 min)\n", new_interval / 60000);
        }
    }

    // Validate data quality
    bool bothZero = (wave_height_cm == 0 && wind_speed_mps == 0 && wave_period_s == 0);
    bool partialZero = !is_data_valid || (wave_height_cm == 0 || wind_speed_mps == 0 || wave_period_s == 0) && !bothZero;

    if (bothZero) {
        Serial.println("⚠️ INVALID DATA: Wave height, wind speed, and wave period are all zero");
    } else if (partialZero) {
        Serial.println("⚠️ PARTIAL DATA FAILURE: One value is zero");
        Serial.printf("   Wave: %d cm, Wind: %d m/s, Period: %.1f s\n", wave_height_cm, wind_speed_mps, wave_period_s);
    }
    
    if (stale_data_warning) {
        Serial.println("⚠️ SERVER WARNING: Data is stale (unchanged for > 60 mins)");
    }

    UpdateGlobalState(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg,
                      wave_threshold_cm, wind_speed_threshold_knots, quiet_hours_active,
                      off_hours_active, brightness_multiplier, led_theme, stale_data_warning);

    print_data_info();

    // Set error flags based on validation
    if (bothZero) {
        lastSurfData.invalidDataError = true;
    } else if (partialZero) {
        lastSurfData.partialDataError = true;
    }

    lastSurfData.needsDisplayUpdate.store(true);  // Thread-safe signal to Core 1 loop()

    return true;
}

bool processBinarySurfData(const uint8_t* binaryData, size_t length) {
    if (length != 26) {
        Serial.printf("❌ Binary protocol error: Expected 26 bytes, got %d\n", length);
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
        Serial.println("❌ Surf data CRC validation FAILED - packet corrupted!");
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
        Serial.println("❌ Settings data CRC validation FAILED - packet corrupted!");
        lastSurfData.jsonParseError = true;
        lastSurfData.needsDisplayUpdate.store(true);
        return false;
    }

    Serial.println("✅ Binary protocol: CRC validation PASSED");

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
    float latitude = settings.GetLatitude();
    float longitude = settings.GetLongitude();
    int32_t tz_offset = settings.GetTzOffset();

    // Map LED theme enum to string
    LEDTheme theme_enum = settings.GetLEDTheme();
    String led_theme = "classic_surf";  // Default
    switch (theme_enum) {
        case LEDTheme::CLASSIC_SURF: led_theme = "classic_surf"; break;
        case LEDTheme::VIBRANT_MIX: led_theme = "vibrant_mix"; break;
        case LEDTheme::TROPICAL_PARADISE: led_theme = "tropical_paradise"; break;
        case LEDTheme::OCEAN_SUNSET: led_theme = "ocean_sunset"; break;
        case LEDTheme::ELECTRIC_VIBES: led_theme = "electric_vibes"; break;
    }

    // Update coordinates in sunset calculator
    if (latitude != 0.0 && longitude != 0.0) {
        sunsetCalc.updateCoordinates(latitude, longitude, tz_offset);
    }

    // Extract fetch interval
    unsigned long new_interval = settings.GetFetchIntervalMs();
    if (new_interval >= 60000 && new_interval <= 3600000) {
        unsigned long current_interval = FETCH_INTERVAL_MS.load();
        if (current_interval != new_interval) {
            FETCH_INTERVAL_MS.store(new_interval);
            Serial.printf("✅ Fetch interval updated: %lu min → %lu min\n", current_interval / 60000, new_interval / 60000);
        }
    }

    // Update global state (same as JSON version)
    UpdateGlobalState(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg,
                      wave_threshold_cm, wind_speed_threshold_knots, quiet_hours_active,
                      off_hours_active, brightness_multiplier, led_theme, stale_data_warning);

    print_data_info();

    // Set error flags based on validation
    bool bothZero = (wave_height_cm == 0 && wind_speed_mps == 0);
    bool partialZero = (wave_height_cm == 0) != (wind_speed_mps == 0);

    if (bothZero) {
        lastSurfData.invalidDataError = true;
    } else if (partialZero) {
        lastSurfData.partialDataError = true;
    }

    lastSurfData.needsDisplayUpdate.store(true);

    Serial.printf("📊 Binary packet decoded: wave=%dcm, wind=%dm/s, brightness=%.0f%%\n",
                  wave_height_cm, wind_speed_mps, brightness_multiplier * 100);

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
    
    Serial.println("💓 Sending heartbeat: " + url);
    int httpCode = http.POST(jsonPayload);
    
    bool success = false;
    if (httpCode == HTTP_CODE_OK) {
        Serial.println("✅ Heartbeat acknowledged");
        success = true;
    } else {
        Serial.printf("❌ Heartbeat failed: %d\n", httpCode);
    }
    
    http.end();
    globalHttpsClient.stop();
    return success;
}

bool fetchSurfDataFromServer() {
    String apiServer = serverDiscovery.getApiServer();
    if (apiServer.length() == 0) {
        Serial.println("❌ No API server available for fetching data");
        return false;
    }

    // Close any previous connection and prepare for reuse
    globalHttpsClient.stop();
    globalHttpsClient.setInsecure();

    HTTPClient http;
    String url = "https://" + apiServer + "/api/arduino/v3/" + String(ARDUINO_ID) + "/data";
    Serial.println("🌐 Fetching surf data (V3 Binary Protocol): " + url);

    http.begin(globalHttpsClient, url);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        // Extract Date header for time synchronization
        String dateHeader = http.header("Date");

        // Get binary payload size
        int payloadSize = http.getSize();
        Serial.printf("📦 Received %d bytes from server\n", payloadSize);

        // Read binary data
        uint8_t binaryBuffer[26];  // Fixed size for v3 protocol
        WiFiClient* stream = http.getStreamPtr();

        if (payloadSize == 26 && stream->readBytes(binaryBuffer, 26) == 26) {
            http.end();
            globalHttpsClient.stop();

            // Process Date header
            if (dateHeader.length() > 0) {
                Serial.println("📅 HTTP Date: " + dateHeader);
                if (sunsetCalc.parseAndUpdateTime(dateHeader)) {
                    sunsetCalc.calculateSunset();
                } else {
                    Serial.println("⚠️ Failed to parse Date header");
                }
            }

            Serial.println("📥 Processing binary surf data (26 bytes)");
            return processBinarySurfData(binaryBuffer, 26);
        } else {
            Serial.printf("❌ Invalid payload size: expected 26 bytes, got %d\n", payloadSize);
            http.end();
            globalHttpsClient.stop();
            lastSurfData.jsonParseError = true;
            lastSurfData.needsDisplayUpdate.store(true);
            return false;
        }
    } else {
        Serial.printf("❌ HTTP error fetching surf data: %d (%s)\n", httpCode, http.errorToString(httpCode).c_str());
        http.end();
        globalHttpsClient.stop();  // Explicit cleanup after failure

        // Mark server as unreachable
        lastSurfData.serverUnreachableError = true;
        lastSurfData.needsDisplayUpdate.store(true);

        return false;
    }
}
