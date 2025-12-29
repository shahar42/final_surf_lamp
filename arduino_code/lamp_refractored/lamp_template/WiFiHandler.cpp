/*
 * WIFI HANDLER - IMPLEMENTATION
 *
 * WiFi connection management and diagnostics.
 */

#include "WiFiHandler.h"
#include "LedController.h"
#include "esp_wifi.h"

// Global WiFi state (defined here, declared extern in header)
String lastWiFiError = "";
uint8_t lastDisconnectReason = 0;
int reconnectAttempts = 0;
unsigned long lastReconnectAttempt = 0;
WiFiManager* globalWiFiManager = nullptr; // For error injection from event handler
bool wifiJustReconnected = false; // Flag to trigger immediate data fetch after reconnection
static String persistentErrorHTML = ""; // Persistent storage for error message HTML
static bool allowErrorInjection = false; // Only inject after first connection attempt

const int MAX_WIFI_RETRIES = 10;  // 10 attempts × 30s = ~5 min (covers router boot times)

// ---------------- TIMEOUT CONSTANTS ----------------
namespace WiFiTimeouts {
    const int PORTAL_TIMEOUT_GENEROUS_SEC = 1020;    // 17 minutes
    const int INITIAL_CONNECTION_TIMEOUT_SEC = 20;   // First attempt
    const int MAX_CONNECTION_TIMEOUT_SEC = 60;       // Cap for exponential backoff
    const unsigned long ROUTER_REBOOT_TIMEOUT_MS = 300000;  // 5 minutes total
}

// ---------------- DELAY CONSTANTS ----------------
namespace WiFiDelays {
    const int INITIAL_RETRY_DELAY_SEC = 5;           // First retry delay
    const int MAX_RETRY_DELAY_SEC = 60;              // Cap for exponential backoff
    const int LOCATION_CHECK_DISPLAY_MS = 1000;      // Show purple LED
    const int RESTART_DELAY_MS = 3000;               // Before ESP.restart()
    const int CONNECTION_POLL_MS = 500;              // WiFi.status() polling interval
}

// ---------------- DIAGNOSTICS ----------------

String getDisconnectReasonText(uint8_t reason) {
    switch(reason) {
        case 1:  return "Unspecified error";
        case 2:  return "Wrong password or WiFi name";
        case 3:  return "Wrong password or WiFi name";
        case 4:  return "Disassociated (inactive)";
        case 5:  return "Too many devices connected to AP";
        case 6:  return "Wrong password or WiFi name";
        case 7:  return "Wrong password";
        case 8:  return "Connection timeout - check WiFi name and password";
        case 15: return "Wrong password";
        case 23: return "Wrong password (too many failed attempts)";
        case 201: return "WiFi signal lost - router may be off or out of range";
        case 202: return "WiFi network not found - check WiFi name";
        case 203: return "Wrong password";
        case 204: return "Router rejected connection - check password";
        case 205: return "Wrong password";
        default: return "Connection failed (code: " + String(reason) + ")";
    }
}

String diagnoseSSID(const char* targetSSID) {
    Serial.printf("🔍 Scanning for SSID: %s\n", targetSSID);

    int numNetworks = WiFi.scanNetworks();

    if (numNetworks == 0) {
        return "No WiFi networks found. Check if router is powered on and in range.";
    }

    Serial.printf("📡 Found %d networks\n", numNetworks);

    // Look for target SSID
    int bestSignalIndex = -1;
    int bestRSSI = -127;

    for (int i = 0; i < numNetworks; i++) {
        String ssid = WiFi.SSID(i);
        int rssi = WiFi.RSSI(i);
        wifi_auth_mode_t authMode = (wifi_auth_mode_t)WiFi.encryptionType(i);
        int channel = WiFi.channel(i);

        Serial.printf("   %d: %s (Ch %d, %d dBm, Auth %d)\n", i, ssid.c_str(), channel, rssi, authMode);

        if (ssid == targetSSID) {
            if (rssi > bestRSSI) {
                bestRSSI = rssi;
                bestSignalIndex = i;
            }
        }
    }

    if (bestSignalIndex == -1) {
        // SSID not found - most common user error
        return String("Network '") + targetSSID + "' not found. Check:\n" +
               "• Is SSID typed correctly (case-sensitive)?\n" +
               "• Is router's 2.4GHz band enabled? (ESP32 doesn't support 5GHz)\n" +
               "• Is router in range?";
    }

    // Found the network - check signal strength
    wifi_auth_mode_t authMode = (wifi_auth_mode_t)WiFi.encryptionType(bestSignalIndex);
    int channel = WiFi.channel(bestSignalIndex);

    Serial.printf("✅ Found target network:\n");
    Serial.printf("   Signal: %d dBm\n", bestRSSI);
    Serial.printf("   Channel: %d\n", channel);
    Serial.printf("   Security: %d\n", authMode);

    // Check signal strength
    if (bestRSSI < -85) {
        return String("Weak signal (") + bestRSSI + " dBm). Move lamp closer to router or use WiFi extender.";
    }

    // Check channel (ESP32 supports 1-13, some routers use 12-14 which may not work everywhere)
    if (channel > 11) {
        Serial.printf("⚠️ Warning: Channel %d may not be supported in all regions\n", channel);
    }

    // Check security mode
    if (authMode == WIFI_AUTH_WPA3_PSK) {
        return "Router uses WPA3 security. ESP32 requires WPA2. Change router to WPA2/WPA3 mixed mode.";
    }

    // All checks passed
    return "";
}

// ---------------- EVENT HANDLERS ----------------

void WiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    static uint8_t lastPrintedReason = 0;
    static unsigned long lastErrorPrint = 0;

    switch(event) {
        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("✅ WiFi connected to AP");
            lastWiFiError = "";  // Clear error on success
            persistentErrorHTML = "";  // Clear error HTML
            lastPrintedReason = 0;  // Reset error tracking
            break;

        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            Serial.printf("✅ Got IP: %s\n", WiFi.localIP().toString().c_str());
            break;

        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED: {
            lastDisconnectReason = info.wifi_sta_disconnected.reason;
            lastWiFiError = getDisconnectReasonText(lastDisconnectReason);

            // Only print if reason changed OR 10 seconds passed since last print
            unsigned long now = millis();
            if (lastDisconnectReason != lastPrintedReason || (now - lastErrorPrint > 10000)) {
                Serial.printf("❌ WiFi disconnected - Reason: %s\n", lastWiFiError.c_str());
                lastPrintedReason = lastDisconnectReason;
                lastErrorPrint = now;
            }

            // Inject error message IMMEDIATELY for portal display (only after first connect attempt)
            if (allowErrorInjection && globalWiFiManager != nullptr && lastWiFiError.length() > 0) {
                persistentErrorHTML = "<div style='background:#ff4444;color:white;padding:15px;margin:10px 0;border-radius:5px;'>";
                persistentErrorHTML += "<strong>❌ What Happened:</strong><br>";
                persistentErrorHTML += lastWiFiError;
                persistentErrorHTML += "<br/><br/><strong>✅ What To Do:</strong><br>";
                persistentErrorHTML += "Click your WiFi network below and enter the correct password.";
                persistentErrorHTML += "</div>";
                globalWiFiManager->setCustomHeadElement(persistentErrorHTML.c_str());
                Serial.println("📋 Error message injected into portal from WiFiEvent");
            }
            break;
        }

        default:
            break;
    }
}

void configModeCallback(WiFiManager *myWiFiManager) {
    Serial.println("🔧 Config mode started");
    Serial.println("📱 AP: SurfLamp-Setup");

    // AP Mode pattern: Right=Red, Center=White, Left=Green
    showAPMode();
}

void saveConfigCallback() {
    Serial.println("✅ Config saved!");
}

void saveParamsCallback() {
    Serial.println("💾 Credentials saved, performing diagnostics...");

    // Enable error injection now that user has submitted credentials
    allowErrorInjection = true;

    // Get the SSID that was just saved (WiFiManager stores it)
    String ssid = WiFi.SSID();
    if (ssid.length() == 0) {
        // WiFiManager hasn't connected yet, can't get SSID from WiFi object
        Serial.println("⏳ Will diagnose after connection attempt");
        return;
    }

    String diagnostic = diagnoseSSID(ssid.c_str());
    if (diagnostic.length() > 0) {
        lastWiFiError = diagnostic;
        Serial.printf("⚠️ Diagnostic warning: %s\n", diagnostic.c_str());
    }
}

// ---------------- WIFI CONNECTION ----------------

bool setupWiFi(WiFiManager& wifiManager, WiFiFingerprinting& fingerprinting) {
    // Store WiFiManager reference for error injection from WiFiEvent handler
    globalWiFiManager = &wifiManager;

    // Clear any previous error messages from past sessions
    lastWiFiError = "";
    persistentErrorHTML = "";
    allowErrorInjection = false; // Don't inject errors from boot-time disconnect events
    wifiManager.setCustomHeadElement("");

    // WiFiManager setup with enhanced diagnostics
    wifiManager.setAPCallback(configModeCallback);
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setSaveParamsCallback(saveParamsCallback);
    wifiManager.setConnectTimeout(10); // Fast fail: 10 seconds to attempt connection
    wifiManager.setConfigPortalTimeout(0); // No timeout - wait indefinitely

    // Load WiFi fingerprint from NVS
    fingerprinting.load();

    // Auto-connect with scenario-based timeout strategy (IoT industry best practices)
    bool connected = false;

    // CRITICAL: Detect credentials state BEFORE entering retry loop
    // Read from ESP32's NVS storage (WiFi.SSID() only works when connected)
    WiFi.mode(WIFI_STA);
    wifi_config_t wifi_cfg;
    esp_err_t err = esp_wifi_get_config(WIFI_IF_STA, &wifi_cfg);
    bool hasCredentials = (err == ESP_OK && strlen((char*)wifi_cfg.sta.ssid) > 0);

    if (hasCredentials) {
        Serial.printf("📡 Found saved credentials for SSID: %s\n", (char*)wifi_cfg.sta.ssid);
    } else {
        Serial.println("📡 No saved WiFi credentials found");
    }

    // Scenario detection for optimal timeout strategy
    enum SetupScenario { FIRST_SETUP, ROUTER_REBOOT, NEW_LOCATION, HAS_CREDENTIALS };
    SetupScenario scenario = hasCredentials ? ROUTER_REBOOT : FIRST_SETUP;

    if (scenario == FIRST_SETUP) {
        Serial.println("📋 No WiFi credentials saved - opening configuration portal");

        // CRITICAL FIX: Do NOT scan for fingerprinting before AP mode
        // WiFi scanning while AP is active causes watchdog crashes
        // Default to generous timeout for all first-time setup scenarios
        Serial.println("🆕 FIRST SETUP MODE");
        Serial.println("   Opening configuration portal for 17 minutes");
        wifiManager.setConfigPortalTimeout(WiFiTimeouts::PORTAL_TIMEOUT_GENEROUS_SEC);
    } else {
        Serial.println("🔌 WiFi credentials found - assuming router reboot scenario");
        Serial.println("   Will retry for 5 minutes with exponential backoff");
    }

    // Retry loop with scenario-based timeout strategy
    unsigned long retryStartTime = millis();
    int attempt = 0;

    while (!connected) {
        attempt++;

        // ROUTER_REBOOT: Check if 5 minutes elapsed
        if (scenario == ROUTER_REBOOT) {
            unsigned long elapsed = millis() - retryStartTime;
            if (elapsed >= WiFiTimeouts::ROUTER_REBOOT_TIMEOUT_MS) {
                Serial.println("⏱️ 5 minutes elapsed, opening AP indefinitely");
                wifiManager.setConfigPortalTimeout(0); // Indefinite
                break; // Exit retry loop, will open AP below
            }
            Serial.printf("🔄 WiFi connection attempt %d (elapsed: %lu seconds)\n", attempt, elapsed / 1000);
        } else {
            Serial.printf("🔄 WiFi connection attempt %d\n", attempt);
        }

        // Visual feedback: Trying to connect (all LEDs slow blinking green)
        showTryingToConnect();

        // Set portal timeout for scenarios that use autoConnect
        if (scenario == HAS_CREDENTIALS) {
            // HAS CREDENTIALS but connection failing - standard retry strategy
            if (attempt < MAX_WIFI_RETRIES) {
                wifiManager.setConfigPortalTimeout(WiFiTimeouts::PORTAL_TIMEOUT_GENEROUS_SEC);
            } else {
                wifiManager.setConfigPortalTimeout(0); // Final attempt: indefinite
            }
        } else if (scenario == FIRST_SETUP) {
            // FIRST_SETUP: single attempt with timeout already set
            if (attempt > 1) break; // Only one attempt for first setup
        }
        // Note: ROUTER_REBOOT doesn't use portal timeout (uses WiFi.begin instead of autoConnect)

        // Enable error injection now that we're about to attempt connection
        // But NOT for FIRST_SETUP (old credentials from NVS shouldn't show errors)
        if (scenario != FIRST_SETUP) {
            allowErrorInjection = true;
        }

        // CRITICAL: Use different connection methods based on scenario
        if (scenario == ROUTER_REBOOT) {
            // ROUTER_REBOOT: Just retry connection with saved credentials, NO AP portal
            Serial.println("   Attempting connection with saved credentials (no AP)...");
            WiFi.begin();  // Reconnect with saved credentials

            // Wait for connection with timeout (exponential backoff)
            int timeout = min(
                WiFiTimeouts::INITIAL_CONNECTION_TIMEOUT_SEC * (int)pow(2, attempt - 1),
                WiFiTimeouts::MAX_CONNECTION_TIMEOUT_SEC
            );
            unsigned long startTime = millis();
            while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < (timeout * 1000)) {
                delay(WiFiDelays::CONNECTION_POLL_MS);
            }
            connected = (WiFi.status() == WL_CONNECTED);
        } else {
            // FIRST_SETUP or other scenarios: Use autoConnect (opens AP portal)
            connected = wifiManager.autoConnect("SurfLamp-Setup", "surf123456");
        }

        // If connection failed, run diagnostics to determine WHY
        if (!connected) {
            Serial.println("❌ Connection failed - running diagnostics...");

            // Get SSID from WiFiManager (it stores the last attempted SSID)
            String attemptedSSID = WiFi.SSID();
            if (attemptedSSID.length() == 0) {
                Serial.println("⚠️ No SSID stored - user did not enter credentials during portal session");

                // For FIRST_SETUP and NEW_LOCATION, restart to reopen portal
                if (scenario == FIRST_SETUP || scenario == NEW_LOCATION) {
                    Serial.println("🔄 Restarting to reopen configuration portal...");
                    delay(WiFiDelays::RESTART_DELAY_MS);
                    ESP.restart();
                }
            } else {
                Serial.printf("🔍 Diagnosing connection to: %s\n", attemptedSSID.c_str());

                // Run pre-scan diagnostics
                String diagnostic = diagnoseSSID(attemptedSSID.c_str());

                if (diagnostic.length() > 0) {
                    // Store for display in portal
                    lastWiFiError = diagnostic;
                    Serial.println("🔴 DIAGNOSTIC RESULT:");
                    Serial.println(diagnostic);
                    Serial.println("🔴 ==========================================");
                } else if (lastDisconnectReason != 0) {
                    // Store disconnect reason
                    Serial.println("🔴 DISCONNECT REASON:");
                    Serial.println(lastWiFiError);
                    Serial.println("🔴 ==========================================");
                }

                // Visual feedback: Checking location (all LEDs slow blinking purple)
                showCheckingLocation();
                delay(WiFiDelays::LOCATION_CHECK_DISPLAY_MS);

                // Check if moved to new location using fingerprinting
                if (!fingerprinting.isSameLocation()) {
                    Serial.println("🏠 NEW LOCATION DETECTED - Forcing AP mode");
                    lastWiFiError = "Moved to new location. Please reconfigure WiFi.";
                    break;  // Exit retry loop, go straight to AP mode
                }
            }

            // Retry delay for ROUTER_REBOOT and HAS_CREDENTIALS scenarios
            if (scenario == ROUTER_REBOOT) {
                // Exponential backoff delay: 5s, 10s, 20s, 40s...
                int delaySeconds = min(
                    WiFiDelays::INITIAL_RETRY_DELAY_SEC * (int)pow(2, attempt - 1),
                    WiFiDelays::MAX_RETRY_DELAY_SEC
                );
                Serial.printf("⏳ Waiting %d seconds before retry...\n", delaySeconds);
                delay(delaySeconds * 1000);
            } else if (scenario == HAS_CREDENTIALS && attempt < MAX_WIFI_RETRIES) {
                Serial.printf("⏳ Waiting %d seconds before retry...\n", WiFiDelays::INITIAL_RETRY_DELAY_SEC);
                delay(WiFiDelays::INITIAL_RETRY_DELAY_SEC * 1000);
            }
        }
    }

    if (!connected) {
        Serial.println("❌ Failed to connect after retries");
        Serial.println("📋 Final diagnostic summary:");
        Serial.printf("   Last SSID attempted: %s\n", WiFi.SSID().c_str());
        Serial.printf("   Last error: %s\n", lastWiFiError.c_str());
        Serial.printf("   Disconnect reason code: %d\n", lastDisconnectReason);
        
        // CRITICAL FIX: Do not return false to restart.
        // Instead, open the portal indefinitely so the user can fix the bad credentials.
        Serial.println("🔓 Starting Configuration Portal (Indefinite Wait)...");
        wifiManager.setConfigPortalTimeout(0); // Indefinite timeout

        // Visual feedback: AP Mode
        showAPMode();

        if (!wifiManager.startConfigPortal("SurfLamp-Setup", "surf123456")) {
             Serial.println("❌ Failed to connect in forced AP mode");
             // Only return false if even manual configuration failed/timed out (shouldn't happen with timeout 0)
             return false;
        }
        
        Serial.println("✅ Connected via forced AP mode!");
        connected = true;
    }

    Serial.println("✅ WiFi Connected!");
    Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());

    // Update WiFi fingerprint with current environment
    fingerprinting.update();

    return true;
}

void handleWiFiHealth() {
    unsigned long now = millis();

    if (WiFi.status() != WL_CONNECTED) {
        blinkRedLED();

        // Try to reconnect every 10 seconds
        if (now - lastReconnectAttempt > 10000) {
            lastReconnectAttempt = now;
            reconnectAttempts++;

            Serial.printf("🔄 WiFi disconnected - reconnection attempt %d of %d\n",
                          reconnectAttempts, MAX_WIFI_RETRIES);
            WiFi.reconnect();

            if (reconnectAttempts >= MAX_WIFI_RETRIES) {
                Serial.println("❌ Failed to reconnect after retries - restarting for config portal");
                delay(1000);
                ESP.restart(); // Will trigger config portal in setup
            }
        }
    } else {
        // Connected and operational

        // Reset reconnect counter when connected
        if (reconnectAttempts > 0) {
            Serial.println("✅ WiFi reconnected successfully");
            Serial.println("⏳ Waiting 10 seconds for network stack to stabilize...");
            delay(10000);  // Let DNS, routing, DHCP, ARP fully settle (critical after router power loss)
            reconnectAttempts = 0;
            wifiJustReconnected = true;  // Signal to fetch data immediately
            Serial.println("📡 Network ready - data fetch triggered");
        }
    }
}

void handleWiFiResetButton(WiFiManager& wifiManager) {
    static unsigned long buttonPressTime = 0;
    bool isPressed = (digitalRead(BUTTON_PIN) == LOW);

    if (isPressed) {
        // Button is currently being held down
        if (buttonPressTime == 0) {
            // This is the moment the button was first pressed
            buttonPressTime = millis();
            Serial.println("🔘 Button press detected. Hold for 2 seconds to reset WiFi...");
        } else if (millis() - buttonPressTime >= 2000) {
            // Button has been held for 2 seconds
            Serial.println("🔘 Button held for 2 seconds. Resetting WiFi now!");
            wifiManager.resetSettings(); // Wipe credentials
            delay(500); // Allow serial message to send
            ESP.restart();
        }
    } else {
        // Button is not pressed, so reset the timer
        if (buttonPressTime > 0) {
            // This indicates the button was released before the 2s mark
            Serial.println("🔘 Button released before reset triggered.");
        }
        buttonPressTime = 0;
    }
}
