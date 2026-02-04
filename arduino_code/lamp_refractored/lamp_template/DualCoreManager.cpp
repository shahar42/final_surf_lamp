/*
manages the 2 cores one for led display
and one for network handling handling
*/

#include "DualCoreManager.h"
#include "SurfState.h"
#include "WebServerHandler.h"
#include "SunsetCalculator.h"
#include "WiFiHandler.h"
#include "JitterManager.h"
#include "my_linear_buffer.hpp"

// External references (global scope)
extern SunsetCalculator sunsetCalc;
extern AsyncSerialLogger asyncLogger;

namespace DualCore 
{

// ==================== ATOMIC VARIABLES ====================

std::atomic<int> sunsetMinutesSinceMidnight(-1);
std::atomic<bool> sunsetPlayedToday(false);
std::atomic<int> lastDayOfYear(0);

std::atomic<int> currentYear(2025);
std::atomic<int> currentMonth(1);
std::atomic<int> currentDay(1);
std::atomic<int> currentHour(0);
std::atomic<int> currentMinute(0);

std::atomic<bool> coordinatesInitialized(false);
std::atomic<bool> networkTaskRunning(false);
std::atomic<unsigned long> lastSuccessfulFetch(0);

TaskHandle_t networkTaskHandle = nullptr;

// ==================== CORE 0: NETWORK SECRETARY (HELPERS) ====================

bool shouldFetchNow(unsigned long now, unsigned long lastFetch) {
    // Add permanent phase shift to prevent long-term synchronization
    // Each lamp has a unique interval: 13min + (0-120s)
    static unsigned long phaseShift = JitterManager::getIntervalPhaseShiftMs();
    unsigned long effectiveInterval = FETCH_INTERVAL_MS.load() + phaseShift;  // Atomic read

    return (now - lastFetch > effectiveInterval) || wifiJustReconnected;
}

void updateTimeVariables() {
    DateTime dt = sunsetCalc.getCurrentTime();
    currentYear.store(dt.year);
    currentMonth.store(dt.month);
    currentDay.store(dt.day);
    currentHour.store(dt.hour);
    currentMinute.store(dt.minute);
}

void checkAndResetSunsetFlag() {
    DateTime dt = sunsetCalc.getCurrentTime();
    int dayOfYear = sunsetCalc.getDayOfYear(dt.year, dt.month, dt.day);
    int prevDay = lastDayOfYear.load();

    if (dayOfYear != prevDay) {
        asyncLogger.Log("[Core 0] New day detected, resetting sunset flag");
        sunsetPlayedToday.store(false);
        lastDayOfYear.store(dayOfYear);
    }
}

void updateCoordinatesIfReady() {
    if (sunsetCalc.hasCoordinates()) {
        coordinatesInitialized.store(true);
    }
}

void handleFetchSuccess(unsigned long now) {
    asyncLogger.Log("[Core 0] Fetch successful");
    lastSuccessfulFetch.store(now);
    updateTimeVariables();
    checkAndResetSunsetFlag();
    updateCoordinatesIfReady();
}

// ==================== CORE 0: NETWORK SECRETARY ====================

void networkSecretaryTask(void* parameter)
{
    asyncLogger.Log("[Core 0] Network Secretary started");
    networkTaskRunning.store(true);

    delay(5000);  // Wait for WiFi to be ready

    unsigned long lastFetch = 0;

    while (true) {
        unsigned long now = millis();

        if (shouldFetchNow(now, lastFetch)) {
            if (wifiJustReconnected) {
                asyncLogger.Log("[Core 0] WiFi reconnected - fetching immediately");
                wifiJustReconnected = false;
            } else {
                asyncLogger.Log("[Core 0] Starting surf data fetch");
            }

            if (fetchSurfDataFromServer()) {
                handleFetchSuccess(now);
            } else {
                asyncLogger.Log("[Core 0] Fetch failed");
            }

            lastFetch = now;
            lastDataFetch = now;  // Update global for compatibility
        }

        delay(1000);  // Check every second
    }
}

// ==================== CORE 1:UTILITY FUNCTIONS ====================

bool isSunsetTimeNow() 
{

    if (!coordinatesInitialized.load()) {
        return false; 
    }

    if (sunsetPlayedToday.load()) {
        return false; 
    }

    return sunsetCalc.isSunsetTime();
}

void markSunsetPlayed() {
    sunsetPlayedToday.store(true);
    sunsetCalc.markSunsetPlayed(); 
    asyncLogger.Log("[Core 1] Sunset animation completed, flag set");
}

String getCurrentTimeString() {
    int y = currentYear.load();
    int m = currentMonth.load();
    int d = currentDay.load();
    int h = currentHour.load();
    int min = currentMinute.load();

    char buf[32];
    sprintf(buf, "%04d-%02d-%02d %02d:%02d", y, m, d, h, min);
    return String(buf);
}

// ==================== TASK STARTUP ====================

void startDualCoreTasks() {
    asyncLogger.Log("Starting dual-core architecture");

    // Create Core 0 task (Network Secretary)
    xTaskCreatePinnedToCore(
        networkSecretaryTask,   // Function
        "NetworkSecretary",     // Name
        10000,                  // Stack size (10KB)
        NULL,                   // Parameters
        1,                      // Priority (normal)
        &networkTaskHandle,     // Task handle
        0                       // Core 0
    );

    asyncLogger.Log("Core 0 task created (Network Secretary)");
    asyncLogger.Log("Core 1 running main loop (LED Artist)");
}

} // namespace DualCore
