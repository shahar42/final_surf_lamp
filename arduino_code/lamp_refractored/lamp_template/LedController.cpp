/*
 * LED CONTROLLER - IMPLEMENTATION
 *
 * LED display functions for surf lamp.
 */

#include "LedController.h"
#include "Themes.h"

// Global LED array (defined here, declared extern in header)
CRGB leds[TOTAL_LEDS];

// File-static animation state (hidden from external access)
static unsigned long lastBlinkUpdate = 0;
static float blinkPhase = 0.0;
static const unsigned long BLINK_INTERVAL = 1500; // 1.5 seconds for slow smooth blink

// ---------------- INITIALIZATION ----------------

void initializeLEDs() {
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, TOTAL_LEDS);
    FastLED.setBrightness(BRIGHTNESS * lastSurfData.brightnessMultiplier);
    FastLED.clear();
    FastLED.show();
    Serial.println("💡 LEDs initialized");
}

#include "animation.h"

void playStartupAnimation() {
    Serial.println("🎬 Starting 'The Rising Tide' animation...");

    // Create strip configurations from Config.h constants
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

    // Execute the animation using the shared Animation module
    // This allows the animation logic to be reused or updated in one place
    Animation::playStartupTide(leds, waveHeight, wavePeriod, windSpeed);
}

void testAllStatusLEDStates() {
    Serial.println("🧪 Testing all status LED error states...");

    // 1. RED - WiFi Error
    Serial.println("   🔴 RED - WiFi Disconnected");
    for (int i = 0; i < 3; i++) {
        blinkRedLED();
        delay(500);
    }
    delay(2000);

    // 2. BLUE - Connecting
    Serial.println("   🔵 BLUE - Connecting to WiFi");
    for (int i = 0; i < 3; i++) {
        blinkBlueLED();
        delay(500);
    }
    delay(2000);

    // 3. GREEN - Connected & Fresh Data
    Serial.println("   🟢 GREEN - Connected & Fresh Data");
    for (int i = 0; i < 3; i++) {
        blinkGreenLED();
        delay(500);
    }
    delay(2000);

    // 4. ORANGE - Stale Data / Server Issues
    Serial.println("   🟠 ORANGE - Stale Data / Server Issues");
    for (int i = 0; i < 3; i++) {
        blinkOrangeLED();
        delay(500);
    }
    delay(2000);

    // 5. YELLOW - Config Mode
    Serial.println("   🟡 YELLOW - Configuration Portal");
    for (int i = 0; i < 3; i++) {
        blinkYellowLED();
        delay(500);
    }
    delay(2000);

    // 6. Full system patterns
    Serial.println("   🟢 Full System: Trying to Connect");
    showTryingToConnect();
    delay(3000);

    Serial.println("   🟣 Full System: Checking Location");
    showCheckingLocation();
    delay(3000);

    Serial.println("   🔴🔵🟢 Full System: AP Mode");
    showAPMode();
    delay(3000);

    clearLEDs();
    Serial.println("✅ Status LED test completed");
}

// ---------------- BASIC LED CONTROL ----------------

void clearLEDs() {
    FastLED.clear();
    FastLED.show();
}

void setStatusLED(CRGB color) {
    leds[STATUS_LED_INDEX] = color;
    FastLED.show();
}

// ---------------- STATUS PATTERNS ----------------

void blinkStatusLED(CRGB color) {
    static unsigned long lastStatusUpdate = 0;
    static float statusPhase = 0.0;

    // Update status LED at slower timing (every 20ms for slower pace)
    if (millis() - lastStatusUpdate >= 20) {
        statusPhase += 0.05; // Much slower: ~1.25-second cycle
        if (statusPhase >= 2 * PI) statusPhase = 0.0;
        lastStatusUpdate = millis();
    }

    // Gentler breathing pattern
    float brightnessFactor = 0.7 + 0.3 * sin(statusPhase);
    int adjustedBrightness = min(MAX_BRIGHTNESS, (int)(MAX_BRIGHTNESS * brightnessFactor));

    // Convert RGB to HSV for brightness control
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
    static unsigned long lastUpdate = 0;
    
    // Limit refresh rate to 10Hz to avoid excessive CPU/LED updates
    if (millis() - lastUpdate >= 100) {
        fill_solid(leds, TOTAL_LEDS, CRGB::Green);
        FastLED.show();
        lastUpdate = millis();
    }
}

void showTryingToConnect() {
    static unsigned long lastUpdate = 0;
    static float phase = 0.0;

    if (millis() - lastUpdate >= 20) {
        phase += 0.03;  // Slow blink
        if (phase >= 2 * PI) phase = 0.0;
        lastUpdate = millis();
    }

    float brightnessFactor = 0.5 + 0.5 * sin(phase);
    int brightness = (int)(255 * brightnessFactor);

    fill_solid(leds, TOTAL_LEDS, CHSV(96, 255, brightness));  // Green
    FastLED.show();
}

void showCheckingLocation() {
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
    // Clear ALL LEDs first - only defined strips should be visible
    FastLED.clear();

    // Wave Height (Right): Red
    for (int i = 0; i < WAVE_HEIGHT_LENGTH; i++) {
        leds[WAVE_HEIGHT_START + i] = CRGB::Red;
    }

    // Wind Speed (Center): White
    int wind_min = min(WIND_SPEED_BOTTOM, WIND_SPEED_TOP);
    int wind_max = max(WIND_SPEED_BOTTOM, WIND_SPEED_TOP);
    for (int i = wind_min; i <= wind_max; i++) {
        leds[i] = CRGB::White;
    }

    // Wave Period (Left): Green
    for (int i = 0; i < WAVE_PERIOD_LENGTH; i++) {
        leds[WAVE_PERIOD_START + i] = CRGB::Green;
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
    Serial.printf("🐛 DEBUG: Wind direction = %d°\n", windDirection);

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
    // Skip all LED updates during quiet hours - quiet hours mode already set the display
    if (lastSurfData.quietHoursActive) return;

    if (waveHeight_cm < waveThreshold_cm) {
        // NORMAL MODE: Theme-based wave height visualization
        updateWaveHeightLEDs(waveHeightLEDs, getWaveHeightColor(lastSurfData.theme));
    } else {
        // ALERT MODE: Blinking theme-based wave height LEDs
        CHSV themeColor = getWaveHeightColor(lastSurfData.theme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
    }
}

void applyWindSpeedThreshold(int windSpeedLEDs, int windSpeed_mps, int windSpeedThreshold_knots) {
    // Skip all LED updates during quiet hours - quiet hours mode already set the display
    if (lastSurfData.quietHoursActive) return;

    // Convert wind speed from m/s to knots for threshold comparison
    float windSpeedInKnots = ledMapping.windSpeedToKnots(windSpeed_mps);

    if (windSpeedInKnots < windSpeedThreshold_knots) {
        // NORMAL MODE: Theme-based wind speed visualization
        updateWindSpeedLEDs(windSpeedLEDs, getWindSpeedColor(lastSurfData.theme));
    } else {
        // ALERT MODE: Blinking theme-based wind speed LEDs
        CHSV themeColor = getWindSpeedColor(lastSurfData.theme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
    }
}

// ---------------- HIGH-LEVEL DISPLAY UPDATES ----------------

void updateSurfDisplay() {
    // Check if we have valid surf data
    if (!lastSurfData.dataReceived) {
        Serial.println("⚠️ No surf data available to display");
        return;
    }

    // OFF HOURS: Lamp completely off (top priority)
    if (lastSurfData.offHoursActive) {
        FastLED.clear();
        FastLED.show();
        Serial.println("🔴 Off hours active - lamp turned OFF");
        return;
    }

    // Convert stored data back to the units needed for display
    int waveHeight_cm = static_cast<int>(lastSurfData.waveHeight * 100);
    float wavePeriod = lastSurfData.wavePeriod;
    int windSpeed = static_cast<int>(lastSurfData.windSpeed);
    int windDirection = lastSurfData.windDirection;
    int waveThreshold_cm = static_cast<int>(lastSurfData.waveThreshold * 100);
    int windSpeedThreshold_knots = lastSurfData.windSpeedThreshold;

    // QUIET HOURS: Only top LED of each strip (secondary priority)
    if (lastSurfData.quietHoursActive) {
        FastLED.setBrightness(BRIGHTNESS * lastSurfData.brightnessMultiplier * 0.3); // User brightness + 30% dim for quiet hours

        // Calculate how many LEDs would be on during daytime
        int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
        int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

        // Turn off all LEDs first
        FastLED.clear();

        // Set wind direction LED - always on during quiet hours
        setWindDirection(windDirection);

        // Light only the top LED using correct indices
        // Wind: top = lowest index in reverse strip
        if (windSpeedLEDs > 0) {
            int topWindIndex = WIND_SPEED_BOTTOM - windSpeedLEDs;
            leds[topWindIndex] = getWindSpeedColor(lastSurfData.theme);
        }
        // Wave height: top = highest index
        if (waveHeightLEDs > 0) {
            int topWaveIndex = WAVE_HEIGHT_START + waveHeightLEDs - 1;
            leds[topWaveIndex] = getWaveHeightColor(lastSurfData.theme);
        }
        // Wave period: top = highest index
        if (wavePeriodLEDs > 0) {
            int topPeriodIndex = WAVE_PERIOD_START + wavePeriodLEDs - 1;
            leds[topPeriodIndex] = getWavePeriodColor(lastSurfData.theme);
        }

        FastLED.show();
        Serial.println("🌙 Quiet hours: Only top LEDs active + wind direction");
        return;
    }

    // NORMAL MODE: Clear all LEDs first (including hidden LEDs between strips)
    FastLED.clear();

    // Apply user brightness setting
    FastLED.setBrightness(BRIGHTNESS * lastSurfData.brightnessMultiplier);

    // Calculate LED counts based on surf data using centralized mapping configuration
    int windSpeedLEDs = ledMapping.calculateWindLEDs(windSpeed);
    int waveHeightLEDs = ledMapping.calculateWaveLEDsFromCm(waveHeight_cm);
    int wavePeriodLEDs = ledMapping.calculateWavePeriodLEDs(wavePeriod);

    // Set wind direction indicator
    setWindDirection(windDirection);

    // Set wave period LEDs with theme color
    updateWavePeriodLEDs(wavePeriodLEDs, getWavePeriodColor(lastSurfData.theme));

    // Apply threshold logic for wind speed and wave height
    applyWindSpeedThreshold(windSpeedLEDs, windSpeed, windSpeedThreshold_knots);
    applyWaveHeightThreshold(waveHeightLEDs, waveHeight_cm, waveThreshold_cm);

    FastLED.show();

    Serial.printf("🎨 LEDs Updated - Wind: %d, Wave: %d, Period: %d, Direction: %d° [Wave Threshold: %dcm, Wind Threshold: %dkts]\n",
                  windSpeedLEDs, waveHeightLEDs, wavePeriodLEDs, windDirection, waveThreshold_cm, windSpeedThreshold_knots);
}

void updateBlinkingAnimation() {
    // Only update blinking if we have valid surf data and thresholds are exceeded
    if (!lastSurfData.dataReceived) return;

    // Skip all blinking during quiet hours (sleep time)
    if (lastSurfData.quietHoursActive) return;

    // Update timing once per call
    unsigned long currentMillis = millis();
    if (currentMillis - lastBlinkUpdate >= 5) { // 200 FPS for ultra-smooth animation
        blinkPhase += 0.0419; // 1.5-second cycle (slower threshold alerts)
        lastBlinkUpdate = currentMillis;
    }

    bool needsUpdate = false;

    // Check if wind speed threshold is exceeded
    float windSpeedInKnots = ledMapping.windSpeedToKnots(lastSurfData.windSpeed);
    if (windSpeedInKnots >= lastSurfData.windSpeedThreshold) {
        int windSpeedLEDs = ledMapping.calculateWindLEDs(lastSurfData.windSpeed);
        CHSV themeColor = getWindSpeedColor(lastSurfData.theme);
        updateBlinkingWindSpeedLEDs(windSpeedLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
        needsUpdate = true;
    }

    // Check if wave height threshold is exceeded (lastSurfData.waveHeight is in METERS)
    if (lastSurfData.waveHeight >= lastSurfData.waveThreshold) {
        int waveHeightLEDs = ledMapping.calculateWaveLEDsFromMeters(lastSurfData.waveHeight);
        CHSV themeColor = getWaveHeightColor(lastSurfData.theme);
        updateBlinkingWaveHeightLEDs(waveHeightLEDs, CHSV(themeColor.hue, themeColor.sat, ledMapping.getThresholdBrightness()));
        needsUpdate = true;
    }

    // Only call FastLED.show() if we updated blinking LEDs
    if (needsUpdate) {
        FastLED.show();
    }
}