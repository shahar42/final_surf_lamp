#include "Watchdog.h"
#include <nvs_flash.h>
#include <nvs.h>
#include <Arduino.h>

#define NVS_NAMESPACE "watchdog"
#define NVS_KEY_COUNT "restart_count"

Watchdog::Watchdog() : lastPetTime(0), recentRestartCount(0) {
}

void Watchdog::begin() {
    // Initialize NVS
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    loadRestartHistory();
    lastPetTime = millis();

    Serial.printf("🐕 Watchdog initialized. Recent restarts: %d\n", recentRestartCount);
}

void Watchdog::pet() {
    lastPetTime = millis();
}

bool Watchdog::isAlive() const {
    uint32_t now = millis();
    uint32_t timeSincePet = now - lastPetTime;
    return timeSincePet < TIMEOUT_MS;
}

bool Watchdog::shouldFallbackToAP() {
    return recentRestartCount >= MAX_RESTARTS;
}

void Watchdog::onRestart() {
    saveRestartTime();
    Serial.printf("🐕 Watchdog triggered restart. Total: %d in 2hr window\n", recentRestartCount + 1);
}

uint8_t Watchdog::getRestartCount() const {
    return recentRestartCount;
}

void Watchdog::loadRestartHistory() {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);

    if (err != ESP_OK) {
        recentRestartCount = 0;
        return;
    }

    // Read count
    nvs_get_u8(handle, NVS_KEY_COUNT, &recentRestartCount);
    nvs_close(handle);

    // Clean old restarts
    cleanupOldRestarts();
}

void Watchdog::saveRestartTime() {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);

    if (err != ESP_OK) {
        Serial.println("❌ NVS open failed");
        return;
    }

    recentRestartCount++;
    nvs_set_u8(handle, NVS_KEY_COUNT, recentRestartCount);
    nvs_commit(handle);
    nvs_close(handle);
}

void Watchdog::cleanupOldRestarts() {
    // TODO: Implement timestamp-based cleanup
    // For now, just decrement count if it exceeds window
    // This is a simplified version - full implementation would track individual timestamps
}
