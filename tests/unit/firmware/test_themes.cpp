// Themes.cpp name<->index table, and its agreement with the V3 wire enum.
#include <cstring>

#include "check.h"
#include "Themes.h"
#include "esp_Server_encoding.hpp"

int main() {
    const char* names[] = {"classic_surf", "vibrant_mix", "tropical_paradise", "ocean_sunset", "electric_vibes"};

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

    TEST(firmware_theme_count_equals_wire_enum_size) {
        // Every firmware theme must be reachable over V3: the table stops
        // exactly where the wire enum stops. (A 6th 'dark' theme used to sit
        // here unreachable; removed.)
        CHECK_EQ((int)THEME_COUNT, (int)LEDTheme::ELECTRIC_VIBES + 1);
        CHECK_EQ(themeNameToIndex("dark"), THEME_CLASSIC_SURF);   // gone -> fallback
    }

    TEST(every_theme_has_three_colours) {
        for (uint8_t i = 0; i < THEME_COUNT; ++i) {
            ThemeColors c = getThemeColors(i);
            CHECK(c.wave_color.v > 0);
            CHECK(c.wind_color.v > 0);
            CHECK(c.period_color.v > 0);
        }
        ThemeColors fallback = getThemeColors(200);
        ThemeColors classic = getThemeColors(THEME_CLASSIC_SURF);
        CHECK_EQ(fallback.wave_color.h, classic.wave_color.h);
    }

    return check::summary("test_themes");
}
