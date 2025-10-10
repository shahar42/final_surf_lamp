/*
 * LED Mapper Tool - Single Strip Configuration Helper
 *
 * Purpose: Identify LED indices for a continuous strip wrapped to appear as 3 separate strips
 *
 * Usage:
 * 1. Upload this sketch to your ESP32 with the wrapped LED strip
 * 2. Open Serial Monitor (115200 baud)
 * 3. Enter LED index numbers (0-N) to light up that specific LED
 * 4. Record which indices correspond to each visual "strip"
 * 5. Update MAPPING_NOTES.md with your findings
 *
 * Commands:
 * - Enter number (0-N): Light up LED at that index
 * - "off" or "0": Turn off all LEDs
 * - "test": Run full strip test (lights all LEDs in sequence)
 * - "rainbow": Rainbow animation across entire strip
 */

#include <FastLED.h>

// ---------------------------- Configuration ----------------------------
#define LED_PIN 2              // D2 = GPIO 2 (single wrapped strip)
#define TOTAL_LEDS 150        // Increased - if your strip has fewer, that's OK
#define BRIGHTNESS 255        // LED brightness (0-255) - MAX for testing
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

// ---------------------------- Global Variables ----------------------------
CRGB leds[TOTAL_LEDS];
int currentLED = -1;

// ---------------------------- Setup ----------------------------
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n╔════════════════════════════════════════════════════════════╗");
    Serial.println("║         LED MAPPER TOOL - Single Strip Configuration       ║");
    Serial.println("╚════════════════════════════════════════════════════════════╝");
    Serial.println();
    Serial.println("📋 Purpose: Identify LED indices for wrapped strip configuration");
    Serial.println();
    Serial.printf("🔧 Configuration:\n");
    Serial.printf("   Pin: %d\n", LED_PIN);
    Serial.printf("   Total LEDs: %d\n", TOTAL_LEDS);
    Serial.printf("   Brightness: %d/255\n", BRIGHTNESS);
    Serial.println();

    // Initialize FastLED
    Serial.println("🔄 Initializing FastLED library...");
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();
    Serial.println("✅ FastLED initialized!");

    // HARDWARE TEST: Aggressive startup test
    Serial.println();
    Serial.println("🧪 RUNNING HARDWARE TEST...");
    Serial.println("   Testing if LEDs respond at all...");
    Serial.println();
    Serial.println("⚠️  WATCH YOUR LAMP CAREFULLY - Testing GPIO 2...");

    // Test 1: All white
    Serial.println("   Test 1/4: All LEDs WHITE (max brightness)...");
    fill_solid(leds, TOTAL_LEDS, CRGB::White);
    FastLED.setBrightness(255); // Max brightness
    FastLED.show();
    delay(3000); // Longer delay

    // Test 2: All red
    Serial.println("   Test 2/4: All LEDs RED...");
    fill_solid(leds, TOTAL_LEDS, CRGB::Red);
    FastLED.show();
    delay(2000);

    // Test 3: All green
    Serial.println("   Test 3/4: All LEDs GREEN...");
    fill_solid(leds, TOTAL_LEDS, CRGB::Green);
    FastLED.show();
    delay(2000);

    // Test 4: All blue
    Serial.println("   Test 4/4: All LEDs BLUE...");
    fill_solid(leds, TOTAL_LEDS, CRGB::Blue);
    FastLED.show();
    delay(2000);

    // Clear and reset
    FastLED.clear();
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.show();

    Serial.println("✅ Hardware test complete!");
    Serial.println();
    Serial.println("⚠️  DID YOU SEE ANY LEDS LIGHT UP DURING THE TEST?");
    Serial.println("    - If YES: Hardware is working! Type any command to continue.");
    Serial.println("    - If NO: Read troubleshooting below...");
    Serial.println();
    Serial.println("🔍 TROUBLESHOOTING:");
    Serial.println("    1. Is external 5V power connected and ON?");
    Serial.println("    2. Are GND pins connected (ESP32 GND to Power GND)?");
    Serial.println("    3. Is data wire connected to GPIO 2?");
    Serial.println("    4. Try changing LED_PIN to 4 or 5 at top of code");
    Serial.println();

    Serial.println("💡 LED strip initialized!");
    Serial.println();
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    Serial.println("📝 COMMANDS:");
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    Serial.println("  [0-N]     → Light up LED at index N");
    Serial.println("  off       → Turn off all LEDs");
    Serial.println("  test      → Light up all LEDs in sequence");
    Serial.println("  rainbow   → Rainbow animation");
    Serial.println("  help      → Show this help message");
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    Serial.println();
    Serial.println("🎯 Ready! Enter LED index to begin mapping...");
    Serial.println();
}

// ---------------------------- Main Loop ----------------------------
void loop() {
    if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        input.toLowerCase();

        Serial.println("─────────────────────────────────────────────────────────");

        if (input == "off" || input == "0") {
            turnOffAll();
        }
        else if (input == "test") {
            runFullTest();
        }
        else if (input == "rainbow") {
            runRainbow();
        }
        else if (input == "help") {
            showHelp();
        }
        else {
            // Try to parse as LED index
            int ledIndex = input.toInt();

            // Validate index
            if (ledIndex >= 0 && ledIndex < TOTAL_LEDS) {
                lightUpLED(ledIndex);
            } else if (input.length() > 0) {
                Serial.printf("❌ Invalid index: %s (must be 0-%d)\n", input.c_str(), TOTAL_LEDS - 1);
                Serial.println("💡 Type 'help' for available commands");
            }
        }

        Serial.println("─────────────────────────────────────────────────────────");
        Serial.println();
    }
}

// ---------------------------- LED Control Functions ----------------------------

void lightUpLED(int index) {
    // Turn off previous LED
    FastLED.clear();

    // Light up requested LED in white
    leds[index] = CRGB::White;
    FastLED.show();

    currentLED = index;

    Serial.printf("✅ LED %d is now ON (WHITE)\n", index);
    Serial.println();
    Serial.println("📍 MAPPING GUIDE:");
    Serial.println("   → Look at your lamp and note which physical position is lit");
    Serial.println("   → Record in MAPPING_NOTES.md:");
    Serial.printf("      - Strip 1 (wave height): Start = ?, End = ?\n");
    Serial.printf("      - Strip 2 (wave period): Start = ?, End = ?\n");
    Serial.printf("      - Strip 3 (wind speed):  Start = ?, End = ?\n");
}

void turnOffAll() {
    FastLED.clear();
    FastLED.show();
    currentLED = -1;

    Serial.println("🌑 All LEDs turned OFF");
}

void runFullTest() {
    Serial.println("🧪 Running full strip test...");
    Serial.println("   Lighting each LED in sequence (0.5s each)");
    Serial.println();

    for (int i = 0; i < TOTAL_LEDS; i++) {
        FastLED.clear();
        leds[i] = CRGB::Cyan;
        FastLED.show();

        Serial.printf("   LED %d\n", i);
        delay(500);
    }

    FastLED.clear();
    FastLED.show();

    Serial.println();
    Serial.println("✅ Full test completed!");
}

void runRainbow() {
    Serial.println("🌈 Running rainbow animation...");
    Serial.println("   Press any key to stop");
    Serial.println();

    for (int hue = 0; hue < 256 * 3 && !Serial.available(); hue++) {
        fill_rainbow(leds, TOTAL_LEDS, hue, 256 / TOTAL_LEDS);
        FastLED.show();
        delay(10);
    }

    // Clear serial buffer
    while (Serial.available()) {
        Serial.read();
    }

    FastLED.clear();
    FastLED.show();

    Serial.println("✅ Rainbow animation stopped!");
}

void showHelp() {
    Serial.println("📖 LED MAPPER TOOL - HELP");
    Serial.println();
    Serial.println("BASIC USAGE:");
    Serial.println("  1. Enter a number (0-89) to light that LED");
    Serial.println("  2. Observe which physical position lights up on your lamp");
    Serial.println("  3. Record the index ranges for each visual strip");
    Serial.println();
    Serial.println("MAPPING STRATEGY:");
    Serial.println("  → Start with index 0 - where is it physically?");
    Serial.println("  → Try index 29, 30, 59, 60, etc. to find boundaries");
    Serial.println("  → Test middle indices to confirm strip ranges");
    Serial.println();
    Serial.println("COMMANDS:");
    Serial.println("  [0-N]     → Light up LED at index N");
    Serial.println("  off       → Turn off all LEDs");
    Serial.println("  test      → Light up all LEDs in sequence (helps find total count)");
    Serial.println("  rainbow   → Rainbow animation (verifies all LEDs work)");
    Serial.println("  help      → Show this help message");
    Serial.println();
    Serial.println("WHAT TO RECORD:");
    Serial.println("  For each visual strip, record:");
    Serial.println("    - Start index (first LED of that strip)");
    Serial.println("    - End index (last LED of that strip)");
    Serial.println("    - Total count (end - start + 1)");
    Serial.println("    - Direction (does it go up or down?)");
    Serial.println();
    Serial.println("EXAMPLE FINDINGS:");
    Serial.println("  Strip 1 (Right - Wave Height):  LEDs 0-29   (30 total, bottom-up)");
    Serial.println("  Strip 2 (Left - Wave Period):   LEDs 30-59  (30 total, bottom-up)");
    Serial.println("  Strip 3 (Center - Wind Speed):  LEDs 60-89  (30 total, bottom-up)");
    Serial.println();
    Serial.println("💡 TIP: Use 'test' command to quickly find the total LED count!");
}

// ---------------------------- Startup Animation (Optional) ----------------------------
// Uncomment this function and call it in setup() for a nice startup effect

/*
void startupAnimation() {
    Serial.println("✨ Running startup animation...");

    // Chase animation
    for (int i = 0; i < TOTAL_LEDS; i++) {
        leds[i] = CRGB::Blue;
        FastLED.show();
        delay(20);
    }

    // Fade out
    for (int brightness = 100; brightness >= 0; brightness -= 5) {
        FastLED.setBrightness(brightness);
        FastLED.show();
        delay(20);
    }

    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    Serial.println("✅ Startup animation complete!");
}
*/
