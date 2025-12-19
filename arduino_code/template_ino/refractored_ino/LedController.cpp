#include "LedController.h"

// Instantiate mapping helpers
static LEDMappingConfig ledMapping;
static WaveConfig waveConfig;

LedController::LedController() {
    // Constructor
}

void LedController::setup() {
    // Initialize single LED strip
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
    FastLED.clear();
    FastLED.show();
}

// ---------------------------- Theme Functions ----------------------------

LedController::ThemeColors LedController::getThemeColors(String theme) {
    // 5 LED themes with completely distinct colors (minimal red)
    if (theme == "classic_surf") {
        return {CHSV(160, 255, 200), CHSV(0, 50, 255), CHSV(60, 255, 200)}; // Blue waves, white wind, yellow period
    } else if (theme == "vibrant_mix") {
        return {CHSV(240, 255, 200), CHSV(85, 255, 200), CHSV(160, 255, 200)}; // Purple waves, green wind, blue period
    } else if (theme == "tropical_paradise") {
        return {CHSV(85, 255, 200), CHSV(140, 255, 200), CHSV(200, 255, 200)}; // Green waves, cyan wind, magenta period
    } else if (theme == "ocean_sunset") {
        return {CHSV(160, 255, 220), CHSV(20, 255, 220), CHSV(212, 255, 220)}; // Blue waves, orange wind, pink period
    } else if (theme == "electric_vibes") {
        return {CHSV(140, 255, 240), CHSV(60, 255, 240), CHSV(240, 255, 240)}; // Cyan waves, yellow wind, purple period
    } else if (theme == "dark") {
        return {CHSV(135, 255, 255), CHSV(24, 250, 240), CHSV(85, 155, 205)};
    } else {
        return {CHSV(160, 255, 200), CHSV(0, 50, 255), CHSV(60, 255, 200)};
    }
}

CHSV LedController::getWindSpeedColor(String theme) {
    return getThemeColors(theme).wind_color;
}

CHSV LedController::getWaveHeightColor(String theme) {
    return getThemeColors(theme).wave_color;
}

CHSV LedController::getWavePeriodColor(String theme) {
    return getThemeColors(theme).period_color;
}

// ---------------------------- LED Control Functions ----------------------------

void LedController::updateWaveHeightLEDs(int numActiveLeds, CHSV color) {
    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        int index = WAVE_HEIGHT_START + i;
        if (i < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void LedController::updateBlinkingWaveHeightLEDs(int numActiveLeds, CHSV baseColor, const WaveConfig& config) {
    const float minBrightness = config.brightness_min_percent / 100.0;
    const float maxBrightness = config.brightness_max_percent / 100.0;

    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        int index = WAVE_HEIGHT_START + i;

        if (i < numActiveLeds) {
            float wavePhase = blinkPhase * config.wave_speed - (i * 2.0 * PI / config.wave_length_side);
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

            leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void LedController::updateWavePeriodLEDs(int numActiveLeds, CHSV color) {
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        int index = WAVE_PERIOD_START + i;
        if (i < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void LedController::updateWindSpeedLEDs(int numActiveLeds, CHSV color) {
    // Determine direction: +1 if filling up, -1 if filling down (reversed strip)
    int direction = WIND_SPEED_FORWARD ? 1 : -1;

    // Wind strip: Bottom is Status, Top is Direction.
    // We fill the LEDs IN BETWEEN.
    // Loop i = 1 to Length-2.
    // i represents the "step" away from the Bottom.
    
    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        // Calculate physical index based on direction
        int index = WIND_SPEED_BOTTOM + (i * direction);
        
        // Logical position (0-based index for the bar graph itself)
        int ledPosition = i - 1; 

        if (ledPosition < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void LedController::updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor, const WaveConfig& config) {
    const float minBrightness = config.brightness_min_percent / 100.0;
    const float maxBrightness = config.brightness_max_percent / 100.0;
    
    int direction = WIND_SPEED_FORWARD ? 1 : -1;

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_BOTTOM + (i * direction);
        int ledPosition = i - 1;

        if (ledPosition < numActiveLeds) {
            float wavePhase = blinkPhase * config.wave_speed - (ledPosition * 2.0 * PI / config.wave_length_center);
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

            leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void LedController::setWindDirection(int windDirection) {
    if ((windDirection >= 0 && windDirection <= 10) || (windDirection >= 300 && windDirection <= 360)) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Green;   // North
    } else if (windDirection > 10 && windDirection <= 180) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Yellow;  // East
    } else if (windDirection > 180 && windDirection <= 250) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Red;     // South
    } else if (windDirection > 250 && windDirection < 300) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Blue;    // West
    }
}

// ---------------------------- Main Display Logic ----------------------------

void LedController::applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots, const SurfData& data) {
    if (data.quietHoursActive) return;

    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed_mps);

    if (windSpeedInKnots < windSpeedThreshold_knots) {
        updateWindSpeedLEDs(windSpeedLEDs, getWindSpeedColor(data.currentTheme));
    } else {
        CHSV themeColor = getWindSpeedColor(data.currentTheme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()), waveConfig);
    }
}

void LedController::applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm, const SurfData& data) {
    if (data.quietHoursActive) return;

    if (waveHeight_cm < waveThreshold_cm) {
        updateWaveHeightLEDs(waveHeightLEDs, getWaveHeightColor(data.currentTheme));
    } else {
        CHSV themeColor = getWaveHeightColor(data.currentTheme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()), waveConfig);
    }
}

void LedController::updateSurfDisplay(const SurfData& data) {
    if (!data.dataReceived) {
        return;
    }

    if (data.offHoursActive) {
        FastLED.clear();
        FastLED.show();
        return;
    }

    int waveHeight_cm = static_cast<int>(data.waveHeight * 100);
    float wavePeriod = data.wavePeriod;
    int windSpeed = static_cast<int>(data.windSpeed);
    int windDirection = data.windDirection;
    int waveThreshold_cm = static_cast<int>(data.waveThreshold * 100);
    int windSpeedThreshold_knots = data.windSpeedThreshold;

    if (data.quietHoursActive) {
        FastLED.setBrightness(BRIGHTNESS * 0.3);

        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

        FastLED.clear();
        setWindDirection(windDirection);

        if (windSpeedLEDs > 0) {
            int topWindIndex = WIND_SPEED_START - windSpeedLEDs;
            leds[topWindIndex] = getWindSpeedColor(data.currentTheme);
        }
        if (waveHeightLEDs > 0) {
            int topWaveIndex = WAVE_HEIGHT_START + waveHeightLEDs - 1;
            leds[topWaveIndex] = getWaveHeightColor(data.currentTheme);
        }
        if (wavePeriodLEDs > 0) {
            int topPeriodIndex = WAVE_PERIOD_START + wavePeriodLEDs - 1;
            leds[topPeriodIndex] = getWavePeriodColor(data.currentTheme);
        }
        FastLED.show();
        return;
    }

    FastLED.clear();

    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

    setWindDirection(windDirection);
    updateWavePeriodLEDs(wavePeriodLEDs, getWavePeriodColor(data.currentTheme));
    applyWindSpeedThreshold(windSpeedLEDs, windSpeed, windSpeedThreshold_knots, data);
    applyWaveHeightThreshold(waveHeightLEDs, waveHeight_cm, waveThreshold_cm, data);

    FastLED.show();
}

void LedController::updateBlinkingAnimation(const SurfData& data) {
    if (!data.dataReceived || data.quietHoursActive) return;

    unsigned long currentMillis = millis();
    if (currentMillis - lastBlinkUpdate >= 5) {
        blinkPhase += 0.0419;
        lastBlinkUpdate = currentMillis;
    }

    bool needsUpdate = false;

    float windSpeedInKnots = ledMapping.windSpeedToKnots(data.windSpeed);
    if (windSpeedInKnots >= data.windSpeedThreshold) {
        int windSpeedLEDs = ledMapping.calculateWindLEDs(data.windSpeed);
        CHSV themeColor = getWindSpeedColor(data.currentTheme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()), waveConfig);
        needsUpdate = true;
    }

    if (data.waveHeight >= data.waveThreshold) {
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(data.waveHeight);
        CHSV themeColor = getWaveHeightColor(data.currentTheme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()), waveConfig);
        needsUpdate = true;
    }

    if (needsUpdate) {
        FastLED.show();
    }
}

// ---------------------------- Status & Visuals ----------------------------

void LedController::blinkStatusLED(CRGB color) {
    static unsigned long lastStatusUpdate = 0;
    static float statusPhase = 0.0;

    if (millis() - lastStatusUpdate >= 20) {
        statusPhase += 0.05;
        if (statusPhase >= 2 * PI) statusPhase = 0.0;
        lastStatusUpdate = millis();
    }

    float brightnessFactor = 0.7 + 0.3 * sin(statusPhase);
    int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(MAX_BRIGHTNESS * brightnessFactor));

    CHSV hsvColor = rgb2hsv_approximate(color);
    hsvColor.val = adjustedBrightness;

    leds[STATUS_LED_INDEX] = hsvColor;
    FastLED.show();
}

void LedController::blinkBlueLED()   { blinkStatusLED(CRGB::Blue); }
void LedController::blinkGreenLED()  { blinkStatusLED(CRGB::Green); }
void LedController::blinkRedLED()    { blinkStatusLED(CRGB::Red); }
void LedController::blinkYellowLED() { blinkStatusLED(CRGB::Yellow); }
void LedController::blinkOrangeLED() { blinkStatusLED(CRGB::Orange); }

void LedController::clearLEDs() {
    FastLED.clear();
    FastLED.show();
}

void LedController::setStatusLED(CRGB color) {
    leds[STATUS_LED_INDEX] = color;
    FastLED.show();
}

void LedController::showTryingToConnect() {
    static unsigned long lastUpdate = 0;
    static float phase = 0.0;

    if (millis() - lastUpdate >= 20) {
        phase += 0.03;
        if (phase >= 2 * PI) phase = 0.0;
        lastUpdate = millis();
    }

    float brightnessFactor = 0.5 + 0.5 * sin(phase);
    int brightness = (int)(255 * brightnessFactor);

    fill_solid(leds, TOTAL_LEDS, CHSV(96, 255, brightness));  // Green
    FastLED.show();
}

void LedController::showCheckingLocation() {
    static unsigned long lastUpdate = 0;
    static float phase = 0.0;

    if (millis() - lastUpdate >= 20) {
        phase += 0.03;
        if (phase >= 2 * PI) phase = 0.0;
        lastUpdate = millis();
    }

    float brightnessFactor = 0.5 + 0.5 * sin(phase);
    int brightness = (int)(255 * brightnessFactor);

    fill_solid(leds, TOTAL_LEDS, CHSV(192, 255, brightness));  // Purple
    FastLED.show();
}

void LedController::showAPMode() {
    FastLED.clear();
    // Wave Height (Right): Red
    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) leds[WAVE_HEIGHT_START + i] = CRGB::Red;
    // Wind Speed (Center): White
    int wind_min = min(WIND_SPEED_BOTTOM, WIND_SPEED_TOP);
    int wind_max = max(WIND_SPEED_BOTTOM, WIND_SPEED_TOP);
    for (int i = wind_min; i <= wind_max; i++) leds[i] = CRGB::White;
    // Wave Period (Left): Green
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) leds[WAVE_PERIOD_START + i] = CRGB::Green;
    FastLED.show();
}

void LedController::performLEDTest() {
    updateWaveHeightLEDs(WAVE_HEIGHT_LENGTH, CHSV(160, 255, 255));
    FastLED.show();
    delay(1000);

    updateWavePeriodLEDs(WAVE_PERIOD_LENGTH, CHSV(60, 255, 255));
    FastLED.show();
    delay(1000);

    updateWindSpeedLEDs(WIND_SPEED_LENGTH - 2, CHSV(0, 50, 255));
    FastLED.show();
    delay(1000);

    leds[STATUS_LED_INDEX] = CRGB::Green;
    FastLED.show();
    delay(1000);

    leds[WIND_DIRECTION_INDEX] = CRGB::Red;
    FastLED.show();
    delay(1000);

    for (int hue = 0; hue < 256; hue += 5) {
        fill_solid(leds, TOTAL_LEDS, CHSV(hue, 255, 80));
        FastLED.show();
        delay(20);
    }
}

void LedController::testAllStatusLEDStates() {
    for (int i = 0; i < 3; i++) { blinkRedLED(); delay(500); }
    delay(2000);
    for (int i = 0; i < 3; i++) { blinkBlueLED(); delay(500); }
    delay(2000);
    for (int i = 0; i < 3; i++) { blinkGreenLED(); delay(500); }
    delay(2000);
    for (int i = 0; i < 3; i++) { blinkOrangeLED(); delay(500); }
    delay(2000);
    for (int i = 0; i < 3; i++) { blinkYellowLED(); delay(500); }
    delay(2000);

    showTryingToConnect();
    delay(3000);
    showCheckingLocation();
    delay(3000);
    showAPMode();
    delay(3000);
    clearLEDs();
}
