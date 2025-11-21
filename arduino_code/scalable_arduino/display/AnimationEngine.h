#ifndef ANIMATION_ENGINE_H
#define ANIMATION_ENGINE_H

#include <Arduino.h>
#include "LEDController.h"
#include "ThemeManager.h"
#include "../data/SurfDataModel.h"
#include "../config/SystemConfig.h"

/**
 * Animation Engine
 * - Handles threshold-based blinking animations
 * - Coordinates between LEDController and surf data
 * - Manages animation timing
 * - Single responsibility: Animation logic
 */

class AnimationEngine {
private:
    LEDController& ledController;
    ThemeManager& themeManager;
    WaveConfig& waveConfig;
    LEDMappingConfig& ledMapping;

public:
    /**
     * Constructor
     */
    AnimationEngine(LEDController& leds, ThemeManager& themes,
                   WaveConfig& waveConf, LEDMappingConfig& mapping)
        : ledController(leds)
        , themeManager(themes)
        , waveConfig(waveConf)
        , ledMapping(mapping)
    {}

    /**
     * Update threshold animations
     * Call this in loop() to update blinking LEDs when thresholds exceeded
     * @param surfData Current surf data
     * @return true if any animation was updated
     */
    bool updateThresholdAnimations(const SurfData& surfData) {
        // Skip animations during quiet hours
        if (surfData.quietHoursActive) return false;

        // Skip if no valid data
        if (!surfData.dataReceived) return false;

        // Update animation phase
        ledController.updateAnimationPhase();

        bool needsUpdate = false;

        // Check if wind speed threshold is exceeded
        if (surfData.isWindThresholdExceeded()) {
            animateWindSpeedThreshold(surfData);
            needsUpdate = true;
        }

        // Check if wave height threshold is exceeded
        if (surfData.isWaveThresholdExceeded()) {
            animateWaveHeightThreshold(surfData);
            needsUpdate = true;
        }

        // Show updates if needed
        if (needsUpdate) {
            ledController.show();
        }

        return needsUpdate;
    }

    /**
     * Animate wind speed LEDs when threshold exceeded
     */
    void animateWindSpeedThreshold(const SurfData& surfData) {
        // Calculate number of LEDs
        int windSpeedLEDs = ledMapping.calculateWindLEDs(
            surfData.windSpeed,
            WIND_SPEED_LENGTH
        );

        // Get theme color with brightness boost
        CHSV themeColor = themeManager.getWindColor();
        CHSV animColor = CHSV(
            themeColor.hue,
            themeColor.sat,
            ledMapping.getThresholdBrightness(themeColor.val)
        );

        // Animate with wave effect
        ledController.setWindSpeedLEDsAnimated(
            windSpeedLEDs,
            animColor,
            waveConfig.wave_length_center,
            waveConfig.brightness_min_percent / 100.0,
            waveConfig.brightness_max_percent / 100.0
        );
    }

    /**
     * Animate wave height LEDs when threshold exceeded
     */
    void animateWaveHeightThreshold(const SurfData& surfData) {
        // Calculate number of LEDs
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(
            surfData.waveHeight,
            WAVE_HEIGHT_LENGTH
        );

        // Get theme color with brightness boost
        CHSV themeColor = themeManager.getWaveColor();
        CHSV animColor = CHSV(
            themeColor.hue,
            themeColor.sat,
            ledMapping.getThresholdBrightness(themeColor.val)
        );

        // Animate with wave effect
        ledController.setWaveHeightLEDsAnimated(
            waveHeightLEDs,
            animColor,
            waveConfig.wave_length_side,
            waveConfig.brightness_min_percent / 100.0,
            waveConfig.brightness_max_percent / 100.0
        );
    }

    /**
     * Stop all animations (return to static display)
     */
    void stopAnimations() {
        ledController.resetAnimationPhase();
    }
};

#endif // ANIMATION_ENGINE_H
