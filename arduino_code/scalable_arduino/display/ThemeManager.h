#ifndef THEME_MANAGER_H
#define THEME_MANAGER_H

#include <Arduino.h>
#include <FastLED.h>

/**
 * Theme Manager
 * - Manages LED color themes
 * - Clean theme switching
 * - Extensible theme system
 */

/**
 * Theme color structure
 * Each theme defines colors for wave, wind, and period LEDs
 */
struct ThemeColors {
    CHSV wave_color;     // Wave height LED color
    CHSV wind_color;     // Wind speed LED color
    CHSV period_color;   // Wave period LED color
};

class ThemeManager {
private:
    String currentTheme;

public:
    ThemeManager() : currentTheme("classic_surf") {}

    /**
     * Get current theme name
     */
    String getCurrentTheme() const {
        return currentTheme;
    }

    /**
     * Set active theme
     * @param themeName Name of the theme to activate
     * @return true if theme exists and was set, false otherwise
     */
    bool setTheme(const String& themeName) {
        // Validate theme exists
        if (!themeExists(themeName)) {
            Serial.printf("⚠️ ThemeManager: Unknown theme '%s'\n", themeName.c_str());
            return false;
        }

        if (currentTheme != themeName) {
            currentTheme = themeName;
            Serial.printf("🎨 ThemeManager: Theme changed to '%s'\n", themeName.c_str());
        }

        return true;
    }

    /**
     * Check if a theme exists
     */
    bool themeExists(const String& themeName) const {
        return themeName == "classic_surf" ||
               themeName == "vibrant_mix" ||
               themeName == "tropical_paradise" ||
               themeName == "ocean_sunset" ||
               themeName == "electric_vibes" ||
               themeName == "dark" ||
               themeName == "day";  // Legacy fallback
    }

    /**
     * Get all colors for the current theme
     */
    ThemeColors getColors() const {
        return getColors(currentTheme);
    }

    /**
     * Get all colors for a specific theme
     */
    ThemeColors getColors(const String& theme) const {
        // 5 modern themes with distinct colors
        if (theme == "classic_surf") {
            return {
                {160, 255, 200},  // Blue waves
                {0, 50, 255},     // White wind
                {60, 255, 200}    // Yellow period
            };
        }
        else if (theme == "vibrant_mix") {
            return {
                {240, 255, 200},  // Purple waves
                {85, 255, 200},   // Green wind
                {160, 255, 200}   // Blue period
            };
        }
        else if (theme == "tropical_paradise") {
            return {
                {85, 255, 200},   // Green waves
                {140, 255, 200},  // Cyan wind
                {200, 255, 200}   // Magenta period
            };
        }
        else if (theme == "ocean_sunset") {
            return {
                {160, 255, 220},  // Blue waves
                {20, 255, 220},   // Orange wind
                {212, 255, 220}   // Pink period
            };
        }
        else if (theme == "electric_vibes") {
            return {
                {140, 255, 240},  // Cyan waves
                {60, 255, 240},   // Yellow wind
                {240, 255, 240}   // Purple period
            };
        }
        else if (theme == "dark") {
            // Legacy dark theme
            return {
                {135, 255, 255},  // Cyan waves
                {24, 250, 240},   // Orange wind
                {85, 155, 205}    // Green period
            };
        }
        else {
            // Legacy day theme / fallback - defaults to classic_surf
            return {
                {160, 255, 200},  // Blue waves
                {0, 50, 255},     // White wind
                {60, 255, 200}    // Yellow period
            };
        }
    }

    /**
     * Get wave height color for current theme
     */
    CHSV getWaveColor() const {
        return getColors().wave_color;
    }

    /**
     * Get wind speed color for current theme
     */
    CHSV getWindColor() const {
        return getColors().wind_color;
    }

    /**
     * Get wave period color for current theme
     */
    CHSV getPeriodColor() const {
        return getColors().period_color;
    }

    /**
     * Get wave height color for specific theme
     */
    CHSV getWaveColor(const String& theme) const {
        return getColors(theme).wave_color;
    }

    /**
     * Get wind speed color for specific theme
     */
    CHSV getWindColor(const String& theme) const {
        return getColors(theme).wind_color;
    }

    /**
     * Get wave period color for specific theme
     */
    CHSV getPeriodColor(const String& theme) const {
        return getColors(theme).period_color;
    }

    /**
     * Print available themes
     */
    void printAvailableThemes() const {
        Serial.println("🎨 Available Themes:");
        Serial.println("   - classic_surf (Blue waves, white wind, yellow period)");
        Serial.println("   - vibrant_mix (Purple waves, green wind, blue period)");
        Serial.println("   - tropical_paradise (Green waves, cyan wind, magenta period)");
        Serial.println("   - ocean_sunset (Blue waves, orange wind, pink period)");
        Serial.println("   - electric_vibes (Cyan waves, yellow wind, purple period)");
        Serial.println("   - dark (Legacy dark theme)");
        Serial.println("   - day (Legacy day theme, same as classic_surf)");
    }

    /**
     * Print current theme info
     */
    void printCurrentTheme() const {
        Serial.printf("🎨 Current Theme: %s\n", currentTheme.c_str());

        ThemeColors colors = getColors();

        Serial.println("   Colors:");
        Serial.printf("     Wave:   H=%d S=%d V=%d\n",
                      colors.wave_color.hue, colors.wave_color.sat, colors.wave_color.val);
        Serial.printf("     Wind:   H=%d S=%d V=%d\n",
                      colors.wind_color.hue, colors.wind_color.sat, colors.wind_color.val);
        Serial.printf("     Period: H=%d S=%d V=%d\n",
                      colors.period_color.hue, colors.period_color.sat, colors.period_color.val);
    }
};

#endif // THEME_MANAGER_H
