#ifndef WATCHDOG_H
#define WATCHDOG_H

#include <cstdint>
#include <vector>

class Watchdog {
public:
    static const uint32_t TIMEOUT_MS = 30000;        // 30 seconds
    static const uint32_t WINDOW_MS = 7200000;       // 2 hours
    static const uint8_t MAX_RESTARTS = 10;

    Watchdog();

    // Initialize NVS and load restart history
    void begin();

    // Core 0 calls this periodically (~every 5s)
    void pet();

    // Core 1 checks if Core 0 is alive
    bool isAlive() const;

    // Check if we should skip Phase 1 and go straight to AP
    bool shouldFallbackToAP();

    // Call before ESP.restart() when watchdog triggers
    void onRestart();

    // For debugging
    uint8_t getRestartCount() const;

private:
    uint32_t lastPetTime = 0;
    uint8_t recentRestartCount = 0;

    void loadRestartHistory();
    void saveRestartTime();
    void cleanupOldRestarts();
};

#endif // WATCHDOG_H
