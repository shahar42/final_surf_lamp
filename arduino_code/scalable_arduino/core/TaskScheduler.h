#ifndef TASK_SCHEDULER_H
#define TASK_SCHEDULER_H

#include <Arduino.h>

/**
 * Cooperative Task Scheduler for ESP32
 * - Replaces manual millis() timing checks
 * - Memory-safe: Fixed array allocation
 * - Cooperative: No threading overhead
 * - Professional pattern: Used in production ESP32 projects
 */

// Task Structure
struct Task {
    void (*callback)();         // Function to execute
    unsigned long interval;     // Interval in milliseconds
    unsigned long lastRun;      // Last execution time
    bool enabled;               // Is task active?
    const char* name;          // For debugging
};

class TaskScheduler {
private:
    static const uint8_t MAX_TASKS = 15;  // Adjust based on needs
    Task tasks[MAX_TASKS];
    uint8_t taskCount;

public:
    TaskScheduler() : taskCount(0) {
        // Initialize all tasks as disabled
        for (uint8_t i = 0; i < MAX_TASKS; i++) {
            tasks[i].enabled = false;
        }
    }

    /**
     * Register a periodic task
     * @param callback Function to call
     * @param interval How often to run (milliseconds)
     * @param name Task name for debugging
     * @return Task ID (index) or -1 if failed
     */
    int8_t addTask(void (*callback)(), unsigned long interval, const char* name = "unnamed") {
        if (taskCount >= MAX_TASKS) {
            Serial.println("⚠️ TaskScheduler: Max tasks reached!");
            return -1;
        }

        // Find first available slot
        for (uint8_t i = 0; i < MAX_TASKS; i++) {
            if (!tasks[i].enabled) {
                tasks[i].callback = callback;
                tasks[i].interval = interval;
                tasks[i].lastRun = 0;  // Run immediately on first update
                tasks[i].enabled = true;
                tasks[i].name = name;
                taskCount++;

                Serial.printf("✅ TaskScheduler: Added task '%s' (slot %d, interval %lu ms)\n",
                              name, i, interval);
                return i;
            }
        }

        return -1;
    }

    /**
     * Main update function - call this in loop()
     * Executes all due tasks
     */
    void update() {
        unsigned long now = millis();

        for (uint8_t i = 0; i < MAX_TASKS; i++) {
            if (tasks[i].enabled) {
                // Check if task is due
                if (tasks[i].lastRun == 0 || (now - tasks[i].lastRun >= tasks[i].interval)) {
                    // Execute task
                    tasks[i].callback();
                    tasks[i].lastRun = now;
                }
            }
        }
    }

    /**
     * Enable a task
     * @param taskId Task index returned by addTask()
     */
    bool enableTask(int8_t taskId) {
        if (taskId < 0 || taskId >= MAX_TASKS) return false;

        if (!tasks[taskId].enabled) {
            tasks[taskId].enabled = true;
            tasks[taskId].lastRun = 0;  // Reset timing
            Serial.printf("▶️ TaskScheduler: Enabled task '%s'\n", tasks[taskId].name);
        }
        return true;
    }

    /**
     * Disable a task (doesn't remove it, just stops execution)
     * @param taskId Task index returned by addTask()
     */
    bool disableTask(int8_t taskId) {
        if (taskId < 0 || taskId >= MAX_TASKS) return false;

        if (tasks[taskId].enabled) {
            tasks[taskId].enabled = false;
            Serial.printf("⏸️ TaskScheduler: Disabled task '%s'\n", tasks[taskId].name);
        }
        return true;
    }

    /**
     * Change task interval
     * @param taskId Task index
     * @param newInterval New interval in milliseconds
     */
    bool setInterval(int8_t taskId, unsigned long newInterval) {
        if (taskId < 0 || taskId >= MAX_TASKS) return false;

        tasks[taskId].interval = newInterval;
        Serial.printf("⏱️ TaskScheduler: Task '%s' interval changed to %lu ms\n",
                      tasks[taskId].name, newInterval);
        return true;
    }

    /**
     * Force a task to run immediately (resets timer)
     * @param taskId Task index
     */
    bool runTaskNow(int8_t taskId) {
        if (taskId < 0 || taskId >= MAX_TASKS || !tasks[taskId].enabled) {
            return false;
        }

        Serial.printf("▶️ TaskScheduler: Force-running task '%s'\n", tasks[taskId].name);
        tasks[taskId].callback();
        tasks[taskId].lastRun = millis();
        return true;
    }

    /**
     * Remove a task completely
     * @param taskId Task index
     */
    bool removeTask(int8_t taskId) {
        if (taskId < 0 || taskId >= MAX_TASKS) return false;

        if (tasks[taskId].enabled) {
            Serial.printf("🗑️ TaskScheduler: Removed task '%s'\n", tasks[taskId].name);
            tasks[taskId].enabled = false;
            taskCount--;
        }
        return true;
    }

    /**
     * Get active task count
     */
    uint8_t getTaskCount() const {
        return taskCount;
    }

    /**
     * Print task status (for debugging)
     */
    void printStatus() const {
        Serial.println("📋 TaskScheduler Status:");
        Serial.printf("   Active tasks: %d/%d\n", taskCount, MAX_TASKS);

        unsigned long now = millis();
        for (uint8_t i = 0; i < MAX_TASKS; i++) {
            if (tasks[i].enabled) {
                unsigned long nextRun = tasks[i].interval - (now - tasks[i].lastRun);
                Serial.printf("   [%d] %s: interval=%lu ms, next in %lu ms\n",
                              i, tasks[i].name, tasks[i].interval, nextRun);
            }
        }
    }

    /**
     * Clear all tasks (for reset/testing)
     */
    void clear() {
        for (uint8_t i = 0; i < MAX_TASKS; i++) {
            tasks[i].enabled = false;
        }
        taskCount = 0;
        Serial.println("🧹 TaskScheduler: All tasks cleared");
    }

    /**
     * Check if a specific task is enabled
     * @param taskId Task index
     */
    bool isTaskEnabled(int8_t taskId) const {
        if (taskId < 0 || taskId >= MAX_TASKS) return false;
        return tasks[taskId].enabled;
    }

    /**
     * Get time until next task execution
     * @param taskId Task index
     * @return milliseconds until next run, or 0 if overdue/disabled
     */
    unsigned long getTimeUntilNext(int8_t taskId) const {
        if (taskId < 0 || taskId >= MAX_TASKS || !tasks[taskId].enabled) {
            return 0;
        }

        unsigned long now = millis();
        unsigned long elapsed = now - tasks[taskId].lastRun;

        if (elapsed >= tasks[taskId].interval) {
            return 0;  // Overdue
        }

        return tasks[taskId].interval - elapsed;
    }
};

#endif // TASK_SCHEDULER_H
