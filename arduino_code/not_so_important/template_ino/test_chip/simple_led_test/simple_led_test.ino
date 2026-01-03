#include <FastLED.h>

#define LED_PIN     2
#define NUM_LEDS    120
#define BRIGHTNESS  50
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB

CRGB leds[NUM_LEDS];

void setup() {
    delay(2000); // Safety delay
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
}

void loop() {
    // Light up all LEDs in Cyan
    fill_solid(leds, NUM_LEDS, CRGB::Cyan);
    FastLED.show();
    delay(500); // Wait 0.5 second

    // Turn off (Blink)
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    delay(500); // Wait 0.5 second
}