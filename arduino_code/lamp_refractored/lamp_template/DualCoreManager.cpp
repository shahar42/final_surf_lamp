#include "DualCoreManager.h"
#include "WebServerHandler.h"
#include "SunsetCalculator.h"

// External references (global scope)
extern SunsetCalculator sunsetCalc;
extern unsigned long lastDataFetch;

namespace DualCore {

// ==================== ATOMIC VARIABLES ====================
// Defined here, declared extern in header

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

// ==================== CORE 0: NETWORK SECRETARY ====================

void networkSecretaryTask(void* parameter) {
    Serial.println("🔧 [Core 0] Network Secretary started");
    networkTaskRunning.store(true);

    // Wait for WiFi to be ready (initial setup happens in main setup())
    delay(5000);

    const unsigned long FETCH_INTERVAL = 780000; // 13 minutes
    unsigned long lastFetch = 0;

    while (true) {
        unsigned long now = millis();

        // Check if it's time to fetch (13-min interval)
        if (now - lastFetch > FETCH_INTERVAL) {
            Serial.println("🔧 [Core 0] Starting surf data fetch...");

            // Fetch data from server (BLOCKING - but only Core 0 blocks)
            if (fetchSurfDataFromServer()) {
                Serial.println("✅ [Core 0] Fetch successful");
                lastSuccessfulFetch.store(now);

                // Update atomic time variables from SunsetCalculator
                DateTime dt = sunsetCalc.getCurrentTime();
                currentYear.store(dt.year);
                currentMonth.store(dt.month);
                currentDay.store(dt.day);
                currentHour.store(dt.hour);
                currentMinute.store(dt.minute);

                // Calculate day of year
                int dayOfYear = sunsetCalc.getDayOfYear(dt.year, dt.month, dt.day);

                // Check if day changed (reset sunset played flag)
                int prevDay = lastDayOfYear.load();
                if (dayOfYear != prevDay) {
                    Serial.println("🌅 [Core 0] New day detected, resetting sunset flag");
                    sunsetPlayedToday.store(false);
                    lastDayOfYear.store(dayOfYear);
                }

                // Update sunset time (from SunsetCalculator's internal state)
                // SunsetCalculator already calculated sunset, just expose it via getter
                if (sunsetCalc.hasCoordinates()) {
                    coordinatesInitialized.store(true);
                }

            } else {
                Serial.println("❌ [Core 0] Fetch failed");
            }

            lastFetch = now;
            lastDataFetch = now; // Update global for compatibility
        }

        // Sleep to avoid burning CPU (Core 0 doesn't need high frequency)
        delay(1000); // Check every second
    }
}

// ==================== CORE 1: UTILITY FUNCTIONS ====================

bool isSunsetTimeNow() {
    // Called from Core 1 (main loop) to check if sunset animation should play

    if (!coordinatesInitialized.load()) {
        return false; // No coordinates yet
    }

    if (sunsetPlayedToday.load()) {
        return false; // Already played today
    }

    // Use SunsetCalculator's isSunsetTime() method
    // This accesses internal state which is safe because SunsetCalculator
    // is only written to by Core 0, and we're reading from Core 1
    return sunsetCalc.isSunsetTime();
}

void markSunsetPlayed() {
    // Called from Core 1 after animation completes
    sunsetPlayedToday.store(true);
    sunsetCalc.markSunsetPlayed(); // Also update SunsetCalculator's internal state
    Serial.println("🌅 [Core 1] Sunset animation completed, flag set");
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
    Serial.println("🚀 Starting dual-core architecture...");

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

    Serial.println("✅ Core 0 task created (Network Secretary)");
    Serial.println("✅ Core 1 running main loop (LED Artist)");
}

} // namespace DualCore
