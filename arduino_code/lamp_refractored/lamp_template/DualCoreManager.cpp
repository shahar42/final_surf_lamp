/*
manages the 2 cores one for led display
and one for network handling handling
*/

#include "DualCoreManager.h"
#include "SurfState.h"
#include "WebServerHandler.h"
#include "WiFiHandler.h"
#include "JitterManager.h"
#include "my_linear_buffer.hpp"
#include "Watchdog.h"

// External references (global scope)
extern AsyncSerialLogger asyncLogger;
extern Watchdog watchdog;

namespace DualCore
{

// ==================== ATOMIC VARIABLES ====================

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

void handleFetchSuccess(unsigned long now) {
    asyncLogger.Log("[Core 0] Fetch successful");
    lastSuccessfulFetch.store(now);
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

            bool success = fetchSurfDataFromServer();

            if (!success) {
                // Retry 1: after 30 seconds
                asyncLogger.Log("[Core 0] Fetch failed - retry 1 in 30s");
                delay(30000);
                watchdog.pet();
                success = fetchSurfDataFromServer();
            }

            if (!success) {
                // Retry 2: after 50 more seconds (80s total from first failure)
                asyncLogger.Log("[Core 0] Retry 1 failed - retry 2 in 50s");
                delay(50000);
                watchdog.pet();
                success = fetchSurfDataFromServer();
            }

            if (success) {
                handleFetchSuccess(now);
            } else {
                asyncLogger.Log("[Core 0] All 3 fetch attempts failed - showing error");
            }

            lastFetch = now;
            lastDataFetch = now;  // Update global for compatibility
        }

        // Pet the watchdog to signal Core 0 is alive
        watchdog.pet();

        delay(1000);  // Check every second
    }
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
