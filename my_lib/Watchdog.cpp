#include "Watchdog.h"
#include <nvs_flash.h>
#include <nvs.h>
#include <Arduino.h>
#include <cstdio>

#define NVS_NAMESPACE "watchdog"
#define NVS_KEY_COUNT "restart_count"
#define NVS_KEY_TIMES "restart_times"

// Static member initialization
AsyncSerialLogger* Watchdog::s_logger = nullptr;

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

    if (s_logger) {
        char buf[64];
        snprintf(buf, sizeof(buf), "[Watchdog] initialized. Recent restarts: %d", recentRestartCount);
        s_logger->Log(buf);
    } else {
        Serial.printf("[Watchdog] initialized. Recent restarts: %d\n", recentRestartCount);
    }
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
    if (s_logger) {
        char buf[64];
        snprintf(buf, sizeof(buf), "[Watchdog] triggered restart. Total: %d in 2hr window", recentRestartCount);
        s_logger->Log(buf);
    } else {
        Serial.printf("[Watchdog] triggered restart. Total: %d in 2hr window\n", recentRestartCount);
    }
}

uint8_t Watchdog::getRestartCount() const {
    return recentRestartCount;
}

void Watchdog::loadRestartHistory() 
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);

    if (err != ESP_OK) {
        recentRestartCount = 0;
        return;
    }

    // Read count
    nvs_get_u8(handle, NVS_KEY_COUNT, &recentRestartCount);
    //load timestamps from nvs loop with unique key
    for (int i = 0; i < recentRestartCount; i++) {
        //make a unique key for each restart
        char key[20];
        sprintf(key, "%s_%d", NVS_KEY_TIMES, i);
        nvs_get_u32(handle, key, &arr_restart_times[i]);
    }
    nvs_close(handle);

    // Clean old restarts
    cleanupOldRestarts();
}

void Watchdog::saveRestartTime() 
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);

    if (err != ESP_OK) {
        if (s_logger) {
            s_logger->Log("[Watchdog] NVS open failed");
        } else {
            Serial.println("[Watchdog] NVS open failed");
        }
        return;
    }
    //add the current time to the array of the restart time
    arr_restart_times[recentRestartCount] = millis();
    //save to nvs in a loop

    for (int i = 0; i < recentRestartCount; i++) 
    {
        //use unique key each time
        char key[20];
        sprintf(key, "%s_%d", NVS_KEY_TIMES, i);
        nvs_set_u32(handle, key, arr_restart_times[i]);

    }
    recentRestartCount++;
    nvs_set_u8(handle, NVS_KEY_COUNT, recentRestartCount);
    nvs_commit(handle);
    nvs_close(handle);
}

void Watchdog::cleanupOldRestarts() 

{
    //make a variable for the current time
    uint32_t now = millis();
    //loop thourgh the array of the restart time and check if it is older than the window time
    for (int i = 0; i < recentRestartCount; i++) 
    {
        if (now - arr_restart_times[i] > WINDOW_MS && arr_restart_times[i] != 0) 
        {
            arr_restart_times[i] = 0;
            recentRestartCount--;
        }
    }       
}
