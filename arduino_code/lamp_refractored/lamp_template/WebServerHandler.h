/*
 * WEB SERVER HANDLER
 *
 * HTTP endpoint handlers for surf lamp.
 * Provides API for receiving surf data, status monitoring, and testing.
 *
 * Design principles:
 * - Separation: HTTP handling vs data processing
 * - Dependency injection (WebServer passed by reference)
 * - Handlers match WebServer callback signature
 * - Easy to add endpoints without modifying other code
 *
 * Dependencies:
 * - Config.h: ARDUINO_ID, LED configuration
 * - SurfState.h: lastSurfData for status reporting
 * - LedController.h: LED test functions
 * - ServerDiscovery.h: API server discovery
 */

#ifndef WEB_SERVER_HANDLER_H
#define WEB_SERVER_HANDLER_H

#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include "Config.h"
#include "SurfState.h"

// ---------------- SERVER SETUP ----------------

/**
 * Setup all HTTP endpoints on the web server
 * @param server Reference to WebServer instance (dependency injection)
 */
void setupHTTPEndpoints(WebServer& server);

// ---------------- ENDPOINT HANDLERS ----------------
// These are called by WebServer callbacks

/**
 * POST /api/update - Receive surf data from background processor
 * Expects JSON body with surf conditions and user preferences
 */
void handleSurfDataUpdate();

/**
 * GET /api/status - Device status and diagnostics
 * Returns JSON with WiFi, surf data, LED calculations, and fetch timing
 */
void handleStatusRequest();

/**
 * GET /api/test - Connection test
 * Returns simple OK response to verify device is reachable
 */
void handleTestRequest();

/**
 * GET /api/led-test - LED test sequence
 * Triggers performLEDTest() - tests all strips with rainbow animation
 */
void handleLEDTestRequest();

/**
 * GET /api/status-led-test - Status LED test
 * Triggers testAllStatusLEDStates() - cycles through all error states
 */
void handleStatusLEDTestRequest();

/**
 * GET /api/info - Device information
 * Returns hardware specs: chip model, flash size, LED configuration, firmware version
 */
void handleDeviceInfoRequest();

/**
 * GET /api/fetch - Manual surf data fetch
 * Immediately fetches surf data from server (bypasses 13-minute interval)
 */
void handleManualFetchRequest();

/**
 * GET /api/wifi-diagnostics - WiFi connection diagnostics
 * Returns current WiFi status, signal strength, errors, and disconnect reasons
 */
void handleWiFiDiagnostics();

/**
 * GET /api/discovery-test - Test server discovery
 * Forces server discovery and returns current API server URL
 */
void handleDiscoveryTest();

// ---------------- DATA PROCESSING ----------------
// Separated from HTTP handling for better testability

/**
 * Process surf data from JSON string
 * @param jsonData JSON string with surf conditions
 * @return true if successful, false if parsing failed
 */
bool processSurfData(const String& jsonData);

/**
 * Fetch surf data from discovered server
 * @return true if successful, false if fetch or parse failed
 */
bool fetchSurfDataFromServer();

// ---------------- STATE TRACKING ----------------
// Exposed for loop() access

extern unsigned long lastDataFetch;
extern const unsigned long FETCH_INTERVAL;
extern const unsigned long DATA_STALENESS_THRESHOLD;

#endif // WEB_SERVER_HANDLER_H
