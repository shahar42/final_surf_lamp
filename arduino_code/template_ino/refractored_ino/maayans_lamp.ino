/*
 * SURF LAMP - MAAYAN'S LAMP (ID 6)
 * REFACTORED VERSION 2.0
 */

#include <Arduino.h>
#include "Config.h"
#include "SurfState.h"
#include "LedController.h"
#include "WiFiHandler.h"
#include "WebServerHandler.h"
#include "ServerDiscovery.h"
#include "WiFiFingerprinting.h"

// ---------------- GLOBAL OBJECTS ----------------
SurfData surfData;
WiFiFingerprinting fingerprinting;
ServerDiscovery serverDiscovery;
LedController ledController;
WiFiHandler wifiHandler(ledController, fingerprinting);
WebServerHandler webHandler(surfData, ledController, wifiHandler, serverDiscovery);

// ---------------- TIMING VARIABLES ----------------
unsigned long lastStaleLog = 0;

// ---------------- SETUP ----------------
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌊 SURF LAMP - REFACTORED FIRMWARE");
    Serial.printf("🔧 Arduino ID: %d\n", ARDUINO_ID);

    // 1. Initialize LEDs (show startup rainbow)
    ledController.setup();
    ledController.performLEDTest();

    // 2. Connect to WiFi
    wifiHandler.setup();

    // 3. Start Web Server
    webHandler.setup();

    // 4. Initial Data Fetch
    Serial.println("🔄 Attempting initial surf data fetch...");
    if (webHandler.fetchSurfDataFromServer()) {
        Serial.println("✅ Initial surf data fetch successful");
    } else {
        Serial.println("⚠️ Initial surf data fetch failed, will retry later");
    }
}

// ---------------- LOOP ----------------
void loop() {
    // 1. Handle WiFi connection maintenance
    wifiHandler.loop();

    // 2. Handle Web Server requests
    webHandler.handleClient();

    // 3. Periodic Data Fetch
    if (millis() - webHandler.getLastFetchTime() > FETCH_INTERVAL) {
        Serial.println("🔄 Time to fetch new surf data...");
        if (webHandler.fetchSurfDataFromServer()) {
            Serial.println("✅ Surf data fetch successful");
        } else {
            Serial.println("❌ Surf data fetch failed");
        }
    }

    // 4. Update Visuals
    // Check if display needs update (flag set by WebServerHandler when data arrives)
    if (surfData.needsDisplayUpdate) {
        Serial.println("🔄 Detected state change, updating display...");
        ledController.updateSurfDisplay(surfData);
        surfData.needsDisplayUpdate = false;
    }

    // Always run animation logic (handles blinking if thresholds exceeded)
    ledController.updateBlinkingAnimation(surfData);

    // 5. Status LED Logic (Data Freshness)
    // Only run this if WiFi is connected, otherwise WiFiHandler handles red blinking
    if (WiFi.status() == WL_CONNECTED) {
        unsigned long dataAge = millis() - surfData.lastUpdate;
        
        if (surfData.dataReceived && dataAge < DATA_STALENESS_THRESHOLD) {
            ledController.blinkGreenLED(); // ✅ Fresh data
        } else {
            ledController.blinkOrangeLED(); // ⚠️ Stale data
            
            if (millis() - lastStaleLog > 60000) {
                if (!surfData.dataReceived) {
                    Serial.println("⚠️ Status: ORANGE - No data received yet");
                } else {
                    Serial.printf("⚠️ Status: ORANGE - Data is %lu min old\n", dataAge / 60000);
                }
                lastStaleLog = millis();
            }
        }
    }

    delay(5);
}