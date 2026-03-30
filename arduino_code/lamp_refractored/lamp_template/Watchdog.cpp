#include "Watchdog.h"
#include <nvs_flash.h>
#include <Arduino.h>

// Static member initialization
AsyncSerialLogger* Watchdog::s_logger = nullptr;

void Watchdog::begin() {
    // NVS init required by WiFiManager for storing WiFi credentials
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    lastPetTime = millis();

    if (s_logger) {
        s_logger->Log("[Watchdog] initialized");
    } else {
        Serial.println("[Watchdog] initialized");
    }
}

void Watchdog::pet() {
    lastPetTime = millis();
}

bool Watchdog::isAlive() const {
    return (millis() - lastPetTime) < TIMEOUT_MS;
}

void Watchdog::onRestart() {
    if (s_logger) {
        s_logger->Log("[Watchdog] Core 0 unresponsive - triggering restart");
    } else {
        Serial.println("[Watchdog] Core 0 unresponsive - triggering restart");
    }
}
