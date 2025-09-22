/*
 * Color Test Script for Surf Lamp
 * Shows one color across ALL LEDs for 5 seconds, then moves to next color
 * Simple way to test which colors you like - just note the color number!
 *
 * 30 carefully selected colors including ocean themes, sunsets, and vibrant options
 * Each color gets a number (0-29) for easy reference
 */

#include <FastLED.h>

// Configuration - adjust these for your setup
#define NUM_STRIPS 4        // Number of LED strips
#define LEDS_PER_STRIP 10   // LEDs per strip
#define DATA_PIN_1 2        // Data pins for each strip
#define DATA_PIN_2 3
#define DATA_PIN_3 4
#define DATA_PIN_4 5

CRGB strips[NUM_STRIPS][LEDS_PER_STRIP];

// 30 Color palette for testing
CRGB test_colors[] = {
  CRGB::Red,            // 0 - Classic Red
  CRGB::Blue,           // 1 - Classic Blue
  CRGB::Green,          // 2 - Classic Green
  CRGB(0, 128, 128),    // 3 - Teal
  CRGB(64, 224, 208),   // 4 - Turquoise
  CRGB(0, 191, 255),    // 5 - Deep Sky Blue
  CRGB(30, 144, 255),   // 6 - Dodger Blue
  CRGB(0, 0, 139),      // 7 - Dark Blue
  CRGB(25, 25, 112),    // 8 - Midnight Blue
  CRGB(255, 165, 0),    // 9 - Orange
  CRGB(255, 69, 0),     // 10 - Red Orange
  CRGB(255, 20, 147),   // 11 - Deep Pink
  CRGB(255, 105, 180),  // 12 - Hot Pink
  CRGB(138, 43, 226),   // 13 - Blue Violet
  CRGB(75, 0, 130),     // 14 - Indigo
  CRGB(255, 215, 0),    // 15 - Gold
  CRGB(255, 140, 0),    // 16 - Dark Orange
  CRGB(220, 20, 60),    // 17 - Crimson
  CRGB(255, 192, 203),  // 18 - Pink
  CRGB(173, 216, 230),  // 19 - Light Blue
  CRGB(144, 238, 144),  // 20 - Light Green
  CRGB(221, 160, 221),  // 21 - Plum
  CRGB(50, 205, 50),    // 22 - Lime Green
  CRGB(255, 0, 255),    // 23 - Fuchsia
  CRGB(0, 255, 255),    // 24 - Aqua
  CRGB(255, 255, 0),    // 25 - Bright Yellow
  CRGB(255, 182, 193),  // 26 - Light Pink
  CRGB(175, 238, 238),  // 27 - Pale Turquoise
  CRGB(230, 230, 250),  // 28 - Lavender
  CRGB::White           // 29 - White
};

String color_names[] = {
  "Classic Red",         // 0
  "Classic Blue",        // 1
  "Classic Green",       // 2
  "Teal",               // 3
  "Turquoise",          // 4
  "Deep Sky Blue",      // 5
  "Dodger Blue",        // 6
  "Dark Blue",          // 7
  "Midnight Blue",      // 8
  "Orange",             // 9
  "Red Orange",         // 10
  "Deep Pink",          // 11
  "Hot Pink",           // 12
  "Blue Violet",        // 13
  "Indigo",             // 14
  "Gold",               // 15
  "Dark Orange",        // 16
  "Crimson",            // 17
  "Pink",               // 18
  "Light Blue",         // 19
  "Light Green",        // 20
  "Plum",               // 21
  "Lime Green",         // 22
  "Fuchsia",            // 23
  "Aqua",               // 24
  "Bright Yellow",      // 25
  "Light Pink",         // 26
  "Pale Turquoise",     // 27
  "Lavender",           // 28
  "White"               // 29
};

int num_colors = 30;
int current_color_index = 0;
unsigned long last_change = 0;
const unsigned long DISPLAY_TIME = 5000; // 5 seconds per color

void setup() {
  Serial.begin(115200);

  // Initialize LED strips
  FastLED.addLeds<WS2812B, DATA_PIN_1, GRB>(strips[0], LEDS_PER_STRIP);
  FastLED.addLeds<WS2812B, DATA_PIN_2, GRB>(strips[1], LEDS_PER_STRIP);
  FastLED.addLeds<WS2812B, DATA_PIN_3, GRB>(strips[2], LEDS_PER_STRIP);
  FastLED.addLeds<WS2812B, DATA_PIN_4, GRB>(strips[3], LEDS_PER_STRIP);

  FastLED.setBrightness(100); // Adjust brightness (0-255)

  Serial.println("=== SURF LAMP COLOR TEST ===");
  Serial.println("30 colors - each shown for 5 seconds");
  Serial.println("ALL LEDs will be the same color");
  Serial.println("Just note the COLOR NUMBER for ones you like!");
  Serial.println("Commands: 'n'=next, 'p'=previous, 'r'=restart");
  Serial.println("================================");

  displayCurrentColor();
}

void loop() {
  if (millis() - last_change > DISPLAY_TIME) {
    nextColor();
    displayCurrentColor();
    last_change = millis();
  }

  // Check for serial input for manual control
  if (Serial.available()) {
    char input = Serial.read();
    switch(input) {
      case 'n': // Next color
        nextColor();
        displayCurrentColor();
        last_change = millis();
        break;
      case 'p': // Previous color
        previousColor();
        displayCurrentColor();
        last_change = millis();
        break;
      case 'r': // Restart from beginning
        current_color_index = 0;
        displayCurrentColor();
        last_change = millis();
        break;
    }
  }
}

void nextColor() {
  current_color_index = (current_color_index + 1) % num_colors;
}

void previousColor() {
  current_color_index = (current_color_index - 1 + num_colors) % num_colors;
}

void displayCurrentColor() {
  // Set ALL LEDs to the same current color
  CRGB current_color = test_colors[current_color_index];

  for (int strip = 0; strip < NUM_STRIPS; strip++) {
    for (int led = 0; led < LEDS_PER_STRIP; led++) {
      strips[strip][led] = current_color;
    }
  }

  FastLED.show();
  printCurrentColor();
}

void printCurrentColor() {
  Serial.println();
  Serial.println("================================");
  Serial.print("COLOR #");
  Serial.print(current_color_index);
  Serial.print(": ");
  Serial.println(color_names[current_color_index]);

  CRGB color = test_colors[current_color_index];
  CHSV hsvColor = rgb2hsv_approximate(color);

  Serial.print("RGB Values: (");
  Serial.print(color.r);
  Serial.print(", ");
  Serial.print(color.g);
  Serial.print(", ");
  Serial.print(color.b);
  Serial.println(")");

  Serial.print("HSV Values: (");
  Serial.print(hsvColor.h);
  Serial.print(", ");
  Serial.print(hsvColor.s);
  Serial.print(", ");
  Serial.print(hsvColor.v);
  Serial.println(")");

  Serial.print("Progress: ");
  Serial.print(current_color_index + 1);
  Serial.print("/");
  Serial.println(num_colors);
  Serial.println("================================");
}