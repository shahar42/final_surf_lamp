/*
 * SURF STATE DATA STRUCTURES
 *author: shahar
 *date: 6/2/2026
 * Centralized data structures for surf lamp state management.
 * Single source of truth for all runtime data.
 */

#ifndef SURF_STATE_H
#define SURF_STATE_H

#include <Arduino.h>
#include <atomic>
#include "Config.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

struct SurfData {
    // Surf conditions
    float waveHeight = 0.0;           // Wave height in meters
    float wavePeriod = 0.0;           // Wave period in seconds
    float windSpeed = 0.0;            // Wind speed in m/s (NOT knots!)
    int windDirection = 0;            // Wind direction in degrees (0-360, 0=North)

    // User preferences/thresholds
    float waveThreshold = 1.0;        // Wave threshold in meters (MUST be float for comparison!)
    int windSpeedThreshold = 15;      // Wind threshold in knots
    uint8_t themeIndex = 0;           // Theme index (0=classic_surf, see Themes.h)
    float brightnessMultiplier = BrightnessLevel::LEVEL_MID;

    // Operating modes
    bool quietHoursActive = false;    // only top leds are on
    bool offHoursActive = false;      // all leds are off

    // State tracking
    unsigned long lastUpdate = 0;     // Timestamp
    bool dataReceived = false;        

    // Error states
    bool invalidDataError = false;    
    bool serverUnreachableError = false; 
    bool jsonParseError = false;      
    bool partialDataError = false;    
    bool staleDataError = false;      // Connection lost for > 30 mins
    bool staleDataWarning = false;    // Server reports data is stale (> 60 mins same value)

    std::atomic<bool> needsDisplayUpdate{false};  // Thread-safe flag

    // Unit conversion helpers
    int waveHeightCm() const {
        return static_cast<int>(waveHeight * 100);
    }
    int waveThresholdCm() const {
        return static_cast<int>(waveThreshold * 100);
    }
    float waveHeightMeters() const {
        return waveHeight;  // Already in meters, for code clarity
    }
    float waveThresholdMeters() const {
        return waveThreshold;  // Already in meters, for code clarity
    }
};

// Global surf data instance and its mutex
extern SurfData lastSurfData;
extern SemaphoreHandle_t surfDataMutex;

// DEPRECATED: Use MutexGuard instead of manual LOCK/UNLOCK macros
// These are kept for backwards compatibility only - do not use in new code
#define LOCK_SURF_DATA() xSemaphoreTake(surfDataMutex, portMAX_DELAY)
#define UNLOCK_SURF_DATA() xSemaphoreGive(surfDataMutex)

// Global shared flags (thread-safe)
extern std::atomic<bool> wifiJustReconnected;
extern std::atomic<unsigned long> lastDataFetch;

// Global configuration (modifiable at runtime, thread-safe)
extern std::atomic<unsigned long> FETCH_INTERVAL_MS;

#endif // SURF_STATE_H
