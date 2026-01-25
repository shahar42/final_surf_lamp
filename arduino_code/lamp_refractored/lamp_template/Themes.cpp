/*
 * LED COLOR THEMES - IMPLEMENTATION
 *
 * Color theme definitions for surf lamp LED displays.
 */

#include "Themes.h"

// ---------------------------- Color Maps ----------------------------
// Legacy color maps (currently unused but preserved for potential future features)

CHSV colorMap[] = {
    CHSV(120, 255, 125), CHSV(130, 255, 200), CHSV(140, 255, 255), CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(190, 255, 255), CHSV(200, 255, 200),
    CHSV(210, 255, 255), CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(110, 255, 255), CHSV(0, 0, 255)
};

CHSV colorMapWave[] = {
    CHSV(95, 255, 125),  CHSV(95, 255, 200),  CHSV(140, 255, 255), CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(190, 255, 255), CHSV(200, 255, 200),
    CHSV(210, 255, 255), CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(85, 255, 255),  CHSV(85, 255, 255)
};

CHSV colorMapWind[] = {
    CHSV(85, 255, 125),  CHSV(90, 255, 200),  CHSV(95, 255, 255),  CHSV(150, 255, 200),
    CHSV(160, 255, 255), CHSV(180, 255, 200), CHSV(87, 255, 255),  CHSV(90, 255, 200),
    CHSV(95, 255, 255),  CHSV(220, 255, 255), CHSV(20, 255, 255),  CHSV(10, 255, 255),
    CHSV(0, 255, 255),   CHSV(0, 255, 200),   CHSV(60, 255, 255),  CHSV(90, 255, 200),
    CHSV(120, 255, 255), CHSV(150, 255, 200), CHSV(180, 255, 255), CHSV(210, 255, 200),
    CHSV(240, 255, 255), CHSV(100, 255, 255), CHSV(85, 255, 255),  CHSV(85, 255, 255)
};

// ---------------------------- Theme Functions ----------------------------

ThemeColors getThemeColors(const String& theme) {
    // 5 LED themes with completely distinct colors (minimal red to avoid alarm appearance)

    if (theme == "classic_surf") {
        // Blue waves, white wind, yellow period - Traditional surf colors
        return {CHSV(160, 255, 200), CHSV(0, 50, 255), CHSV(60, 255, 200)};

    } else if (theme == "vibrant_mix") {
        // Purple waves, green wind, blue period - Vibrant and distinct
        return {CHSV(240, 255, 200), CHSV(85, 255, 200), CHSV(160, 255, 200)};

    } else if (theme == "tropical_paradise") {
        // Green waves, cyan wind, magenta period - Tropical feel
        return {CHSV(85, 255, 200), CHSV(140, 255, 200), CHSV(200, 255, 200)};

    } else if (theme == "ocean_sunset") {
        // Blue waves, orange wind, pink period - Sunset colors
        return {CHSV(160, 255, 220), CHSV(20, 255, 220), CHSV(212, 255, 220)};

    } else if (theme == "electric_vibes") {
        // Cyan waves, yellow wind, purple period - High energy
        return {CHSV(140, 255, 240), CHSV(60, 255, 240), CHSV(240, 255, 240)};

    } else if (theme == "dark") {
        // Legacy dark theme - Preserved for backward compatibility
        return {CHSV(135, 255, 255), CHSV(24, 250, 240), CHSV(85, 155, 205)};

    } else {
        // Legacy "day" theme OR unknown theme - Default to classic_surf
        // This ensures graceful handling of invalid theme names
        return {CHSV(160, 255, 200), CHSV(0, 50, 255), CHSV(60, 255, 200)};
    }
}
