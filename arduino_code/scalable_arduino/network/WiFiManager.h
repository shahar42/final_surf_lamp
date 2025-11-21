/**
 * WiFiManager.h
 *
 * Manages WiFi connection and configuration AP mode.
 *
 * RESPONSIBILITIES:
 * - WiFi STA (station) mode connection
 * - WiFi AP (access point) configuration mode
 * - Credential storage in NVRAM (Preferences)
 * - WiFi reconnection logic
 * - Configuration timeout handling
 *
 * EVENTS PUBLISHED:
 * - EVENT_WIFI_CONNECTED
 * - EVENT_WIFI_DISCONNECTED
 * - EVENT_CONFIG_MODE_STARTED
 *
 * STATE MACHINE INTEGRATION:
 * - Triggers state transitions (WIFI_CONNECTING → OPERATIONAL)
 */

#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>
#include <Preferences.h>
#include "../core/EventBus.h"
#include "../config/SystemConfig.h"

class WiFiManager {
private:
    EventBus& eventBus;
    Preferences preferences;

    char ssid[32];
    char password[64];

    bool configModeActive;
    unsigned long apStartTime;

public:
    /**
     * Constructor
     * @param events Reference to the global EventBus
     */
    WiFiManager(EventBus& events)
        : eventBus(events), configModeActive(false), apStartTime(0) {
        // Default credentials (overridden by stored values)
        strcpy(ssid, SystemConfig::DEFAULT_WIFI_SSID);
        strcpy(password, SystemConfig::DEFAULT_WIFI_PASSWORD);

        Serial.println("📶 WiFiManager initialized");
    }

    /**
     * Initialize WiFi system
     */
    void begin() {
        preferences.begin("wifi-creds", false);
        loadCredentials();
    }

    /**
     * Load WiFi credentials from NVRAM
     */
    void loadCredentials() {
        preferences.begin("wifi-creds", false);
        String storedSSID = preferences.getString("ssid", ssid);
        String storedPassword = preferences.getString("password", password);
        preferences.end();

        storedSSID.toCharArray(ssid, sizeof(ssid));
        storedPassword.toCharArray(password, sizeof(password));

        Serial.printf("📝 WiFiManager: Loaded SSID: %s\n", ssid);
    }

    /**
     * Save WiFi credentials to NVRAM
     */
    void saveCredentials(const char* newSSID, const char* newPassword) {
        preferences.begin("wifi-creds", false);
        preferences.putString("ssid", newSSID);
        preferences.putString("password", newPassword);
        preferences.end();

        strcpy(ssid, newSSID);
        strcpy(password, newPassword);

        Serial.println("✅ WiFiManager: Credentials saved");
    }

    /**
     * Attempt to connect to WiFi
     * @return true if connected successfully
     */
    bool connect() {
        Serial.println("🔄 WiFiManager: Connecting to WiFi...");
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid, password);

        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < SystemConfig::WIFI_TIMEOUT_SECONDS) {
            Serial.print(".");
            delay(1000);
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("\n✅ WiFiManager: Connected!");
            Serial.printf("📍 IP: %s\n", WiFi.localIP().toString().c_str());
            Serial.printf("📶 SSID: %s\n", WiFi.SSID().c_str());
            Serial.printf("💪 Signal: %d dBm\n", WiFi.RSSI());

            eventBus.publish(EVENT_WIFI_CONNECTED, nullptr);
            return true;
        } else {
            Serial.println("\n❌ WiFiManager: Connection failed");
            eventBus.publish(EVENT_WIFI_DISCONNECTED, nullptr);
            return false;
        }
    }

    /**
     * Start WiFi configuration AP mode
     */
    void startConfigMode() {
        Serial.println("🔧 WiFiManager: Starting config mode...");

        configModeActive = true;
        apStartTime = millis();

        WiFi.disconnect(true);
        WiFi.mode(WIFI_AP);
        WiFi.softAP(SystemConfig::CONFIG_AP_SSID, SystemConfig::CONFIG_AP_PASSWORD);

        Serial.printf("📍 AP IP: %s\n", WiFi.softAPIP().toString().c_str());
        Serial.printf("📱 SSID: %s\n", SystemConfig::CONFIG_AP_SSID);
        Serial.printf("🔑 Password: %s\n", SystemConfig::CONFIG_AP_PASSWORD);

        eventBus.publish(EVENT_CONFIG_MODE_STARTED, nullptr);
    }

    /**
     * Handle configuration mode timeout
     * @return true if timeout occurred
     */
    bool handleConfigTimeout() {
        if (configModeActive && (millis() - apStartTime > SystemConfig::CONFIG_AP_TIMEOUT_MS)) {
            Serial.println("⏰ WiFiManager: Config mode timeout");
            configModeActive = false;
            return true;
        }
        return false;
    }

    /**
     * Check if WiFi is connected
     */
    bool isConnected() const {
        return WiFi.status() == WL_CONNECTED;
    }

    /**
     * Check if in configuration mode
     */
    bool isConfigMode() const {
        return configModeActive;
    }

    /**
     * Exit configuration mode
     */
    void exitConfigMode() {
        configModeActive = false;
        Serial.println("✅ WiFiManager: Exited config mode");
    }

    /**
     * Get current SSID
     */
    const char* getSSID() const {
        return WiFi.status() == WL_CONNECTED ? WiFi.SSID().c_str() : ssid;
    }

    /**
     * Get current IP address
     */
    String getIPAddress() const {
        return WiFi.localIP().toString();
    }

    /**
     * Get signal strength in dBm
     */
    int getRSSI() const {
        return WiFi.RSSI();
    }

    /**
     * Attempt WiFi reconnection
     */
    void reconnect() {
        Serial.println("🔄 WiFiManager: Reconnecting...");
        WiFi.disconnect();
        delay(100);
        connect();
    }
};

#endif // WIFI_MANAGER_H
