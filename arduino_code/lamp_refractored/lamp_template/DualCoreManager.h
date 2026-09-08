#ifndef DUAL_CORE_MANAGER_H
#define DUAL_CORE_MANAGER_H

#include <Arduino.h>
#include <atomic>

/*
 * DUAL-CORE ARCHITECTURE
 *
 * Core 0 (Secretary): Heavy blocking tasks
 *   - HTTP requests (13-min interval)
 *
 * Core 1 (Artist): Real-time performance
 *   - LED refresh (200 FPS)
 *   - Button handling
 *   - Status updates
 *
 * Communication: Atomic variables (lock-free, zero overhead)
 */

namespace DualCore {

// ==================== ATOMIC SHARED STATE ====================
// These variables are accessed by both cores safely

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

} // namespace DualCore

#endif
