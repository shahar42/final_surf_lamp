/*
 * LED CONTROLLER - IMPLEMENTATION
 *
 * LED display functions for surf lamp.
 */

#include "LedController.h"
#include "Themes.h"
#include "animation.h"

// Global LED array (defined here, declared extern in header)
CRGB leds[TOTAL_LEDS];

static unsigned long lastBlinkUpdate = 0;
static float blinkPhase = 0.0;

// Single point of truth for LED suppression logic during off hours
static inline bool shouldSuppressAllLEDs() 
{
    LOCK_SURF_DATA();
    bool suppressed = lastSurfData.offHoursActive;
    UNLOCK_SURF_DATA();
    return suppressed;
}

// ---------------- INITIALIZATION ----------------

void initializeLEDs() 
{
    LOCK_SURF_DATA();
    float multiplier = lastSurfData.brightnessMultiplier;
    UNLOCK_SURF_DATA();

    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS * multiplier);
    FastLED.clear();
    FastLED.show();
    Serial.println("💡 LEDs initialized");
}


void playStartupAnimation() 
{
    Serial.println("Starting 'The Rising Tide' animation...");

    //strip configurations from Config.h
    Animation::StripConfig waveHeight = {
        WAVE_HEIGHT_START,
        WAVE_HEIGHT_END,
        WAVE_HEIGHT_FORWARD,
        WAVE_HEIGHT_LENGTH
    };

    Animation::StripConfig wavePeriod = {
        WAVE_PERIOD_START,
        WAVE_PERIOD_END,
        WAVE_PERIOD_FORWARD,
        WAVE_PERIOD_LENGTH
    };

    Animation::StripConfig windSpeed = {
        WIND_SPEED_START,
        WIND_SPEED_END,
        WIND_SPEED_FORWARD,
        WIND_SPEED_LENGTH
    };

    Animation::playStartupTide(leds, waveHeight, wavePeriod, windSpeed, SUNRISE_OVERLAP_SECONDS);
}

// ---------------- BASIC LED CONTROL ----------------

void clearLEDs() {
    FastLED.clear();
    FastLED.show();
}

void setStatusLED(CRGB color) {
    if (shouldSuppressAllLEDs()) return;  // Off hours
    leds[STATUS_LED_INDEX] = color;
    FastLED.show();
}

// ---------------- STATUS PATTERNS ----------------

void blinkStatusLED(CRGB color) {
    if (shouldSuppressAllLEDs()) return;  // Off hours: all LEDs off

    static unsigned long lastStatusUpdate = 0;
    static float statusPhase = 0.0;

    // Update status LED
    if (millis() - lastStatusUpdate >= 20) {
        statusPhase += 0.05; 
        if (statusPhase >= 2 * PI) statusPhase = 0.0;
        lastStatusUpdate = millis();
    }

    // Gentler breathing pattern
    float brightnessFactor = 0.7 + 0.3 * sin(statusPhase);
    int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(MAX_BRIGHTNESS * brightnessFactor));

    // Convert RGB to HSV
    CHSV hsvColor = rgb2hsv_approximate(color);
    hsvColor.val = adjustedBrightness;

    leds[STATUS_LED_INDEX] = hsvColor;
    FastLED.show();
}

void blinkBlueLED()   { blinkStatusLED(CRGB::Blue);   }
void blinkGreenLED()  { blinkStatusLED(CRGB::Green);  }
void blinkRedLED()    { blinkStatusLED(CRGB::Red);    }
void blinkYellowLED() { blinkStatusLED(CRGB::Yellow); }
void blinkOrangeLED() { blinkStatusLED(CRGB::Orange); }

void showNoDataConnected() {
    if (shouldSuppressAllLEDs()) return;  // Off hours

    static unsigned long lastUpdate = 0;

    // Limit refresh rate to 10Hz 
    if (millis() - lastUpdate >= 100) {
        FastLED.clear();

        // Wave Period (Left): Solid GREEN = Waiting for first data
        for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
            leds[WAVE_PERIOD_START + i] = CRGB::Green;
        }

        FastLED.show();
        lastUpdate = millis();
    }
}

void showTryingToConnect() 
{
    if (shouldSuppressAllLEDs()) return;  // Off hours

    static unsigned long lastUpdate = 0;
    static float phase = 0.0;

    if (millis() - lastUpdate >= 20) {
        phase += 0.03;  
        if (phase >= 2 * PI) phase = 0.0;
        lastUpdate = millis();
    }

    
    float brightnessFactor = 0.8 + 0.2 * sin(phase);
    int brightness = (int)(255 * brightnessFactor);

    fill_solid(leds, TOTAL_LEDS, CHSV(96, 255, brightness));  // Green
    FastLED.show();
}

void showCheckingLocation() 
{
    if (shouldSuppressAllLEDs()) return;  // Off hours

    static unsigned long lastUpdate = 0;
    static float phase = 0.0;

    if (millis() - lastUpdate >= 20) {
        phase += 0.03;  // Slow blink
        if (phase >= 2 * PI) phase = 0.0;
        lastUpdate = millis();
    }

    float brightnessFactor = 0.5 + 0.5 * sin(phase);
    int brightness = (int)(255 * brightnessFactor);

    fill_solid(leds, TOTAL_LEDS, CHSV(192, 255, brightness));  // Purple
    FastLED.show();
}

void showAPMode() {
    if (shouldSuppressAllLEDs()) return;  // Off hours

    FastLED.clear();

    // Wave Height (Right): Cyan
    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        leds[WAVE_HEIGHT_START + i] = CRGB::Cyan;
    }

    // Wind Speed (Center): White
    int wind_min = min(WIND_SPEED_BOTTOM, WIND_SPEED_TOP);
    int wind_max = max(WIND_SPEED_BOTTOM, WIND_SPEED_TOP);
    for (int i = wind_min; i <= wind_max; i++) {
        leds[i] = CRGB::White;
    }

    // Wave Period (Left): Cyan
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Cyan;
    }

    FastLED.show();
}

void showInvalidDataError() {
    if (shouldSuppressAllLEDs()) return;  // Off hours

    FastLED.clear();

    // Wave Period (Left): Solid RED = Invalid data
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Red;
    }

    FastLED.show();
}

void showServerUnreachableError() {
    if (shouldSuppressAllLEDs()) return;  // Off hours

    FastLED.clear();

    // Wave Period (Left): Half green, half blue = Server unreachable
    int halfPoint = WAVE_PERIOD_LENGTH / 2;
    for (int i = 0; i < halfPoint; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Green;
    }
    for (int i = halfPoint; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Blue;
    }

    FastLED.show();
}

void showStaleDataError() {
    if (shouldSuppressAllLEDs()) return;  // Off hours

    FastLED.clear();

    // Wave Period (Left): Half red, half blue = Data is stale (>30min old)
    int halfPoint = WAVE_PERIOD_LENGTH / 2;
    for (int i = 0; i < halfPoint; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Red;
    }
    for (int i = halfPoint; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Blue;
    }

    FastLED.show();
}

void showPartialDataError() {
    if (shouldSuppressAllLEDs()) return;  // Off hours: all LEDs off

    FastLED.clear();

    // Wave Period (Left): Solid PURPLE = One sensor failing (wave OR wind is zero, but not both)
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Purple;
    }

    FastLED.show();
}

void showJsonParseError() {
    if (shouldSuppressAllLEDs()) return;  // Off hours: all LEDs off

    FastLED.clear();

    // Wave Period (Left): Half green, half yellow = JSON parse error
    int halfPoint = WAVE_PERIOD_LENGTH / 2;
    for (int i = 0; i < halfPoint; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Green;
    }
    for (int i = halfPoint; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Yellow;
    }

    FastLED.show();
}

// ---------------- DATA DISPLAY FUNCTIONS ----------------

void updateWaveHeightLEDs(int numActiveLeds, CHSV color) {
    // Constrain to prevent buffer overruns
    numActiveLeds = constrain(numActiveLeds, 0, WAVE_HEIGHT_LENGTH);

    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        int index = WAVE_HEIGHT_START + i;

        if (i < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void updateWavePeriodLEDs(int numActiveLeds, CHSV color) {
    // Constrain to prevent buffer overruns
    numActiveLeds = constrain(numActiveLeds, 0, WAVE_PERIOD_LENGTH);

    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        int index = WAVE_PERIOD_START + i;

        if (i < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void updateWindSpeedLEDs(int numActiveLeds, CHSV color) {
    // Wind strip is ALWAYS REVERSE due to physical LED routing in lamp
    // Skip LED at WIND_SPEED_BOTTOM (status) and LED at WIND_SPEED_TOP (wind direction)

    // Constrain to prevent buffer overruns
    numActiveLeds = constrain(numActiveLeds, 0, WIND_SPEED_LENGTH - 2);

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_BOTTOM - i;  // Always count down (hardware constraint)
        int ledPosition = i - 1;  // Logical position (0-based)

        if (ledPosition < numActiveLeds) {
            leds[index] = color;
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void setWindDirection(int windDirection) {
    // Debug statement removed to save flash memory

    // Wind direction color coding (ALWAYS consistent for navigation)
    if ((windDirection >= 0 && windDirection <= 10) || (windDirection >= 300 && windDirection <= 360)) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Green;   // North - Green
    } else if (windDirection > 10 && windDirection <= 180) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Yellow;  // East - Yellow
    } else if (windDirection > 180 && windDirection <= 250) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Red;     // South - Red
    } else if (windDirection > 250 && windDirection < 300) {
        leds[WIND_DIRECTION_INDEX] = CRGB::Blue;    // West - Blue
    }
}

// ---------------- THRESHOLD ANIMATIONS ----------------

void updateBlinkingWaveHeightLEDs(int numActiveLeds, CHSV baseColor) {
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    // Constrain to prevent buffer overruns
    numActiveLeds = constrain(numActiveLeds, 0, WAVE_HEIGHT_LENGTH);

    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        int index = WAVE_HEIGHT_START + i;

        if (i < numActiveLeds) {
            // Calculate wave position
            float wavePhase = blinkPhase * waveConfig.wave_speed - (i * 2.0 * PI / waveConfig.wave_length_side);
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

            leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void updateBlinkingWindSpeedLEDs(int numActiveLeds, CHSV baseColor) {
    const float minBrightness = waveConfig.brightness_min_percent / 100.0;
    const float maxBrightness = waveConfig.brightness_max_percent / 100.0;

    // Wind strip is ALWAYS REVERSE due to physical LED routing in lamp
    // Skip LED at WIND_SPEED_BOTTOM (status) and LED at WIND_SPEED_TOP (wind direction)

    // Constrain to prevent buffer overruns
    numActiveLeds = constrain(numActiveLeds, 0, WIND_SPEED_LENGTH - 2);

    for (int i = 1; i < WIND_SPEED_LENGTH - 1; i++) {
        int index = WIND_SPEED_BOTTOM - i;  // Always count down (hardware constraint)
        int ledPosition = i - 1;  // Logical position

        if (ledPosition < numActiveLeds) {
            // Calculate wave position
            float wavePhase = blinkPhase * waveConfig.wave_speed - (ledPosition * 2.0 * PI / waveConfig.wave_length_center);
            float brightnessFactor = minBrightness + ((sin(wavePhase) + 1.0) / 2.0) * (maxBrightness - minBrightness);
            int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(baseColor.val * brightnessFactor));

            leds[index] = CHSV(baseColor.hue, baseColor.sat, adjustedBrightness);
        } else {
            leds[index] = CRGB::Black;
        }
    }
}

void applyWaveHeightThreshold(int waveHeightLEDs, int waveHeight_cm, int waveThreshold_cm) {

    LOCK_SURF_DATA();

    bool quietHours = lastSurfData.quietHoursActive;

    char currentTheme[32];

    strncpy(currentTheme, lastSurfData.theme, sizeof(currentTheme));

    UNLOCK_SURF_DATA();



    // Skip all LED updates during quiet hours - quiet hours mode already set the display

    if (quietHours) return;



    if (waveHeight_cm < waveThreshold_cm) {

        // NORMAL MODE: Theme-based wave height visualization

        updateWaveHeightLEDs(waveHeightLEDs, getWaveHeightColor(currentTheme));

    } else {

        // ALERT MODE: Blinking theme-based wave height LEDs

        CHSV themeColor = getWaveHeightColor(currentTheme);

        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));

    }

}



void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots) {

    LOCK_SURF_DATA();

    bool quietHours = lastSurfData.quietHoursActive;

    char currentTheme[32];

    strncpy(currentTheme, lastSurfData.theme, sizeof(currentTheme));

    UNLOCK_SURF_DATA();



    // Skip all LED updates during quiet hours - quiet hours mode already set the display

    if (quietHours) return;



    // Convert wind speed from m/s to knots for threshold comparison

    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed_mps);



    if (windSpeedInKnots < windSpeedThreshold_knots) {

        // NORMAL MODE: Theme-based wind speed visualization

        updateWindSpeedLEDs(windSpeedLEDs, getWindSpeedColor(currentTheme));

    } else {

        // ALERT MODE: Blinking theme-based wind speed LEDs

        CHSV themeColor = getWindSpeedColor(currentTheme);

        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));

    }

}



// ---------------- HIGH-LEVEL DISPLAY UPDATES ----------------



bool handleErrorStates() {

    LOCK_SURF_DATA();

    bool unreachable = lastSurfData.serverUnreachableError;

    bool parseErr = lastSurfData.jsonParseError;

    bool invalidData = lastSurfData.invalidDataError;

    bool partialErr = lastSurfData.partialDataError;

    bool staleErr = lastSurfData.staleDataError;

    UNLOCK_SURF_DATA();



    // Priority 1: Server/Communication Errors

    if (unreachable) {

        showServerUnreachableError();

        Serial.println("❌ Server unreachable - displaying GREEN/BLUE on left strip");

        return true;

    }



    if (parseErr) {

        showJsonParseError();

        Serial.println("❌ JSON parse error - displaying GREEN/YELLOW on left strip");

        return true;

    }



    // Priority 2: Data Quality Errors

    if (invalidData) {

        showInvalidDataError();

        Serial.println("❌ Invalid data (both zero) - displaying RED on left strip");

        return true;

    }



    if (partialErr) {

        showPartialDataError();

        Serial.println("❌ Partial data failure - displaying PURPLE on left strip");

        return true;

    }



    if (staleErr) {

        showStaleDataError();

        Serial.println("❌ Stale data - displaying RED/BLUE on left strip");

        return true;

    }



    return false;

}



bool handleOffHours() {

    LOCK_SURF_DATA();

    bool offHours = lastSurfData.offHoursActive;

    UNLOCK_SURF_DATA();



    if (!offHours) return false;



    FastLED.clear();

    FastLED.show();

    Serial.println("🔴 Off hours active - lamp turned OFF");

    return true;

}



bool handleQuietHours() {

    LOCK_SURF_DATA();

    if (!lastSurfData.quietHoursActive) {

        UNLOCK_SURF_DATA();

        return false;

    }



    float brightnessMult = lastSurfData.brightnessMultiplier;

    int waveHeight_cm = static_cast<int>(lastSurfData.waveHeight * 100);

    int windSpeed = static_cast<int>(lastSurfData.windSpeed);

    int windDirection = lastSurfData.windDirection;

    float wavePeriod = lastSurfData.wavePeriod;

    char currentTheme[32];

    strncpy(currentTheme, lastSurfData.theme, sizeof(currentTheme));

    UNLOCK_SURF_DATA();



    FastLED.setBrightness(BRIGHTNESS * brightnessMult);



    // Calculate LED counts

    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);

    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);

    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);



    FastLED.clear();

    setWindDirection(windDirection);



    // Light only the top LED of each strip

    if (windSpeedLEDs > 0) {

        int topWindIndex = WIND_SPEED_BOTTOM - windSpeedLEDs;

        leds[topWindIndex] = getWindSpeedColor(currentTheme);

    }

    if (waveHeightLEDs > 0) {

        int topWaveIndex = WAVE_HEIGHT_START + waveHeightLEDs - 1;

        leds[topWaveIndex] = getWaveHeightColor(currentTheme);

    }

    if (wavePeriodLEDs > 0) {

        int topPeriodIndex = WAVE_PERIOD_START + wavePeriodLEDs - 1;

        leds[topPeriodIndex] = getWavePeriodColor(currentTheme);

    }



    FastLED.show();

    Serial.println("🌙 Quiet hours: Only top LEDs active + wind direction");

    return true;

}



void handleNormalMode() {

    LOCK_SURF_DATA();

    int waveHeight_cm = static_cast<int>(lastSurfData.waveHeight * 100);

    float wavePeriod = lastSurfData.wavePeriod;

    int windSpeed = static_cast<int>(lastSurfData.windSpeed);

    int windDirection = lastSurfData.windDirection;

    int waveThreshold_cm = static_cast<int>(lastSurfData.waveThreshold * 100);

    int windSpeedThreshold_knots = lastSurfData.windSpeedThreshold;

    float brightnessMult = lastSurfData.brightnessMultiplier;

    char currentTheme[32];

    strncpy(currentTheme, lastSurfData.theme, sizeof(currentTheme));

    UNLOCK_SURF_DATA();



    FastLED.clear();

    FastLED.setBrightness(BRIGHTNESS * brightnessMult);



    // Calculate LED counts

    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);

    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);

    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);



    // Update display

    setWindDirection(windDirection);

    updateWavePeriodLEDs(wavePeriodLEDs, getWavePeriodColor(currentTheme));

    

    // Pass local variables to avoid nested locks

    // Note: applyWindSpeedThreshold and applyWaveHeightThreshold now have their own internal locks

    // This is fine as they are called AFTER we unlock above.

    applyWindSpeedThreshold(windSpeedLEDs, windSpeed, windSpeedThreshold_knots);

    applyWaveHeightThreshold(waveHeightLEDs, waveHeight_cm, waveThreshold_cm);



    FastLED.show();

    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d° [Wave Threshold: %dcm, Wind Threshold: %dkts]\n",

                  windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, windDirection, waveThreshold_cm, windSpeedThreshold_knots);

}



void updateSurfDisplay() {

    LOCK_SURF_DATA();

    bool dataReceived = lastSurfData.dataReceived;

    UNLOCK_SURF_DATA();



    // Check if we have valid surf data

    if (!dataReceived) {

        Serial.println("⚠️ No surf data available to display");

        return;

    }



    // Check states in priority order

    if (handleErrorStates()) return;

    if (handleOffHours()) return;

    if (handleQuietHours()) return;

    handleNormalMode();

}



void updateBlinkingAnimation() {

    LOCK_SURF_DATA();

    if (!lastSurfData.dataReceived || lastSurfData.offHoursActive || lastSurfData.quietHoursActive) {

        UNLOCK_SURF_DATA();

        return;

    }



    float windSpeed = lastSurfData.windSpeed;

    int windThreshold = lastSurfData.windSpeedThreshold;

    float waveHeight = lastSurfData.waveHeight;

    float waveThreshold = lastSurfData.waveThreshold;

    char currentTheme[32];

    strncpy(currentTheme, lastSurfData.theme, sizeof(currentTheme));

    UNLOCK_SURF_DATA();



    unsigned long currentMillis = millis();

    if (currentMillis - lastBlinkUpdate >= 5) { 

        blinkPhase += 0.0419; 

        lastBlinkUpdate = currentMillis;

    }



    bool needsUpdate = false;



    // Check wind speed threshold

    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed);

    if (windSpeedInKnots >= windThreshold) {

        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);

        CHSV themeColor = getWindSpeedColor(currentTheme);

        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));

        needsUpdate = true;

    }



    // Check if wave height threshold is exceeded (waveHeight is in METERS)

    if (waveHeight >= waveThreshold) {

        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(waveHeight);

        CHSV themeColor = getWaveHeightColor(currentTheme);

        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));

        needsUpdate = true;

    }



    // Only call FastLED.show() if we updated blinking LEDs

    if (needsUpdate) {

        FastLED.show();

    }

}
