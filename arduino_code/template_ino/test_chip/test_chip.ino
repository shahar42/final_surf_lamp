/*
 * MINIMAL AP TEST - Hardware Debug
 * Tests if ESP32 can create Access Point
 */

#include <WiFi.h>

const char* ap_ssid = "TestESP32-AP";
const char* ap_password = "test1234";

void setup() {
    Serial.begin(115200);
    delay(2000);

    Serial.println("\n=================================");
    Serial.println("ESP32 AP TEST");
    Serial.println("=================================\n");

    // Stop any existing WiFi
    WiFi.mode(WIFI_OFF);
    delay(1000);

    Serial.println("Starting Access Point...");
    Serial.printf("SSID: %s\n", ap_ssid);
    Serial.printf("Password: %s\n", ap_password);

    // Start AP mode
    WiFi.mode(WIFI_AP);
    delay(100);

    // Set max transmission power (78 = 19.5 dBm max for ESP32)
    WiFi.setTxPower(WIFI_POWER_19_5dBm);

    // Use channel 1 (most compatible) and broadcast SSID
    bool result = WiFi.softAP(ap_ssid, ap_password, 1, 0, 4);

    if (result) {
        Serial.println("\n✅ AP STARTED SUCCESSFULLY!");
        Serial.printf("AP IP: %s\n", WiFi.softAPIP().toString().c_str());
        Serial.println("\nLook for WiFi network: TestESP32-AP");
        Serial.println("Password: test1234");
    } else {
        Serial.println("\n❌ AP FAILED TO START!");
    }

    Serial.println("\n=================================\n");
}

void loop() {
    static unsigned long lastCheck = 0;

    if (millis() - lastCheck > 5000) {
        lastCheck = millis();

        int numClients = WiFi.softAPgetStationNum();
        Serial.printf("AP Status: %s | Connected clients: %d\n",
                      WiFi.getMode() == WIFI_AP ? "RUNNING" : "STOPPED",
                      numClients);
    }

    delay(100);
}
