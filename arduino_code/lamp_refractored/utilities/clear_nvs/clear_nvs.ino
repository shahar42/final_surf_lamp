/*
 * NVS CLEAR UTILITY
 *
 * Upload this sketch to clear all stored WiFi credentials and settings
 * before shipping lamps to customers.
 *
 * USAGE:
 * 1. Upload this sketch to the ESP32
 * 2. Open Serial Monitor (115200 baud)
 * 3. Wait for "NVS CLEARED SUCCESSFULLY" message
 * 4. Upload the actual lamp firmware (lamp_template.ino)
 * 5. Ship the lamp
 */

#include <WiFi.h>
#include <Preferences.h>

Preferences preferences;

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n========================================");
    Serial.println("  NVS CLEAR UTILITY");
    Serial.println("========================================\n");

    Serial.println("Clearing all NVS data...");

    // 1. Clear WiFi credentials (ESP32 built-in storage)
    Serial.println("  - Clearing WiFi credentials...");
    WiFi.disconnect(true, true);  // disconnect + erase credentials
    delay(100);

    // 2. Clear sunset calculator data (coordinates + timezone)
    Serial.println("  - Clearing sunset data (lat/lon/timezone)...");
    preferences.begin("surf_lamp", false);
    preferences.clear();
    preferences.end();

    // 3. Clear WiFi fingerprinting data (neighbor SSIDs for location detection)
    Serial.println("  - Clearing WiFi fingerprint (neighbor networks)...");
    preferences.begin("wifi_fp", false);
    preferences.clear();
    preferences.end();

    Serial.println("\n✓ NVS CLEARED SUCCESSFULLY");
    Serial.println("\nAll data erased:");
    Serial.println("  - WiFi SSID and password");
    Serial.println("  - Sunset coordinates (lat/lon/timezone)");
    Serial.println("  - WiFi fingerprint (neighbor networks)");
    Serial.println("\nYou can now upload the lamp firmware and ship the device.\n");
    Serial.println("========================================");
}

void loop() {
    // Nothing to do - task complete
}
