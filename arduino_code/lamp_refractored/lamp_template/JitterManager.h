#ifndef JITTER_MANAGER_H
#define JITTER_MANAGER_H

#include <Arduino.h>
#include "Config.h"

/*
 * JITTER MANAGER
 * 
 * Prevents "thundering herd" problem where all lamps request data simultaneously
 * (e.g., after power outage restoration).
 * 
 * Strategy: Deterministic jitter based on ARDUINO_ID
 * - Startup: Spread over 2 minutes (0-120s)
 * - Reconnect: Spread over 1 minute (0-60s)
 * - Interval: Permanent phase shift (0-120s) to prevent drift synchronization
 */

namespace JitterManager {

    // Configuration constants
    const unsigned long STARTUP_WINDOW_SEC = 120;
    const unsigned long RECONNECT_WINDOW_SEC = 60;
    const unsigned long INTERVAL_WINDOW_SEC = 120;

    // Helper to get deterministic seed from ID
    inline unsigned long getJitterSeed() {
        return (unsigned long)ARDUINO_ID;
    }

    /**
     * Get startup delay in milliseconds
     * Range: 0 to 120,000 ms
     */
    inline unsigned long getStartupJitterMs() {
        // Formula: (ID % 120) * 1000
        return (getJitterSeed() % STARTUP_WINDOW_SEC) * 1000;
    }

    /**
     * Get WiFi reconnection delay in milliseconds
     * Range: 0 to 60,000 ms
     */
    inline unsigned long getReconnectJitterMs() {
        // Formula: (ID % 60) * 1000
        return (getJitterSeed() % RECONNECT_WINDOW_SEC) * 1000;
    }

    /**
     * Get permanent interval phase shift in milliseconds
     * Range: 0 to 120,000 ms
     */
    inline unsigned long getIntervalPhaseShiftMs() {
        // Formula: (ID % 120) * 1000
        return (getJitterSeed() % INTERVAL_WINDOW_SEC) * 1000;
    }

    /**
     * Print jitter configuration to Serial for debugging
     */
    inline void printJitterInfo() {
        Serial.println("\n📊 Jitter Configuration (Thundering Herd Prevention):");
        Serial.printf("   • Device ID: %u\n", ARDUINO_ID);
        Serial.printf("   • Startup Delay: %lu sec\n", getStartupJitterMs() / 1000);
        Serial.printf("   • Reconnect Delay: %lu sec\n", getReconnectJitterMs() / 1000);
        Serial.printf("   • Interval Shift: %lu sec\n", getIntervalPhaseShiftMs() / 1000);
        Serial.println("   ----------------------------------------");
    }
}

#endif // JITTER_MANAGER_H
