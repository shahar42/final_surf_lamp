/**
 * SURF LAMP - MODULAR ARCHITECTURE VERSION
 *
 * Professional ESP32 architecture using:
 * - Event-driven communication (EventBus)
 * - Cooperative multitasking (TaskScheduler)
 * - State machine (WiFi management)
 * - Dependency injection (testable components)
 * - Separation of concerns (modular design)
 *
 * Hardware: Single continuous WS2812B LED strip (47 LEDs)
 *
 * LED MAPPING:
 * - Strip 1 (Wave Height - Right): LEDs 1-14 (bottom-up)
 * - Strip 2 (Wave Period - Left):  LEDs 33-46 (bottom-up)
 * - Strip 3 (Wind Speed - Center):  LEDs 30-17 (REVERSE - bottom to top)
 * - LED 30: Status indicator
 * - LED 17: Wind direction indicator
 */

#include <FastLED.h>

// Core infrastructure
#include "core/EventBus.h"
#include "core/TaskScheduler.h"
#include "core/StateMachine.h"

// Configuration
#include "config/SystemConfig.h"

// Data layer
#include "data/SurfDataModel.h"
#include "data/DataProcessor.h"

// Display layer
#include "display/ThemeManager.h"
#include "display/LEDController.h"
#include "display/AnimationEngine.h"
#include "display/DisplayManager.h"

// Network layer
#include "network/ServerDiscovery.h"
#include "network/DataFetcher.h"
#include "network/WiFiManager.h"
#include "network/HTTPServer.h"

// ========================== Global Instances ==========================

// LED array (hardware)
CRGB leds[SystemConfig::TOTAL_LEDS];

// Core infrastructure
EventBus eventBus;
TaskScheduler scheduler;
StateMachine stateMachine(eventBus);

// Configuration
LEDMappingConfig ledMapping;
WaveConfig waveConfig;

// Data layer
SurfData surfData;
DataProcessor dataProcessor(eventBus, surfData);

// Display layer
ThemeManager themeManager;
LEDController ledController(leds, ledMapping);
AnimationEngine animationEngine(ledController, themeManager, waveConfig, surfData);
DisplayManager displayManager(ledController, animationEngine, themeManager, surfData, eventBus);

// Network layer
ServerDiscovery serverDiscovery;
DataFetcher dataFetcher(eventBus, serverDiscovery, SystemConfig::ARDUINO_ID);
WiFiManager wifiManager(eventBus);
HTTPServer httpServer(eventBus, SystemConfig::ARDUINO_ID);

// ========================== Task Callbacks ==========================

/**
 * Periodic surf data fetch task
 */
void fetchDataTask() {
    Serial.println("⏰ Scheduled data fetch triggered");
    dataFetcher.fetchSurfData();
}

/**
 * Animation update task (200 FPS for smooth waves)
 */
void animationTask() {
    animationEngine.update();
}

/**
 * Status LED breathing effect task
 */
void statusLEDTask() {
    // Determine status color based on system state
    CRGB color;

    if (!wifiManager.isConnected()) {
        color = wifiManager.isConfigMode() ? CRGB::Yellow : CRGB::Red;
    } else if (surfData.isValid() && surfData.isFresh(30 * 60 * 1000)) {
        color = CRGB::Green;  // Fresh data (< 30 minutes)
    } else {
        color = CRGB::Blue;   // No recent data
    }

    ledController.breatheStatusLED(color);
}

/**
 * WiFi reconnection check task
 */
void wifiReconnectTask() {
    if (!wifiManager.isConnected() && !wifiManager.isConfigMode()) {
        Serial.println("🔄 WiFi disconnected, attempting reconnect...");
        wifiManager.reconnect();
    }
}

/**
 * Configuration mode timeout check
 */
void configTimeoutTask() {
    if (wifiManager.handleConfigTimeout()) {
        Serial.println("⏰ Config timeout - attempting WiFi connection");
        wifiManager.connect();
    }
}

// ========================== Event Handlers ==========================

/**
 * Handle WiFi connected event
 */
void onWiFiConnected(void* data) {
    Serial.println("✅ Event: WiFi connected");
    stateMachine.handleEvent(FSM_EVENT_WIFI_CONNECT_SUCCESS);

    // Setup HTTP server
    httpServer.begin();

    // Enable data fetching task
    scheduler.enableTask("DataFetcher");

    // Try immediate data fetch
    dataFetcher.fetchSurfData();
}

/**
 * Handle WiFi disconnected event
 */
void onWiFiDisconnected(void* data) {
    Serial.println("❌ Event: WiFi disconnected");
    stateMachine.handleEvent(FSM_EVENT_WIFI_CONNECT_FAILED);

    // Disable data fetching until reconnected
    scheduler.disableTask("DataFetcher");
}

/**
 * Handle configuration mode started
 */
void onConfigModeStarted(void* data) {
    Serial.println("🔧 Event: Config mode started");
    stateMachine.handleEvent(FSM_EVENT_WIFI_CONNECT_FAILED);

    // Setup config mode HTTP server
    httpServer.beginConfigMode();
}

/**
 * Handle WiFi connection request (from config page)
 */
void onWiFiConnectRequest(void* data) {
    Serial.println("🔄 Event: WiFi connect request");

    // Give the HTTP response time to send
    delay(2000);

    wifiManager.exitConfigMode();
    wifiManager.connect();
}

/**
 * Handle display update needed event
 */
void onDisplayUpdateNeeded(void* data) {
    Serial.println("🎨 Event: Display update needed");
    displayManager.updateDisplay();
}

/**
 * Handle LED test request
 */
void onLEDTestRequested(void* data) {
    Serial.println("🧪 Event: LED test requested");
    ledController.performLEDTest();
}

// ========================== State Machine Callbacks ==========================

void onEnterInit() {
    Serial.println("🔄 State: INIT");
    FastLED.clear();
    FastLED.show();
}

void onEnterWiFiConnecting() {
    Serial.println("🔄 State: WIFI_CONNECTING");
    // Status LED breathing is handled by task
}

void onEnterConfigMode() {
    Serial.println("🔧 State: WIFI_CONFIG_AP");
    wifiManager.startConfigMode();
}

void onEnterOperational() {
    Serial.println("✅ State: OPERATIONAL");
    Serial.printf("📍 Device accessible at: http://%s\n", wifiManager.getIPAddress().c_str());
}

void onEnterReconnecting() {
    Serial.println("🔄 State: WIFI_RECONNECTING");
}

void onEnterError() {
    Serial.println("❌ State: ERROR");
}

// ========================== Setup ==========================

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n🌊 ========================================");
    Serial.println("🌊 SURF LAMP - MODULAR ARCHITECTURE");
    Serial.println("🌊 ========================================");
    Serial.printf("🔧 Arduino ID: %d\n", SystemConfig::ARDUINO_ID);
    Serial.printf("📦 Firmware: %s\n", SystemConfig::FIRMWARE_VERSION);
    Serial.println();

    // ==================== Hardware Initialization ====================

    Serial.println("💡 Initializing LED hardware...");
    FastLED.addLeds<SystemConfig::LED_TYPE, SystemConfig::LED_PIN, SystemConfig::COLOR_ORDER>(
        leds, SystemConfig::TOTAL_LEDS
    );
    FastLED.setBrightness(SystemConfig::LED_BRIGHTNESS);
    FastLED.clear();
    FastLED.show();

    pinMode(SystemConfig::BUTTON_PIN, INPUT_PULLUP);

    Serial.println("✅ Hardware initialized");

    // ==================== Component Initialization ====================

    Serial.println("🔧 Initializing components...");

    // Initialize WiFi manager
    wifiManager.begin();

    // Setup HTTP server dependencies
    httpServer.setDependencies(&wifiManager, &dataFetcher, &serverDiscovery, &surfData);

    Serial.println("✅ Components initialized");

    // ==================== Event Bus Subscriptions ====================

    Serial.println("📡 Setting up event subscriptions...");

    eventBus.subscribe(EVENT_WIFI_CONNECTED, onWiFiConnected);
    eventBus.subscribe(EVENT_WIFI_DISCONNECTED, onWiFiDisconnected);
    eventBus.subscribe(EVENT_CONFIG_MODE_STARTED, onConfigModeStarted);
    eventBus.subscribe(EVENT_WIFI_CONNECT_REQUEST, onWiFiConnectRequest);
    eventBus.subscribe(EVENT_DISPLAY_UPDATE_NEEDED, onDisplayUpdateNeeded);
    eventBus.subscribe(EVENT_LED_TEST_REQUESTED, onLEDTestRequested);

    // DataProcessor subscribes to EVENT_DATA_RECEIVED automatically in constructor

    Serial.println("✅ Event bus wired");

    // ==================== Task Scheduler Setup ====================

    Serial.println("⏰ Setting up task scheduler...");

    scheduler.addTask(fetchDataTask, SystemConfig::FETCH_INTERVAL_MS, "DataFetcher");
    scheduler.addTask(animationTask, 5, "Animation");  // 5ms = 200 FPS
    scheduler.addTask(statusLEDTask, 20, "StatusLED");
    scheduler.addTask(wifiReconnectTask, 30000, "WiFiReconnect");  // Every 30s
    scheduler.addTask(configTimeoutTask, 1000, "ConfigTimeout");   // Every 1s

    // Disable data fetching until WiFi connected
    scheduler.disableTask("DataFetcher");

    Serial.println("✅ Scheduler configured");

    // ==================== State Machine Setup ====================

    Serial.println("🎛️ Setting up state machine...");

    stateMachine.onEnter(STATE_INIT, onEnterInit);
    stateMachine.onEnter(STATE_WIFI_CONNECTING, onEnterWiFiConnecting);
    stateMachine.onEnter(STATE_WIFI_CONFIG_AP, onEnterConfigMode);
    stateMachine.onEnter(STATE_OPERATIONAL, onEnterOperational);
    stateMachine.onEnter(STATE_WIFI_RECONNECTING, onEnterReconnecting);
    stateMachine.onEnter(STATE_ERROR, onEnterError);

    Serial.println("✅ State machine configured");

    // ==================== LED Startup Test ====================

    Serial.println("🧪 Running LED test...");
    ledController.performLEDTest();
    Serial.println("✅ LED test complete");

    // ==================== WiFi Connection ====================

    Serial.println("📶 Starting WiFi connection...");
    stateMachine.transitionTo(STATE_WIFI_CONNECTING);

    if (wifiManager.connect()) {
        // onWiFiConnected event handler will transition to OPERATIONAL
    } else {
        Serial.println("❌ WiFi connection failed - starting config mode");
        wifiManager.startConfigMode();
    }

    Serial.println("🚀 Setup complete - entering main loop");
    Serial.println("========================================\n");
}

// ========================== Main Loop ==========================

void loop() {
    // Update all subsystems
    scheduler.update();         // Run scheduled tasks
    eventBus.processQueue();    // Process async events
    stateMachine.update();      // Update state machine
    httpServer.handleClient();  // Handle HTTP requests

    // Small delay to prevent excessive CPU usage
    delay(1);
}
