/*
author: shahar
date: 6/2/2026
about: watchdog for the surf lamp
*/

#ifndef WATCHDOG_H
#define WATCHDOG_H

#include <cstdint>
#include "my_linear_buffer.hpp"

class Watchdog {
public:
    static const uint32_t TIMEOUT_MS = 140000;  // 140 seconds (handles slow HTTP + retry delays)

    Watchdog() : lastPetTime(0) {}

    // Initialize NVS (required by WiFiManager) and reset pet timer
    void begin();

    // Core 0 calls this periodically (~every 5s)
    void pet();

    // Core 1 checks if Core 0 is alive
    bool isAlive() const;

    // Call before ESP.restart() when watchdog triggers
    void onRestart();

    // Set external logger (for async buffered logging)
    static void setLogger(AsyncSerialLogger* logger) {
        s_logger = logger;
    }

private:
    static AsyncSerialLogger* s_logger;
    uint32_t lastPetTime;
};

#endif // WATCHDOG_H
