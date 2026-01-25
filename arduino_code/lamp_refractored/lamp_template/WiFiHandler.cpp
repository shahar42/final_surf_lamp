/*
 * WIFI HANDLER - IMPLEMENTATION
 *
 * WiFi connection management and diagnostics.
 * Includes "Pulse Strategy" for robust reconnection:
 * 1. Initial 7-min retry (handles slow routers/DFS).
 * 2. 30-min AP Mode (user configuration window).
 * 3. 45-sec "Pulse" check (attempts silent reconnect).
 * 4. Loop 2 & 3 indefinitely.
 */

#include "WiFiHandler.h"
#include "SurfState.h"
#include "LedController.h"
#include "esp_wifi.h"
#include "JitterManager.h"

// Global WiFi state
String lastWiFiError = "";
uint8_t lastDisconnectReason = 0;
int reconnectAttempts = 0;
unsigned long lastReconnectAttempt = 0;
WiFiManager* globalWiFiManager = nullptr;
static String persistentErrorHTML = "";
static bool allowErrorInjection = false;

const int MAX_WIFI_RETRIES = 10;

// ---------------- TIMEOUT CONSTANTS ----------------
namespace WiFiTimeouts {
    const int PORTAL_TIMEOUT_SEC = 1800;             // 30 minutes (AP Window)
    const int INITIAL_RETRY_TIMEOUT_MS = 420000;     // 7 minutes (Initial Wait)
    const int PULSE_CHECK_TIMEOUT_MS = 45000;        // 45 seconds (Silent Retry)
    const int INITIAL_CONNECTION_TIMEOUT_SEC = 20;
    const int MAX_CONNECTION_TIMEOUT_SEC = 60;
}

// ---------------- DELAY CONSTANTS ----------------
namespace WiFiDelays {
    const int INITIAL_RETRY_DELAY_SEC = 5;
    const int MAX_RETRY_DELAY_SEC = 60;
    const int LOCATION_CHECK_DISPLAY_MS = 1000;
    const int RESTART_DELAY_MS = 3000;
    const int CONNECTION_POLL_MS = 500;
}

// ---------------- HELPER FUNCTIONS ----------------

// Check if button is held for 2 seconds to force AP mode
bool checkButtonOverride() {
    if (digitalRead(BUTTON_PIN) == LOW) {
        unsigned long start = millis();
        // Wait up to 2 seconds
        while (digitalRead(BUTTON_PIN) == LOW) {
            if (millis() - start > 2000) {
                return true; // Button held!
            }
            delay(10);
        }
    }
    return false;
}

int calculateExponentialTimeout(int attempt, int initialSeconds, int maxSeconds) {
    return min(initialSeconds * (int)pow(2, attempt - 1), maxSeconds);
}

int calculateExponentialDelay(int attempt, int initialSeconds, int maxSeconds) {
    return min(initialSeconds * (int)pow(2, attempt - 1), maxSeconds);
}

// ---------------- WIFI SETUP SCENARIOS ----------------

enum class WiFiSetupScenario {
    FIRST_SETUP,       // No credentials saved
    ROUTER_REBOOT,     // Has credentials, same location
    NEW_LOCATION,      // Has credentials, moved to different location
    HAS_CREDENTIALS    // Has credentials (generic fallback)
};

struct DiagnosticResult {
    String errorMessage;
    bool isNewLocation;
    bool shouldRestart;
};

WiFiSetupScenario detectWiFiScenario(WiFiFingerprinting& fingerprinting) {
    WiFi.mode(WIFI_STA);
    wifi_config_t wifi_cfg;
    esp_err_t err = esp_wifi_get_config(WIFI_IF_STA, &wifi_cfg);
    bool hasCredentials = (err == ESP_OK && strlen((char*)wifi_cfg.sta.ssid) > 0);

    if (hasCredentials) {
        Serial.printf("📡 Found saved credentials for SSID: %s\n", (char*)wifi_cfg.sta.ssid);
    } else {
        Serial.println("📡 No saved WiFi credentials found");
    }

    if (!hasCredentials) {
        return WiFiSetupScenario::FIRST_SETUP;
    }

    // Smart Location Detection
    if (!fingerprinting.isSameLocation()) {
        Serial.println("🌍 New location detected! Skipping retry and opening portal immediately.");
        return WiFiSetupScenario::NEW_LOCATION;
    }

    return WiFiSetupScenario::ROUTER_REBOOT;
}

void configurePortalForScenario(WiFiManager& wifiManager, WiFiSetupScenario scenario) {
    // Basic setup - specific timeouts handled in the loop
    if (scenario == WiFiSetupScenario::FIRST_SETUP) {
        Serial.println("🆕 FIRST SETUP MODE - Opening portal");
    } else {
        Serial.println("🔌 REBOOT MODE - Will try to connect before opening portal");
    }
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

    if (numNetworks == 0) return "No WiFi networks found.";

    int bestRSSI = -127;
    int bestIndex = -1;

    for (int i = 0; i < numNetworks; i++) {
        if (WiFi.SSID(i) == targetSSID) {
            if (WiFi.RSSI(i) > bestRSSI) {
                bestRSSI = WiFi.RSSI(i);
                bestIndex = i;
            }
        }
    }

    if (bestIndex == -1) {
        return String("Network '") + targetSSID + "' not found.";
    }

    if (bestRSSI < -85) {
        return String("Weak signal (") + bestRSSI + " dBm).";
    }

    wifi_auth_mode_t authMode = (wifi_auth_mode_t)WiFi.encryptionType(bestIndex);
    if (authMode == WIFI_AUTH_WPA3_PSK) {
        return "Router uses WPA3. ESP32 requires WPA2.";
    }

    return "";
}

// ---------------- EVENT HANDLERS ----------------

void WiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    static uint8_t lastPrintedReason = 0;
    static unsigned long lastErrorPrint = 0;

    switch(event) {
        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("✅ WiFi connected to AP");
            lastWiFiError = "";
            persistentErrorHTML = "";
            lastPrintedReason = 0;
            break;

        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            Serial.printf("✅ Got IP: %s\n", WiFi.localIP().toString().c_str());
            break;

        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED: {
            lastDisconnectReason = info.wifi_sta_disconnected.reason;
            lastWiFiError = getDisconnectReasonText(lastDisconnectReason);

            unsigned long now = millis();
            if (lastDisconnectReason != lastPrintedReason || (now - lastErrorPrint > 10000)) {
                Serial.printf("❌ WiFi disconnected - Reason: %s\n", lastWiFiError.c_str());
                lastPrintedReason = lastDisconnectReason;
                lastErrorPrint = now;
            }

            if (allowErrorInjection && globalWiFiManager != nullptr && lastWiFiError.length() > 0) {
                persistentErrorHTML = "<div style='background:#ff4444;color:white;padding:15px;'>";
                persistentErrorHTML += "<strong>❌ Error:</strong><br>" + lastWiFiError;
                persistentErrorHTML += "</div>";
                globalWiFiManager->setCustomHeadElement(persistentErrorHTML.c_str());
            }
            break;
        }
        default: break;
    }
}

void configModeCallback(WiFiManager *myWiFiManager) {
    Serial.println("🔧 Config mode started");
    Serial.println("📱 AP: SurfLamp-Setup");
    showAPMode();
}

void saveConfigCallback() {
    Serial.println("✅ Config saved!");
}

void saveParamsCallback() {
    Serial.println("💾 Credentials saved, performing diagnostics...");
    allowErrorInjection = true;
    String ssid = WiFi.SSID();
    if (ssid.length() > 0) {
        String diagnostic = diagnoseSSID(ssid.c_str());
        if (diagnostic.length() > 0) {
            lastWiFiError = diagnostic;
        }
    }
}

// ---------------- WIFI CONNECTION ----------------

bool setupWiFi(WiFiManager& wifiManager, WiFiFingerprinting& fingerprinting) {
    globalWiFiManager = &wifiManager;
    lastWiFiError = "";
    persistentErrorHTML = "";
    allowErrorInjection = false;
    wifiManager.setCustomHeadElement("");

    wifiManager.setAPCallback(configModeCallback);
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setSaveParamsCallback(saveParamsCallback);
    wifiManager.setConnectTimeout(30); 

    fingerprinting.load();
    WiFiSetupScenario scenario = detectWiFiScenario(fingerprinting);

    // PHASE 1: INITIAL 7-MINUTE ATTEMPT (Only if credentials exist)
    if (scenario == WiFiSetupScenario::ROUTER_REBOOT) {
        Serial.println("⏳ PHASE 1: Attempting connection for 7 minutes...");
        Serial.println("👉 Hold button for 2s to skip to AP mode");

        // Print credentials for debugging
        wifi_config_t wifi_cfg;
        esp_wifi_get_config(WIFI_IF_STA, &wifi_cfg);
        Serial.printf("🔑 Using SSID: '%s'\n", (char*)wifi_cfg.sta.ssid);
        Serial.printf("🔑 Using Password: '%s'\n", (char*)wifi_cfg.sta.password);

        WiFi.begin(); // Use saved credentials
        
        unsigned long start = millis();
        // Loop for 7 minutes or until connected
        while (millis() - start < WiFiTimeouts::INITIAL_RETRY_TIMEOUT_MS) {
            
            // 1. Check Connection
            if (WiFi.status() == WL_CONNECTED) {
                Serial.println("✅ Connected during Phase 1!");
                fingerprinting.update();
                return true;
            }

            // 2. Check Button Override
            if (checkButtonOverride()) {
                Serial.println("🔘 Button Override Detected! Jumping to AP Mode...");
                break; // Break loop -> Go to Phase 2
            }

            // 3. Visual Feedback (Trying to connect)
            showTryingToConnect();
            
            // 4. Retry Logic (every 30s if disconnected)
            static unsigned long lastRetry = 0;
            if (millis() - lastRetry > 30000 && WiFi.status() != WL_CONNECTED) {
                Serial.println("🔄 Retrying connection...");
                WiFi.reconnect();
                lastRetry = millis();
            }
            
            delay(100);
        }
        
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("❌ Phase 1 timeout (7 mins). Entering Heartbeat Cycle.");
        }
    }

    // PHASE 2: HEARTBEAT CYCLE (30 min AP -> 45s Check -> Repeat)
    Serial.println("💓 Entering Heartbeat Cycle (30min AP / 45s Check)");
    
    while (true) {
        // A. AP MODE (30 Minutes)
        Serial.println("📡 Starting AP Mode for 30 minutes...");
        wifiManager.setConfigPortalTimeout(WiFiTimeouts::PORTAL_TIMEOUT_SEC);
        
        // This blocks for 30 minutes OR until user connects & configures
        if (wifiManager.startConfigPortal("SurfLamp-Setup")) {
             Serial.println("✅ Connected via Portal!");
             fingerprinting.update();
             return true;
        }

        // B. PULSE CHECK (45 Seconds)
        Serial.println("💓 Heartbeat: Checking saved WiFi for 45s...");
        WiFi.mode(WIFI_STA); // Stop AP
        WiFi.begin();        // Try saved creds
        
        unsigned long pulseStart = millis();
        bool connected = false;
        
        while (millis() - pulseStart < WiFiTimeouts::PULSE_CHECK_TIMEOUT_MS) {
            if (WiFi.status() == WL_CONNECTED) {
                connected = true;
                break;
            }
            showTryingToConnect();
            delay(100);
        }
        
        if (connected) {
            Serial.println("✅ Connected during Heartbeat!");
            fingerprinting.update();
            return true;
        }
        
        Serial.println("❌ Heartbeat failed. Returning to AP Mode.");
        // Loop continues -> Back to AP Mode
    }
}

void handleWiFiHealth() {
    unsigned long now = millis();

    if (WiFi.status() != WL_CONNECTED) {
        blinkRedLED();
        if (now - lastReconnectAttempt > 10000) {
            lastReconnectAttempt = now;
            reconnectAttempts++;
            Serial.printf("🔄 WiFi disconnected - attempt %d\n", reconnectAttempts);
            WiFi.reconnect();
            
            // If we fail too many times in runtime, maybe we should restart 
            // to enter the clean "Pulse Cycle" logic in setup()? 
            // For now, simple retry is safer for short glitches.
            if (reconnectAttempts > 60) { // ~10 minutes
                 Serial.println("❌ Long disconnection. Restarting to enter Pulse Cycle.");
                 ESP.restart();
            }
        }
    } else {
        if (reconnectAttempts > 0) {
            Serial.println("✅ WiFi reconnected");
            reconnectAttempts = 0;
            
            // Apply jitter before fetching data to prevent server overload
            unsigned long jitterMs = JitterManager::getReconnectJitterMs();
            Serial.printf("⏱ Applying reconnect jitter: %lu ms\n", jitterMs);
            delay(jitterMs);
            
            wifiJustReconnected = true;
            delay(1000); 
        }
    }
}

void handleWiFiResetButton(WiFiManager& wifiManager) {
    // This function handles the RUNTIME reset (while already connected)
    // The boot-time override is handled in checkButtonOverride()
    static unsigned long buttonPressTime = 0;
    bool isPressed = (digitalRead(BUTTON_PIN) == LOW);

    if (isPressed) {
        if (buttonPressTime == 0) {
            buttonPressTime = millis();
            Serial.println("🔘 Button pressed...");
        } else if (millis() - buttonPressTime >= 2000) {
            Serial.println("🔘 Resetting WiFi Settings & Restarting...");
            wifiManager.resetSettings();
            delay(500);
            ESP.restart();
        }
    } else {
        buttonPressTime = 0;
    }
}
