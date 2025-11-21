#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <Arduino.h>
#include "LEDController.h"
#include "ThemeManager.h"
#include "AnimationEngine.h"
#include "../data/SurfDataModel.h"
#include "../config/SystemConfig.h"
#include "../core/EventBus.h"

/**
 * Display Manager
 * - High-level display coordination
 * - Subscribes to data events
 * - Manages display modes (normal/quiet hours)
 * - Coordinates LEDController and AnimationEngine
 */

class DisplayManager {
private:
    LEDController& ledController;
    ThemeManager& themeManager;
    AnimationEngine& animationEngine;
    LEDMappingConfig& ledMapping;
    EventBus& eventBus;

public:
    /**
     * Constructor
     */
    DisplayManager(LEDController& leds, ThemeManager& themes,
                  AnimationEngine& animations, LEDMappingConfig& mapping,
                  EventBus& events)
        : ledController(leds)
        , themeManager(themes)
        , animationEngine(animations)
        , ledMapping(mapping)
        , eventBus(events)
    {}

    /**
     * Update display with surf data
     * Main display update function
     */
    void updateDisplay(const SurfData& surfData) {
        if (!surfData.dataReceived) {
            Serial.println("⚠️ DisplayManager: No surf data available");
            return;
        }

        // Check display mode
        if (surfData.quietHoursActive) {
            updateQuietHoursDisplay(surfData);
        } else {
            updateNormalDisplay(surfData);
        }
    }

    /**
     * Quiet hours mode: Show only top LED of each strip
     */
    void updateQuietHoursDisplay(const SurfData& surfData) {
        // Set dim brightness
        ledController.setBrightness(BRIGHTNESS * QUIET_HOURS_BRIGHTNESS_MULTIPLIER);

        // Calculate LED counts
        int windSpeedLEDs = ledMapping.calculateWindLEDs(surfData.windSpeed, WIND_SPEED_LENGTH);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(surfData.waveHeight, WAVE_HEIGHT_LENGTH);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(surfData.wavePeriod, WAVE_PERIOD_LENGTH);

        // Clear all first
        ledController.clearAll();

        // Light only top LEDs
        if (windSpeedLEDs > 0) {
            int topWindIndex = WIND_SPEED_START - windSpeedLEDs;
            ledController.setLED(topWindIndex, themeManager.getWindColor());
        }

        if (waveHeightLEDs > 0) {
            int topWaveIndex = WAVE_HEIGHT_START + waveHeightLEDs - 1;
            ledController.setLED(topWaveIndex, themeManager.getWaveColor());
        }

        if (wavePeriodLEDs > 0) {
            int topPeriodIndex = WAVE_PERIOD_START + wavePeriodLEDs - 1;
            ledController.setLED(topPeriodIndex, themeManager.getPeriodColor());
        }

        ledController.show();
        Serial.println("🌙 DisplayManager: Quiet hours mode active");
    }

    /**
     * Normal display mode: Full visualization with thresholds
     */
    void updateNormalDisplay(const SurfData& surfData) {
        // Restore normal brightness
        ledController.setBrightness(BRIGHTNESS);

        // Calculate LED counts
        int windSpeedLEDs = ledMapping.calculateWindLEDs(surfData.windSpeed, WIND_SPEED_LENGTH);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(surfData.waveHeight, WAVE_HEIGHT_LENGTH);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(surfData.wavePeriod, WAVE_PERIOD_LENGTH);

        // Set wind direction indicator
        ledController.setWindDirectionLED(surfData.windDirection);

        // Set wave period LEDs (always solid)
        ledController.setWavePeriodLEDs(wavePeriodLEDs, themeManager.getPeriodColor());

        // Apply threshold logic for wind speed
        if (surfData.isWindThresholdExceeded()) {
            // Threshold exceeded - animation engine will handle this
            CHSV themeColor = themeManager.getWindColor();
            CHSV animColor = CHSV(
                themeColor.hue,
                themeColor.sat,
                ledMapping.getThresholdBrightness(themeColor.val)
            );
            // Note: AnimationEngine will update this with animation
            ledController.setWindSpeedLEDs(windSpeedLEDs, animColor);
        } else {
            // Normal mode - solid color
            ledController.setWindSpeedLEDs(windSpeedLEDs, themeManager.getWindColor());
        }

        // Apply threshold logic for wave height
        if (surfData.isWaveThresholdExceeded()) {
            // Threshold exceeded - animation engine will handle this
            CHSV themeColor = themeManager.getWaveColor();
            CHSV animColor = CHSV(
                themeColor.hue,
                themeColor.sat,
                ledMapping.getThresholdBrightness(themeColor.val)
            );
            // Note: AnimationEngine will update this with animation
            ledController.setWaveHeightLEDs(waveHeightLEDs, animColor);
        } else {
            // Normal mode - solid color
            ledController.setWaveHeightLEDs(waveHeightLEDs, themeManager.getWaveColor());
        }

        ledController.show();

        Serial.printf("🎨 DisplayManager: LEDs updated - Wind: %d, Wave: %d, Period: %d, Direction: %d°\n",
                     windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, surfData.windDirection);
    }

    /**
     * Update status LED based on system state
     */
    void updateStatusLED(SystemState state, bool dataFresh) {
        CRGB color;

        switch (state) {
            case STATE_WIFI_CONNECTING:
                color = CRGB::Blue;
                break;

            case STATE_WIFI_CONFIG_AP:
                color = CRGB::Yellow;
                break;

            case STATE_OPERATIONAL:
                color = dataFresh ? CRGB::Green : CRGB::Blue;
                break;

            case STATE_WIFI_RECONNECTING:
                color = CRGB::Red;
                break;

            case STATE_ERROR:
                color = CRGB::Red;
                break;

            default:
                color = CRGB::White;
                break;
        }

        ledController.setStatusLEDBreathing(color);
        ledController.show();
    }

    /**
     * Clear display
     */
    void clearDisplay() {
        ledController.clearAll();
        ledController.show();
        Serial.println("🧹 DisplayManager: Display cleared");
    }

    /**
     * Run LED test sequence
     */
    void runTestSequence() {
        ledController.runTestSequence();
    }

    /**
     * Handle data received event (for event bus integration)
     */
    static void onDataReceived(const Event& event) {
        // This would be implemented in the main .ino file
        // as it needs access to the global DisplayManager instance
        Serial.println("📢 DisplayManager: Data received event");
    }
};

#endif // DISPLAY_MANAGER_H
