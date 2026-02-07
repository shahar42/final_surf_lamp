/*
author: shahar
date: 6/2/2026
about: watchdog for the surf lamp
*/

#ifndef WATCHDOG_H
#define WATCHDOG_H

#include <cstdint>
#include <vector>
#include "my_linear_buffer.hpp"

class Watchdog {
public:
    static const uint32_t TIMEOUT_MS = 45000;        // 45 seconds (handles slow HTTP)
    static const uint32_t WINDOW_MS = 7200000;       // 2 hours
    static const uint8_t MAX_RESTARTS = 10;

    Watchdog() : lastPetTime(0), recentRestartCount(0) 
    {
       memset(arr_restart_times, 0, sizeof(arr_restart_times));
    }

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

    // Set external logger (for async buffered logging)
    static void setLogger(AsyncSerialLogger* logger) {
        s_logger = logger;
    }

private:
    static AsyncSerialLogger* s_logger;
    uint32_t lastPetTime;
    uint8_t recentRestartCount;
    uint32_t arr_restart_times[MAX_RESTARTS];

    void loadRestartHistory();
    void saveRestartTime();
    void cleanupOldRestarts();
};

#endif // WATCHDOG_H
