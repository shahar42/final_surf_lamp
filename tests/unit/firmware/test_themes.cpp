// Themes.cpp name<->index table, and its agreement with the V3 wire enum.
#include <cstring>

#include "check.h"
#include "Themes.h"
#include "esp_Server_encoding.hpp"

int main() {
    const char* names[] = {"classic_surf", "vibrant_mix", "tropical_paradise", "ocean_sunset", "electric_vibes", "dark"};

    TEST(name_to_index_roundtrip_all_themes) {
        for (uint8_t i = 0; i < THEME_COUNT; ++i) {
            CHECK_EQ(themeNameToIndex(names[i]), i);
            CHECK(std::strcmp(themeIndexToName(i), names[i]) == 0);
        }
    }

    TEST(unknown_name_falls_back_to_classic) {
        CHECK_EQ(themeNameToIndex("neon"), THEME_CLASSIC_SURF);
        CHECK_EQ(themeNameToIndex("day"), THEME_CLASSIC_SURF);   // legacy web value
        CHECK_EQ(themeNameToIndex(""), THEME_CLASSIC_SURF);
    }

    TEST(out_of_range_index_falls_back_to_classic) {
        CHECK(std::strcmp(themeIndexToName(THEME_COUNT), "classic_surf") == 0);
        CHECK(std::strcmp(themeIndexToName(255), "classic_surf") == 0);
    }

    TEST(theme_indices_match_v3_wire_enum) {
        CHECK_EQ((int)LEDTheme::CLASSIC_SURF, (int)THEME_CLASSIC_SURF);
        CHECK_EQ((int)LEDTheme::VIBRANT_MIX, (int)THEME_VIBRANT_MIX);
        CHECK_EQ((int)LEDTheme::TROPICAL_PARADISE, (int)THEME_TROPICAL_PARADISE);
        CHECK_EQ((int)LEDTheme::OCEAN_SUNSET, (int)THEME_OCEAN_SUNSET);
        CHECK_EQ((int)LEDTheme::ELECTRIC_VIBES, (int)THEME_ELECTRIC_VIBES);
    }

    TEST(dark_theme_exists_in_firmware_but_not_on_the_wire) {
        // Pinned gap: index 5 fits in the 3-bit field but the server enum stops
        // at 4, so 'dark' can never arrive over V3. Closing it needs both sides.
        CHECK_EQ((int)THEME_DARK, 5);
        CHECK_EQ((int)THEME_COUNT, 6);
        CHECK_EQ((int)LEDTheme::ELECTRIC_VIBES, 4);
    }

    TEST(every_theme_has_three_colours) {
        for (uint8_t i = 0; i < THEME_COUNT; ++i) {
            ThemeColors c = getThemeColors(i);
            CHECK(c.wave_color.v > 0 || i == THEME_DARK);
            CHECK(c.wind_color.v > 0 || i == THEME_DARK);
            CHECK(c.period_color.v > 0 || i == THEME_DARK);
        }
        ThemeColors fallback = getThemeColors(200);
        ThemeColors classic = getThemeColors(THEME_CLASSIC_SURF);
        CHECK_EQ(fallback.wave_color.h, classic.wave_color.h);
    }

    return check::summary("test_themes");
}
