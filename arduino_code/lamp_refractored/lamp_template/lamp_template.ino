/*
 * SURF LAMP - MODULAR TEMPLATE v3.0.0
 *
 * This is the main orchestration file for the modular surf lamp template.
 * It should be IDENTICAL across all lamp configurations.
 *
 * To create a new lamp:
 * 1. Copy this entire directory
 * 2. Edit ONLY Config.h with your lamp's parameters
 * 3. Rename this file to match your lamp (e.g., bens_lamp.ino)
 * 4. Compile and upload
 *
 * ALL business logic is in the modules - this file just orchestrates them.

 */

#include <WiFi.h>
#include <WebServer.h>
#include <WiFiManager.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// ==================== TEMPLATE MODULES ====================
// These modules contain all the reusable business logic

#include "Config.h"              // Lamp-specific configuration (EDIT THIS FOR NEW LAMPS)
#include "SurfState.h"           // Data structures for surf data
#include "LedController.h"       // LED display functions
#include "Themes.h"              // Color theme management
#include "WebServerHandler.h"    // HTTP endpoint handlers
#include "WiFiHandler.h"         // WiFi connection and diagnostics

// ==================== REUSABLE MODULES ====================
// These modules are shared across all lamp types

#include "ServerDiscovery.h"     // API server discovery
#include "WiFiFingerprinting.h"  // WiFi location detection
#include "SunsetCalculator.h"    // Autonomous sunset calculation
#include "DualCoreManager.h"     // Dual-core task management
#include "animation.h"           // Sunset animation
#include "ArduinoIdDisplay.h"    // Arduino ID binary display on startup

// ==================== GLOBAL INSTANCES ====================

WebServer server(80);
ServerDiscovery serverDiscovery;
WiFiManager wifiManager;
WiFiFingerprinting fingerprinting;
SunsetCalculator sunsetCalc;     // Autonomous sunset calculator (V2)

// ==================== GLOBAL STATE ====================
// These are defined here and declared extern in module headers

SurfData lastSurfData;          // Current surf data (defined here, declared in SurfState.h)
WaveConfig waveConfig;          // Animation config (defined here, declared in Config.h)
LEDMappingConfig ledMapping;    // LED mapping config (defined here, declared in Config.h)

// ==================== SETUP FUNCTION ====================

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Configuration printing removed to save flash memory

    // Initialize hardware
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    initializeLEDs();

    // Display Arduino ID in binary (5 seconds)
    ArduinoId::displayId(leds);

    // Play startup tide animation
    playStartupAnimation();

    // Setup WiFi with event handlers
    WiFi.onEvent(WiFiEvent);
    bool connected = setupWiFi(wifiManager, fingerprinting);

    if (!connected) {
        Serial.println("🔄 Restarting to config portal...");
        delay(3000);
        ESP.restart();
    }

    // Setup HTTP server
    setupHTTPEndpoints(server);

    Serial.println("🚀 Surf Lamp ready for operation!");
    Serial.printf("📍 Device accessible at: http://%s\n", WiFi.localIP().toString().c_str());

    // Wait for network stack to fully stabilize after boot (critical for power outage recovery)
    Serial.println("⏳ Waiting 10 seconds for network stack to stabilize...");
    delay(10000);

    // Try to fetch surf data immediately on startup (before Core 0 task starts)
    Serial.println("🔄 Attempting initial surf data fetch...");
    if (fetchSurfDataFromServer()) {
        Serial.println("✅ Initial surf data fetch successful");
        lastDataFetch = millis();
    } else {
        Serial.println("⚠️ Initial surf data fetch failed, will retry later");
    }

    // Start dual-core architecture (Core 0 = Network, Core 1 = LEDs)
    DualCore::startDualCoreTasks();
}

// ==================== MAIN LOOP ====================

void loop() {
    // Handle WiFi reset button
    handleWiFiResetButton(wifiManager);

    // Handle HTTP requests
    server.handleClient();

    // Monitor WiFi health and reconnect if needed
    handleWiFiHealth();

    // NOTE: Network fetching now happens on Core 0 (Network Secretary)
    // No need to call fetchSurfDataFromServer() here - Core 0 handles it

    // Update display if state changed (decoupled architecture)
    if (lastSurfData.needsDisplayUpdate.load()) {
        Serial.println("🔄 [Core 1] Detected state change, updating display...");
        updateSurfDisplay();
        lastSurfData.needsDisplayUpdate.store(false);
    }

    // Autonomous sunset animation (V2 - calculated locally, checked on Core 1)
    if (DualCore::isSunsetTimeNow()) {
        Serial.println("🌅 [Core 1] Sunset detected - playing animation (autonomous mode)");

        // Create strip configurations from constants
        Animation::StripConfig waveHeight = {
            WAVE_HEIGHT_START,
            WAVE_HEIGHT_END,
            WAVE_HEIGHT_FORWARD,
            WAVE_HEIGHT_LENGTH
        };
        Animation::StripConfig wavePeriod = {
            WAVE_PERIOD_START,
            WAVE_PERIOD_END,
            WAVE_PERIOD_FORWARD,
            WAVE_PERIOD_LENGTH
        };
        Animation::StripConfig windSpeed = {
            WIND_SPEED_START,
            WIND_SPEED_END,
            WIND_SPEED_FORWARD,
            WIND_SPEED_LENGTH
        };

        // Play 30-second sunset animation (Core 1 - never blocks)
        Animation::playSunset(leds, waveHeight, wavePeriod, windSpeed, 30);

        // Mark sunset as played (thread-safe atomic update)
        DualCore::markSunsetPlayed();

        // Refresh surf display after animation completes
        lastSurfData.needsDisplayUpdate.store(true);
    }

    // Update blinking animations for threshold alerts
    updateBlinkingAnimation();

    // Update status LED based on data freshness
    unsigned long dataAge = millis() - lastSurfData.lastUpdate;
    if (lastSurfData.dataReceived && dataAge < DATA_STALENESS_THRESHOLD) {
        blinkGreenLED();   // ✅ Fresh data (< 30 min old)
    } else {
        showNoDataConnected();  

        // Log staleness periodically (every 60 seconds)
        static unsigned long lastStaleLog = 0;
        if (millis() - lastStaleLog > 60000) {
            if (!lastSurfData.dataReceived) {
                Serial.println("⚠️ Status: GREEN (was ORANGE) - No data received yet");
            } else {
                Serial.printf("⚠️ Status: GREEN (was ORANGE) - Data is %lu min old (threshold: %lu min)\n",
                              dataAge / 60000, DATA_STALENESS_THRESHOLD / 60000);
            }
            lastStaleLog = millis();
        }
    }

    delay(5); // Small delay to prevent excessive CPU usage
}
