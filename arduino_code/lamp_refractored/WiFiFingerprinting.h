#ifndef WIFI_FINGERPRINTING_H
#define WIFI_FINGERPRINTING_H

#include <WiFi.h>
#include <Preferences.h>

class WiFiFingerprinting {
private:
    static const uint8_t MAX_NEIGHBORS = 4;
    static const uint8_t FINGERPRINT_MAX_SSID_LEN = 32;

    Preferences prefs;

    struct Fingerprint {
        char neighbors[MAX_NEIGHBORS][FINGERPRINT_MAX_SSID_LEN + 1];
        uint8_t count;
    } fingerprint;

public:
    WiFiFingerprinting() {
        fingerprint.count = 0;
    }

    // Load stored fingerprint from NVS
    void load() {
        prefs.begin("wifi_fp", false);
        fingerprint.count = prefs.getUChar("count", 0);

        for (uint8_t i = 0; i < fingerprint.count; i++) {
            String key = "n" + String(i);
            String ssid = prefs.getString(key.c_str(), "");
            strncpy(fingerprint.neighbors[i], ssid.c_str(), FINGERPRINT_MAX_SSID_LEN);
            fingerprint.neighbors[i][FINGERPRINT_MAX_SSID_LEN] = '\0';
        }
        prefs.end();

        Serial.printf("📍 Loaded fingerprint: %d neighbors\n", fingerprint.count);
        for (uint8_t i = 0; i < fingerprint.count; i++) {
            Serial.printf("   - %s\n", fingerprint.neighbors[i]);
        }
    }

    // Update fingerprint with current visible networks (on successful connection)
    void update() {
        Serial.println("🔄 Updating WiFi fingerprint...");

        int numNetworks = WiFi.scanNetworks();
        if (numNetworks == 0) {
            Serial.println("⚠️ No networks found for fingerprint");
            return;
        }

        // Get top 4 strongest networks (excluding our target SSID)
        String targetSSID = WiFi.SSID();
        fingerprint.count = 0;

        for (int i = 0; i < numNetworks && fingerprint.count < MAX_NEIGHBORS; i++) {
            String ssid = WiFi.SSID(i);

            // Skip empty SSIDs and our target network
            if (ssid.length() == 0 || ssid == targetSSID) continue;

            strncpy(fingerprint.neighbors[fingerprint.count], ssid.c_str(), FINGERPRINT_MAX_SSID_LEN);
            fingerprint.neighbors[fingerprint.count][FINGERPRINT_MAX_SSID_LEN] = '\0';
            fingerprint.count++;

            Serial.printf("   + %s (%d dBm)\n", ssid.c_str(), WiFi.RSSI(i));
        }

        // Save to NVS
        prefs.begin("wifi_fp", false);
        prefs.putUChar("count", fingerprint.count);

        for (uint8_t i = 0; i < fingerprint.count; i++) {
            String key = "n" + String(i);
            prefs.putString(key.c_str(), fingerprint.neighbors[i]);
        }
        prefs.end();

        Serial.printf("✅ Fingerprint updated: %d neighbors stored\n", fingerprint.count);
    }

    // Check if fingerprint data exists (first setup detection)
    bool hasData() {
        return fingerprint.count > 0;
    }

    // Check if current environment matches stored fingerprint
    // Returns true if 75% of neighbors match (same location)
    // Returns false if <75% match (moved to new house)
    bool isSameLocation() {
        // No fingerprint stored = first boot or fresh install
        if (fingerprint.count == 0) {
            Serial.println("⚠️ No fingerprint stored (first boot)");
            return false;
        }

        Serial.println("🔍 Checking if same location...");

        int numNetworks = WiFi.scanNetworks();
        if (numNetworks == 0) {
            Serial.println("⚠️ No networks visible, assuming same location (scan failed)");
            return true;  // Conservative: don't force AP mode on scan failure
        }

        // Count how many stored neighbors are visible
        uint8_t matchCount = 0;
        for (int i = 0; i < numNetworks; i++) {
            String currentSSID = WiFi.SSID(i);

            for (uint8_t j = 0; j < fingerprint.count; j++) {
                if (currentSSID == fingerprint.neighbors[j]) {
                    Serial.printf("✅ Match found: '%s'\n", currentSSID.c_str());
                    matchCount++;
                    break;  // Found match, move to next network
                }
            }
        }

        // Require 75% match to confirm same location
        // 4 neighbors → need 3 matches
        // 3 neighbors → need 2 matches
        // 2 neighbors → need 1 match
        // 1 neighbor  → need 1 match
        uint8_t requiredMatches = (fingerprint.count == 1) ? 1 : ((fingerprint.count * 3) / 4);
        if (requiredMatches == 0) requiredMatches = 1;  // Minimum 1 match required

        bool isSame = matchCount >= requiredMatches;

        Serial.printf("%s %d/%d matches (need %d) - %s\n",
                      isSame ? "✅" : "❌",
                      matchCount,
                      fingerprint.count,
                      requiredMatches,
                      isSame ? "SAME LOCATION" : "NEW LOCATION (moved)");

        return isSame;
    }

    // Clear stored fingerprint (for factory reset)
    void clear() {
        prefs.begin("wifi_fp", false);
        prefs.clear();
        prefs.end();
        fingerprint.count = 0;
        Serial.println("🗑️ Fingerprint cleared");
    }
};

#endif
