/*
 * LED COLOR THEMES
 *author: Shahar
 *date: 6/2/2026
 * Color theme management for surf lamp LED displays.
 */

#ifndef THEMES_H
#define THEMES_H

#include <FastLED.h>
#include <Arduino.h>

// Theme indices (must match LEDTheme enum in esp_Server_encoding.hpp)
static constexpr uint8_t THEME_CLASSIC_SURF      = 0;
static constexpr uint8_t THEME_VIBRANT_MIX        = 1;
static constexpr uint8_t THEME_TROPICAL_PARADISE  = 2;
static constexpr uint8_t THEME_OCEAN_SUNSET       = 3;
static constexpr uint8_t THEME_ELECTRIC_VIBES     = 4;
static constexpr uint8_t THEME_DARK               = 5;
static constexpr uint8_t THEME_COUNT              = 6;

/**
 * Theme color set for three surf lamp strips
 */
struct ThemeColors {
    CHSV wave_color;    // Wave height strip color
    CHSV wind_color;    // Wind speed strip color
    CHSV period_color;  // Wave period strip color
};

/**
 * Get complete color set for a theme by index
 *
 * @param themeIndex Theme index (0-5, see THEME_* constants)
 * @return ThemeColors struct with wave, wind, and period colors
 */
ThemeColors getThemeColors(uint8_t themeIndex);

/**
 * Convert theme name string to index (for JSON API path)
 * Returns THEME_CLASSIC_SURF for unknown names
 */
uint8_t themeNameToIndex(const char* name);

/**
 * Get theme name for logging/display
 */
const char* themeIndexToName(uint8_t themeIndex);

// Convenience accessors (inline for zero overhead)
inline CHSV getWaveHeightColor(uint8_t themeIndex) {
    return getThemeColors(themeIndex).wave_color;
}

inline CHSV getWindSpeedColor(uint8_t themeIndex) {
    return getThemeColors(themeIndex).wind_color;
}

inline CHSV getWavePeriodColor(uint8_t themeIndex) {
    return getThemeColors(themeIndex).period_color;
}

#endif // THEMES_H
