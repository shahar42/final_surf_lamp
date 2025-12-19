#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <FastLED.h>
#include "Config.h"
#include "SurfState.h"

class LedController {
public:
    LedController();

    void setup();
    
    // Main Display Logic
    void updateSurfDisplay(const SurfData& data);
    void updateBlinkingAnimation(const SurfData& data);

    // Status & Error Indicators
    void blinkStatusLED(CRGB color);
    void blinkBlueLED();   // Connecting
    void blinkGreenLED();  // Connected & Fresh
    void blinkRedLED();    // Error / Disconnected
    void blinkOrangeLED(); // Stale Data
    void blinkYellowLED(); // Config Mode

    // Full Strip Patterns (for WiFi Setup)
    void showAPMode();
    void showTryingToConnect();
    void showCheckingLocation();
    void clearLEDs();

    // Diagnostics
    void performLEDTest();
    void testAllStatusLEDStates();

    // Theme Helpers
    CHSV getWindSpeedColor(String theme);
    CHSV getWaveHeightColor(String theme);
    CHSV getWavePeriodColor(String theme);

private:
    CRGB leds[TOTAL_LEDS];
    
    // Internal state for animations
    unsigned long lastBlinkUpdate = 0;
    float blinkPhase = 0.0;
    
    // Helper methods
    void updateWaveHeightLEDs(int numActiveLeds, CHSV color);
    void updateBlinkingWaveHeightLEDs(int numActiveLeds, CHSV baseColor, const WaveConfig& config);
    void updateWavePeriodLEDs(int numActiveLeds, CHSV color);
    void updateWindSpeedLEDs(int numActiveLeds, CHSV color);
    void updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor, const WaveConfig& config);
    
    void setWindDirection(int windDirection);
    void setStatusLED(CRGB color);

    // Threshold logic helpers
    void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots, const SurfData& data);
    void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm, const SurfData& data);
    
    struct ThemeColors {
        CHSV wave_color;
        CHSV wind_color;
        CHSV period_color;
    };
    ThemeColors getThemeColors(String theme);
};

#endif // LED_CONTROLLER_H
