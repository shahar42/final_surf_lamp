/*
 * SUNSET ANIMATION TEST - Standalone Demo
 *
 * Tests the sunset animation on Maayan's lamp configuration
 * Press button to trigger animation, or set AUTO_PLAY to loop continuously
 *
 * Hardware: 56 LEDs (3 strips: Wave Height, Wave Period, Wind Speed)
 */

#include <FastLED.h>
#include "animation.h"

// ---------------- HARDWARE SETUP ----------------
#define LED_PIN 2              // GPIO pin connected to LED strip data line
#define TOTAL_LEDS 56          // Total number of LEDs in the physical strip
#define LED_TYPE WS2812B       // LED chipset type
#define COLOR_ORDER GRB        // Color order for your LED strip
#define BRIGHTNESS 75          // Global brightness (0-255)
#define BUTTON_PIN 0           // ESP32 boot button

// ---------------- LED STRIP MAPPING (Maayan's Lamp) ----------------
// Wave Height Strip (Right Side) - 14 LEDs
#define WAVE_HEIGHT_START 3
#define WAVE_HEIGHT_END 16
#define WAVE_HEIGHT_LENGTH 14
#define WAVE_HEIGHT_FORWARD true

// Wave Period Strip (Left Side) - 15 LEDs
#define WAVE_PERIOD_START 42
#define WAVE_PERIOD_END 55
#define WAVE_PERIOD_LENGTH 14
#define WAVE_PERIOD_FORWARD true

// Wind Speed Strip (Center) - 18 LEDs (REVERSE)
#define WIND_SPEED_START 38
#define WIND_SPEED_END 21
#define WIND_SPEED_LENGTH 18
#define WIND_SPEED_FORWARD false

// ---------------- CONFIGURATION ----------------
#define AUTO_PLAY true         // Set false to only play on button press
#define ANIMATION_DURATION 30  // Animation duration in seconds
#define AUTO_PLAY_INTERVAL 60000  // Time between auto-plays (60 seconds)

// Global LED array
CRGB leds[TOTAL_LEDS];

// Timing
unsigned long lastAutoPlay = 0;
bool buttonPressed = false;

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌅 ================================================================");
    Serial.println("🌅 SUNSET ANIMATION TEST");
    Serial.println("🌅 ================================================================");
    Serial.println();
    Serial.printf("Total LEDs: %d\n", TOTAL_LEDS);
    Serial.printf("Wave Height: %d LEDs (indices %d→%d, %s)\n",
                  WAVE_HEIGHT_LENGTH, WAVE_HEIGHT_START, WAVE_HEIGHT_END,
                  WAVE_HEIGHT_FORWARD ? "FORWARD" : "REVERSE");
    Serial.printf("Wave Period: %d LEDs (indices %d→%d, %s)\n",
                  WAVE_PERIOD_LENGTH, WAVE_PERIOD_START, WAVE_PERIOD_END,
                  WAVE_PERIOD_FORWARD ? "FORWARD" : "REVERSE");
    Serial.printf("Wind Speed: %d LEDs (indices %d→%d, %s)\n",
                  WIND_SPEED_LENGTH, WIND_SPEED_START, WIND_SPEED_END,
                  WIND_SPEED_FORWARD ? "FORWARD" : "REVERSE");
    Serial.println();
    Serial.printf("Animation duration: %d seconds\n", ANIMATION_DURATION);
    Serial.printf("Auto-play: %s\n", AUTO_PLAY ? "ENABLED" : "DISABLED (button only)");
    if (AUTO_PLAY) {
        Serial.printf("Auto-play interval: %d seconds\n", AUTO_PLAY_INTERVAL / 1000);
    }
    Serial.println();

    // Initialize button
    pinMode(BUTTON_PIN, INPUT_PULLUP);

    // Initialize LED strip
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    Serial.println("💡 LED strip initialized");

    // Startup indicator - quick rainbow
    Serial.println("🌈 Running startup rainbow...");
    for (int hue = 0; hue < 256; hue += 5) {
        fill_solid(leds, TOTAL_LEDS, CHSV(hue, 255, 80));
        FastLED.show();
        delay(10);
    }

    FastLED.clear();
    FastLED.show();

    Serial.println("✅ Setup complete!");
    Serial.println("\n🎬 Press button to trigger sunset animation");
    Serial.println("================================================================\n");
}

void loop() {
    // Check button press (active low)
    if (digitalRead(BUTTON_PIN) == LOW) {
        if (!buttonPressed) {
            buttonPressed = true;
            playSunsetAnimation();

            // Debounce
            delay(500);
        }
    } else {
        buttonPressed = false;
    }

    // Auto-play mode
    if (AUTO_PLAY) {
        if (millis() - lastAutoPlay >= AUTO_PLAY_INTERVAL) {
            playSunsetAnimation();
            lastAutoPlay = millis();
        }
    }

    delay(10);
}

void playSunsetAnimation() {
    Serial.println("🌅 ============================================================");
    Serial.println("🌅 STARTING SUNSET ANIMATION");
    Serial.println("🌅 ============================================================");

    // Create strip configurations
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

    // Play animation
    Animation::playSunset(leds, waveHeight, wavePeriod, windSpeed, ANIMATION_DURATION);

    Serial.println("✅ ANIMATION COMPLETE");
    Serial.println("============================================================\n");

    // Leave LEDs off after animation
    FastLED.clear();
    FastLED.show();
}
