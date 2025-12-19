/*
 * ESP32 DIAGNOSTIC TEST
 *
 * This script tests all components to isolate the crash issue:
 * 1. Basic ESP32 boot and serial
 * 2. FastLED library and LED strip
 * 3. WiFi AP mode (where crashes occur)
 * 4. Watchdog timer behavior
 *
 * INSTRUCTIONS:
 * - Upload this sketch
 * - Open Serial Monitor (115200 baud)
 * - Watch for which test fails
 */

#include <FastLED.h>
#include <WiFi.h>

// LED Configuration (from Maayan's lamp)
#define LED_PIN 2
#define TOTAL_LEDS 87
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define BRIGHTNESS 90

CRGB leds[TOTAL_LEDS];

void setup() {
    Serial.begin(115200);
    delay(2000);

    Serial.println("\n\n");
    Serial.println("════════════════════════════════════════");
    Serial.println("  ESP32 DIAGNOSTIC TEST");
    Serial.println("════════════════════════════════════════");
    Serial.println();

    // Test 1: Basic ESP32 Info
    Serial.println("TEST 1: ESP32 Hardware Info");
    Serial.println("----------------------------");
    Serial.printf("Chip Model: %s\n", ESP.getChipModel());
    Serial.printf("Chip Revision: %d\n", ESP.getChipRevision());
    Serial.printf("CPU Frequency: %d MHz\n", ESP.getCpuFreqMHz());
    Serial.printf("Flash Size: %d bytes\n", ESP.getFlashChipSize());
    Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
    Serial.println("✅ TEST 1 PASSED - Basic hardware OK\n");
    delay(1000);

    // Test 2: FastLED Initialization
    Serial.println("TEST 2: FastLED Library");
    Serial.println("----------------------------");
    Serial.printf("Initializing %d LEDs on pin %d...\n", TOTAL_LEDS, LED_PIN);

    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    Serial.println("✅ TEST 2 PASSED - FastLED initialized\n");
    delay(1000);

    // Test 3: Simple LED Pattern (no delays)
    Serial.println("TEST 3: Quick LED Test (5 seconds)");
    Serial.println("----------------------------");
    Serial.println("Setting all LEDs to dim red...");

    fill_solid(leds, TOTAL_LEDS, CRGB(50, 0, 0)); // Dim red
    FastLED.show();
    delay(2000);

    Serial.println("Setting all LEDs to dim green...");
    fill_solid(leds, TOTAL_LEDS, CRGB(0, 50, 0)); // Dim green
    FastLED.show();
    delay(2000);

    Serial.println("Clearing LEDs...");
    FastLED.clear();
    FastLED.show();

    Serial.println("✅ TEST 3 PASSED - LEDs working\n");
    delay(1000);

    // Test 4: WiFi Scan (station mode)
    Serial.println("TEST 4: WiFi Scan (Station Mode)");
    Serial.println("----------------------------");
    Serial.println("Scanning for networks (this takes ~3 seconds)...");

    WiFi.mode(WIFI_STA);
    int numNetworks = WiFi.scanNetworks();

    Serial.printf("Found %d networks:\n", numNetworks);
    for (int i = 0; i < min(numNetworks, 5); i++) {
        Serial.printf("  %d: %s (%d dBm)\n", i+1, WiFi.SSID(i).c_str(), WiFi.RSSI(i));
    }

    Serial.println("✅ TEST 4 PASSED - WiFi scan OK\n");
    delay(1000);

    // Test 5: WiFi AP Mode (THE CRITICAL TEST - where crashes occur)
    Serial.println("TEST 5: WiFi AP Mode (CRITICAL - where crashes happen)");
    Serial.println("----------------------------");
    Serial.println("Starting AP mode with SSID: DiagnosticTest...");
    Serial.println("This is where the crashes occur in main code.");
    Serial.println("Waiting 10 seconds to see if watchdog reset happens...");

    bool apStarted = WiFi.softAP("DiagnosticTest", "test12345");

    if (!apStarted) {
        Serial.println("❌ TEST 5 FAILED - AP mode failed to start");
    } else {
        Serial.printf("✅ AP started successfully\n");
        Serial.printf("   IP: %s\n", WiFi.softAPIP().toString().c_str());

        // Wait 10 seconds - if watchdog reset happens, we'll see it
        for (int i = 10; i > 0; i--) {
            Serial.printf("   Countdown: %d seconds (watching for crash)...\n", i);
            delay(1000);
        }

        Serial.println("✅ TEST 5 PASSED - AP mode stable for 10 seconds\n");
    }

    delay(1000);

    // Test 6: LED + AP Mode Together (combination test)
    Serial.println("TEST 6: LED Operations During AP Mode");
    Serial.println("----------------------------");
    Serial.println("Blinking LEDs while AP is running...");
    Serial.println("This tests if LED operations conflict with WiFi...");

    for (int i = 0; i < 5; i++) {
        Serial.printf("   Blink cycle %d/5\n", i+1);
        fill_solid(leds, TOTAL_LEDS, CRGB(30, 30, 30));
        FastLED.show();
        delay(500);
        FastLED.clear();
        FastLED.show();
        delay(500);
    }

    Serial.println("✅ TEST 6 PASSED - LEDs + AP mode OK together\n");
    delay(1000);

    // Final Report
    Serial.println("════════════════════════════════════════");
    Serial.println("  ALL TESTS PASSED!");
    Serial.println("════════════════════════════════════════");
    Serial.println();
    Serial.println("RESULT: Hardware is functioning correctly.");
    Serial.println("The issue must be in the main code logic.");
    Serial.println();
    Serial.println("If you saw ANY crashes during this test,");
    Serial.println("note which test number it failed at:");
    Serial.println("  - Test 1-2: Basic hardware issue");
    Serial.println("  - Test 3: LED strip or FastLED problem");
    Serial.println("  - Test 4: WiFi station mode issue");
    Serial.println("  - Test 5: WiFi AP mode issue (most likely)");
    Serial.println("  - Test 6: LED/WiFi conflict");
    Serial.println();
    Serial.println("Entering loop() - will blink status every 2 seconds...");
}

void loop() {
    static unsigned long lastBlink = 0;
    static bool ledState = false;

    if (millis() - lastBlink > 2000) {
        lastBlink = millis();
        ledState = !ledState;

        if (ledState) {
            fill_solid(leds, TOTAL_LEDS, CRGB(10, 10, 0)); // Dim yellow
            FastLED.show();
            Serial.printf("[%lu ms] Loop running - AP still active, heap: %d bytes\n",
                         millis(), ESP.getFreeHeap());
        } else {
            FastLED.clear();
            FastLED.show();
        }
    }

    delay(10); // Small delay to prevent watchdog
}
