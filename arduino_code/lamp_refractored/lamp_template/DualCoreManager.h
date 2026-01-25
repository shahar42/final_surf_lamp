#ifndef DUAL_CORE_MANAGER_H
#define DUAL_CORE_MANAGER_H

#include <Arduino.h>
#include <atomic>

/*
 * DUAL-CORE ARCHITECTURE
 *
 * Core 0 (Secretary): Heavy blocking tasks
 *   - WiFi management
 *   - HTTP requests (13-min interval)
 *   - Date header parsing
 *   - Flash storage updates
 *
 * Core 1 (Artist): Real-time performance
 *   - LED refresh (200 FPS)
 *   - Sunset trigger checking
 *   - Button handling
 *   - Status updates
 *
 * Communication: Atomic variables (lock-free, zero overhead)
 */

namespace DualCore {

// ==================== ATOMIC SHARED STATE ====================
// These variables are accessed by both cores safely

// Sunset state (written by Core 0, read by Core 1)
extern std::atomic<int> sunsetMinutesSinceMidnight;  // Calculated sunset time
extern std::atomic<bool> sunsetPlayedToday;          // Animation already played
extern std::atomic<int> lastDayOfYear;               // Track day changes

// Time state (written by Core 0, read by Core 1)
extern std::atomic<int> currentYear;
extern std::atomic<int> currentMonth;
extern std::atomic<int> currentDay;
extern std::atomic<int> currentHour;
extern std::atomic<int> currentMinute;

// Location state (written by Core 0, read by Core 1)
extern std::atomic<bool> coordinatesInitialized;     // Has coordinates from server

// Network status (written by Core 0, read by Core 1)
extern std::atomic<bool> networkTaskRunning;         // Core 0 health indicator
extern std::atomic<unsigned long> lastSuccessfulFetch; // Timestamp of last good fetch

// ==================== TASK HANDLES ====================

extern TaskHandle_t networkTaskHandle;

// ==================== TASK FUNCTIONS ====================

// Core 0: Network Secretary Task
void networkSecretaryTask(void* parameter);

// Core 1: LED Artist (runs in main loop)
// No separate task needed - main loop() runs on Core 1 by default

// ==================== SETUP ====================

void startDualCoreTasks();

// ==================== UTILITY ====================

// Check if sunset time matches current time (called from Core 1)
bool isSunsetTimeNow();

// Mark sunset as played (called from Core 1)
void markSunsetPlayed();

// Get current time as string (for debugging)
String getCurrentTimeString();

} // namespace DualCore

#endif
