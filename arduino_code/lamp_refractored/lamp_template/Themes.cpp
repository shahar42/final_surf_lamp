/*
 * LED COLOR THEMES - IMPLEMENTATION
 *
 * Color theme definitions for surf lamp LED displays.
 * Array-indexed for O(1) lookup and cache-friendly access.
 */

#include "Themes.h"
#include <string.h>

// Theme color table - indexed by THEME_* constants
// Order MUST match the THEME_* constants in Themes.h
static const ThemeColors themeTable[THEME_COUNT] = {
    // THEME_CLASSIC_SURF (0): Blue waves, white wind, yellow period
    {CHSV(160, 255, 200), CHSV(0, 50, 255), CHSV(60, 255, 200)},
    // THEME_VIBRANT_MIX (1): Purple waves, green wind, blue period
    {CHSV(240, 255, 200), CHSV(85, 255, 200), CHSV(160, 255, 200)},
    // THEME_TROPICAL_PARADISE (2): Green waves, cyan wind, magenta period
    {CHSV(85, 255, 200), CHSV(140, 255, 200), CHSV(200, 255, 200)},
    // THEME_OCEAN_SUNSET (3): Blue waves, orange wind, pink period
    {CHSV(160, 255, 220), CHSV(20, 255, 220), CHSV(212, 255, 220)},
    // THEME_ELECTRIC_VIBES (4): Cyan waves, yellow wind, purple period
    {CHSV(140, 255, 240), CHSV(60, 255, 240), CHSV(240, 255, 240)}
};

// Theme name table for string conversion.
// Names MUST match cpp_encoder.theme_to_enum and api_user.valid_themes on the server.
static const char* const themeNames[THEME_COUNT] = {
    "classic_surf",
    "vibrant_mix",
    "tropical_paradise",
    "ocean_sunset",
    "electric_vibes"
};

ThemeColors getThemeColors(uint8_t themeIndex) {
    if (themeIndex >= THEME_COUNT) {
        return themeTable[THEME_CLASSIC_SURF];
    }
    return themeTable[themeIndex];
}

uint8_t themeNameToIndex(const char* name) {
    for (uint8_t i = 0; i < THEME_COUNT; i++) {
        if (strcmp(name, themeNames[i]) == 0) {
            return i;
        }
    }
    return THEME_CLASSIC_SURF;  // Default for unknown names (including "day")
}

const char* themeIndexToName(uint8_t themeIndex) {
    if (themeIndex >= THEME_COUNT) {
        return themeNames[THEME_CLASSIC_SURF];
    }
    return themeNames[themeIndex];
}
