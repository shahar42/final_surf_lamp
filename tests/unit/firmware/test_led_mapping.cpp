// LEDMappingConfig from Config.h: how readings become lit LED counts.
// Compiling this file at all also runs Config.h's static_asserts.
#include <cmath>

#include "check.h"
#include "Config.h"

WaveConfig waveConfig;          // Config.h declares these extern
LEDMappingConfig ledMapping;

int main() {
    TEST(strip_geometry_macros_are_consistent) {
        CHECK(WAVE_HEIGHT_START <= WAVE_HEIGHT_END);
        CHECK(WAVE_PERIOD_START <= WAVE_PERIOD_END);
        CHECK(WIND_SPEED_START <= WIND_SPEED_END);
        CHECK_EQ(WAVE_HEIGHT_LENGTH, WAVE_HEIGHT_END - WAVE_HEIGHT_START + 1);
        CHECK_EQ(WAVE_PERIOD_LENGTH, WAVE_PERIOD_END - WAVE_PERIOD_START + 1);
        CHECK_EQ(WIND_SPEED_LENGTH, WIND_SPEED_END - WIND_SPEED_START + 1);
        CHECK(WIND_SPEED_FORWARD == false);   // static_assert says wind strip is reversed
        CHECK(STATUS_LED_INDEX != WIND_DIRECTION_INDEX);
    }

    TEST(wind_leds_clamped_between_one_and_strip_minus_two) {
        CHECK_EQ(ledMapping.calculateWindLEDs(0.0f), 1);
        CHECK_EQ(ledMapping.calculateWindLEDs(-3.0f), 1);
        CHECK_EQ(ledMapping.calculateWindLEDs((float)MAX_WIND_SPEED_MPS), WIND_SPEED_LENGTH - 2);
        CHECK_EQ(ledMapping.calculateWindLEDs((float)MAX_WIND_SPEED_MPS * 3), WIND_SPEED_LENGTH - 2);
    }

    TEST(wind_leds_monotonic_in_wind) {
        int prev = 0;
        for (float w = 0; w <= MAX_WIND_SPEED_MPS; w += 0.5f) {
            int n = ledMapping.calculateWindLEDs(w);
            CHECK(n >= prev);
            prev = n;
        }
    }

    TEST(wave_leds_from_cm_linear_and_clamped) {
        CHECK_EQ(ledMapping.calculateWaveLEDsFromCm(0), 1);
        CHECK_EQ(ledMapping.calculateWaveLEDsFromCm(MAX_WAVE_HEIGHT_METERS * 100), WAVE_HEIGHT_LENGTH);
        CHECK_EQ(ledMapping.calculateWaveLEDsFromCm(MAX_WAVE_HEIGHT_METERS * 100 * 5), WAVE_HEIGHT_LENGTH);
        // one divisor's worth of cm lights exactly one LED, two lights two
        int d = ledMapping.wave_height_divisor;
        CHECK_EQ(ledMapping.calculateWaveLEDsFromCm(d), 1);
        CHECK_EQ(ledMapping.calculateWaveLEDsFromCm(d + 1), 2);
    }

    TEST(wave_leds_from_meters_matches_cm) {
        for (float m = 0.1f; m <= MAX_WAVE_HEIGHT_METERS; m += 0.3f) {
            CHECK_EQ(ledMapping.calculateWaveLEDsFromMeters(m),
                     ledMapping.calculateWaveLEDsFromCm(static_cast<int>(m * 100)));
        }
    }

    TEST(period_leds_ceil_and_clamped) {
        CHECK_EQ(ledMapping.calculateWavePeriodLEDs(0.0f), 1);
        CHECK_EQ(ledMapping.calculateWavePeriodLEDs(2.1f), 3);
        CHECK_EQ(ledMapping.calculateWavePeriodLEDs(3.0f), 3);
        CHECK_EQ(ledMapping.calculateWavePeriodLEDs(100.0f), WAVE_PERIOD_LENGTH);
    }

    TEST(mps_to_knots_conversion) {
        CHECK_NEAR(ledMapping.windSpeedToKnots(1.0f), 1.94384, 1e-4);
        CHECK_NEAR(ledMapping.windSpeedToKnots(10.0f), 19.4384, 1e-3);
    }

    TEST(threshold_brightness_never_exceeds_max) {
        CHECK_EQ((int)ledMapping.getThresholdBrightness(), MAX_BRIGHTNESS);
    }

    TEST(wave_config_intensity_and_amplitude) {
        // getters return float; compare at float precision
        CHECK_NEAR(waveConfig.getBaseIntensity(), (WAVE_BRIGHTNESS_MIN_PERCENT + WAVE_BRIGHTNESS_MAX_PERCENT) / 200.0, 1e-6);
        CHECK_NEAR(waveConfig.getAmplitude(), (WAVE_BRIGHTNESS_MAX_PERCENT - WAVE_BRIGHTNESS_MIN_PERCENT) / 200.0, 1e-6);
        CHECK(waveConfig.getBaseIntensity() + waveConfig.getAmplitude() <= 1.0 + 1e-6);
    }

    return check::summary("test_led_mapping");
}
