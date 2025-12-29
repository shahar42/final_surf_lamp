/*
 * WIFI HANDLER
 *
 * WiFi connection management, diagnostics, and health monitoring.
 * Handles initial connection, reconnection, and error reporting.
 *
 * Design principles:
 * - Single entry point: setupWiFi()
 * - Pure functions for diagnostics (testable)
 * - State exposure limited to what's needed for display
 * - Event handlers encapsulated
 *
 * Dependencies:
 * - Config.h: BUTTON_PIN, WIFI_TIMEOUT
 * - LedController.h: Status LED patterns
 * - WiFiFingerprinting.h: Location change detection
 */

#ifndef WIFI_HANDLER_H
#define WIFI_HANDLER_H

#include <WiFi.h>
#include <WiFiManager.h>
#include "Config.h"
#include "WiFiFingerprinting.h"

// ---------------- WIFI CONNECTION ----------------

/**
 * Setup WiFi connection
 * Handles initial connection with scenario-based timeout strategy:
 * - FIRST_SETUP: 10 minutes for new device configuration
 * - ROUTER_REBOOT: Exponential backoff (30s, 60s, 120s, 240s, 300s max)
 * - HAS_CREDENTIALS: Standard retries with portal
 * - NEW_LOCATION: Forces reconfiguration
 *
 * @param wifiManager Reference to WiFiManager instance
 * @param fingerprinting Reference to WiFiFingerprinting instance
 * @return true if connected, false if failed (caller should restart)
 */
bool setupWiFi(WiFiManager& wifiManager, WiFiFingerprinting& fingerprinting);

/**
 * Handle WiFi health monitoring in loop()
 * Manages reconnection attempts and restarts if needed
 * Call this every loop iteration
 */
void handleWiFiHealth();

/**
 * Handle WiFi reset button
 * Call this every loop iteration to check for button press
 * @param wifiManager Reference to WiFiManager for reset
 */
void handleWiFiResetButton(WiFiManager& wifiManager);

// ---------------- DIAGNOSTICS ----------------

/**
 * Diagnose SSID availability and connection issues
 * Scans for network, checks signal strength, validates security mode
 * @param targetSSID SSID to diagnose
 * @return Error message if issues found, empty string if OK
 */
String diagnoseSSID(const char* targetSSID);

/**
 * Convert WiFi disconnect reason code to human-readable message
 * Based on ESP-IDF wifi_err_reason_t enum
 * @param reason Disconnect reason code
 * @return Human-readable error message
 */
String getDisconnectReasonText(uint8_t reason);

// ---------------- EVENT HANDLERS ----------------

/**
 * WiFi event handler - captures connection and disconnection events
 * Called automatically by ESP32 WiFi stack
 */
void WiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info);

/**
 * WiFiManager callback - AP mode started
 * Called when configuration portal opens
 */
void configModeCallback(WiFiManager* myWiFiManager);

/**
 * WiFiManager callback - Configuration saved
 * Called when user submits credentials
 */
void saveConfigCallback();

/**
 * WiFiManager callback - Parameters saved
 * Called BEFORE connection attempt for diagnostics
 */
void saveParamsCallback();

// ---------------- STATE TRACKING ----------------
// Exposed for display and diagnostics

extern String lastWiFiError;
extern uint8_t lastDisconnectReason;
extern int reconnectAttempts;
extern unsigned long lastReconnectAttempt;
extern WiFiManager* globalWiFiManager; // For error injection from event handler
extern bool wifiJustReconnected; // Flag to trigger immediate data fetch after reconnection

// Constants
extern const int MAX_WIFI_RETRIES;

#endif // WIFI_HANDLER_H
