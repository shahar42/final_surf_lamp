/*
 * LED COLOR THEMES
 *
 * Color theme management for surf lamp LED displays.
 * Supports 5 distinct themes plus legacy themes.
 *
 * Design principles:
 * - Pure functions (no global state, no side effects)
 * - Const references prevent accidental modification
 * - Inline accessors = zero overhead (eliminated by compiler)
 * - Easy to extend (add themes in one place)
 *
 * Scott Meyers Item 23: Prefer non-member functions for better encapsulation
 */

#ifndef THEMES_H
#define THEMES_H

#include <FastLED.h>
#include <Arduino.h>

/**
 * Theme color set for three surf lamp strips
 */
struct ThemeColors {
    CHSV wave_color;    // Wave height strip color
    CHSV wind_color;    // Wind speed strip color
    CHSV period_color;  // Wave period strip color
};

/**
 * Get complete color set for a theme
 *
 * @param theme Theme name (case-sensitive)
 * @return ThemeColors struct with wave, wind, and period colors
 *
 * Available themes:
 * - "classic_surf": Blue waves, white wind, yellow period
 * - "vibrant_mix": Purple waves, green wind, blue period
 * - "tropical_paradise": Green waves, cyan wind, magenta period
 * - "ocean_sunset": Blue waves, orange wind, pink period
 * - "electric_vibes": Cyan waves, yellow wind, purple period
 * - "dark": Legacy dark theme
 * - "day": Legacy day theme (defaults to classic_surf)
 */
ThemeColors getThemeColors(const String& theme);

// Convenience accessors (inline for zero overhead)
// These are syntactic sugar for getThemeColors(theme).wave_color etc.

inline CHSV getWaveHeightColor(const String& theme) {
    return getThemeColors(theme).wave_color;
}

inline CHSV getWindSpeedColor(const String& theme) {
    return getThemeColors(theme).wind_color;
}

inline CHSV getWavePeriodColor(const String& theme) {
    return getThemeColors(theme).period_color;
}

#endif // THEMES_H
