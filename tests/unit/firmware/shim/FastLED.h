// FastLED stand-in: colour structs only, no LED output.
#pragma once
#include <cstdint>

struct CHSV {
    uint8_t h = 0, s = 0, v = 0;
    CHSV() {}
    CHSV(uint8_t hh, uint8_t ss, uint8_t vv) : h(hh), s(ss), v(vv) {}
};

struct CRGB {
    uint8_t r = 0, g = 0, b = 0;
    CRGB() {}
    CRGB(uint8_t rr, uint8_t gg, uint8_t bb) : r(rr), g(gg), b(bb) {}
    static const CRGB Black, White, Red, Green, Blue, Yellow, Orange, Purple;
};
inline const CRGB CRGB::Black{0, 0, 0}, CRGB::White{255, 255, 255}, CRGB::Red{255, 0, 0},
    CRGB::Green{0, 255, 0}, CRGB::Blue{0, 0, 255}, CRGB::Yellow{255, 255, 0},
    CRGB::Orange{255, 165, 0}, CRGB::Purple{128, 0, 128};
