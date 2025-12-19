#include "WiFiHandler.h"
#include "LedController.h"

// Global pointer for WiFiManager callbacks
static WiFiHandler* globalWiFiHandlerInstance = nullptr;

// ---------------- Wrapper Callbacks ----------------
void globalConfigModeCallback(WiFiManager *myWiFiManager) {
    if (globalWiFiHandlerInstance) {
        globalWiFiHandlerInstance->onConfigMode(myWiFiManager);
    }
}

void globalSaveConfigCallback() {
    if (globalWiFiHandlerInstance) {
        globalWiFiHandlerInstance->onSaveConfig();
    }
}

void globalSaveParamsCallback() {
    if (globalWiFiHandlerInstance) {
        globalWiFiHandlerInstance->onSaveParams();
    }
}

void globalWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    if (globalWiFiHandlerInstance) {
        globalWiFiHandlerInstance->handleWiFiEvent(event, info);
    }
}

// ---------------- Implementation ----------------

WiFiHandler::WiFiHandler(LedController& ledController, WiFiFingerprinting& fingerprinting) 
    : _ledController(ledController), _fingerprinting(fingerprinting) {
    globalWiFiHandlerInstance = this;
}

void WiFiHandler::onConfigMode(WiFiManager *myWiFiManager) {
    Serial.println("🔧 Config mode started");
    Serial.println("📱 AP: SurfLamp-Setup");
    _ledController.showAPMode();
}

void WiFiHandler::onSaveConfig() {
    Serial.println("✅ Config saved!");
}

void WiFiHandler::onSaveParams() {
    Serial.println("💾 Credentials saved, performing diagnostics...");
    String ssid = WiFi.SSID();
    if (ssid.length() == 0) {
        Serial.println("⏳ Will diagnose after connection attempt");
        return;
    }

    String diagnostic = diagnoseSSID(ssid.c_str());
    if (diagnostic.length() > 0) {
        lastWiFiError = diagnostic;
        Serial.printf("⚠️ Diagnostic warning: %s\n", diagnostic.c_str());
    }
}

String WiFiHandler::getDisconnectReasonText(uint8_t reason) {
    switch(reason) {
        case 1:  return "Unspecified error";
        case 2:  return "Authentication expired";
        case 3:  return "Deauthenticated";
        case 4:  return "Disassociated";
        case 5:  return "Too many devices";
        case 6:  return "Wrong password/WPA mismatch";
        case 7:  return "Wrong password";
        case 8:  return "Association timeout";
        case 15: return "4-way handshake timeout (wrong password)";
        case 201: return "Beacon timeout (AP lost)";
        case 202: return "No AP found";
        case 203: return "Auth failed";
        case 204: return "Assoc failed (AP rejected)";
        case 205: return "Handshake timeout";
        default: return "Unknown error (" + String(reason) + ")";
    }
}

void WiFiHandler::handleWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    switch(event) {
        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("✅ WiFi connected to AP");
            lastWiFiError = "";
            break;
        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            Serial.printf("✅ Got IP: %s\n", WiFi.localIP().toString().c_str());
            break;
        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            lastDisconnectReason = info.wifi_sta_disconnected.reason;
            lastWiFiError = getDisconnectReasonText(lastDisconnectReason);
            Serial.printf("❌ WiFi disconnected - Reason: %s\n", lastWiFiError.c_str());
            break;
        default:
            break;
    }
}

String WiFiHandler::diagnoseSSID(const char* targetSSID) {
    Serial.printf("🔍 Scanning for SSID: %s\n", targetSSID);
    int numNetworks = WiFi.scanNetworks();

    if (numNetworks == 0) return "No WiFi networks found.";

    int bestSignalIndex = -1;
    int bestRSSI = -127;

    for (int i = 0; i < numNetworks; i++) {
        if (WiFi.SSID(i) == targetSSID) {
            if (WiFi.RSSI(i) > bestRSSI) {
                bestRSSI = WiFi.RSSI(i);
                bestSignalIndex = i;
            }
        }
    }

    if (bestSignalIndex == -1) {
        return String("Network '") + targetSSID + "' not found.";
    }

    wifi_auth_mode_t authMode = (wifi_auth_mode_t)WiFi.encryptionType(bestSignalIndex);
    if (bestRSSI < -85) {
        return String("Weak signal (") + bestRSSI + " dBm).";
    }
    if (authMode == WIFI_AUTH_WPA3_PSK) {
        return "Router uses WPA3. ESP32 requires WPA2/Mixed.";
    }

    return "";
}

void WiFiHandler::setup() {
    WiFi.onEvent(globalWiFiEvent);
    
    _wifiManager.setAPCallback(globalConfigModeCallback);
    _wifiManager.setSaveConfigCallback(globalSaveConfigCallback);
    _wifiManager.setSaveParamsCallback(globalSaveParamsCallback);
    _wifiManager.setConfigPortalTimeout(0); 

    _fingerprinting.load();

    bool connected = false;
    String savedSSID = WiFi.SSID();
    bool hasCredentials = (savedSSID.length() > 0);

    // Scenario logic
    enum SetupScenario { FIRST_SETUP, ROUTER_REBOOT, NEW_LOCATION, HAS_CREDENTIALS };
    SetupScenario scenario = HAS_CREDENTIALS;

    if (!hasCredentials) {
        scenario = FIRST_SETUP;
        _wifiManager.setConfigPortalTimeout(600); // 10 mins
    }

    int maxAttempts = (scenario == ROUTER_REBOOT) ? MAX_WIFI_RETRIES : 1;

    for (int attempt = 1; attempt <= maxAttempts && !connected; attempt++) {
        Serial.printf("🔄 WiFi connection attempt %d of %d\n", attempt, maxAttempts);
        _ledController.showTryingToConnect();

        if (scenario == ROUTER_REBOOT) {
            int timeout = min(30 * (int)pow(2, attempt - 1), 300);
            _wifiManager.setConfigPortalTimeout(timeout);
        } else if (scenario == HAS_CREDENTIALS) {
            _wifiManager.setConfigPortalTimeout(attempt < MAX_WIFI_RETRIES ? 30 : 0);
        }

        if (lastWiFiError.length() > 0) {
            String customHTML = "<div style='background:#ff4444;color:white;padding:10px;'>";
            customHTML += "<strong>❌ Connection Failed</strong><br>" + lastWiFiError + "</div>";
            _wifiManager.setCustomHeadElement(customHTML.c_str());
        }

        connected = _wifiManager.autoConnect("SurfLamp-Setup", "surf123456");

        if (!connected) {
            Serial.println("❌ Connection failed");
            String attemptedSSID = WiFi.SSID();
            
            if (attemptedSSID.length() == 0 && (scenario == FIRST_SETUP || scenario == NEW_LOCATION)) {
                delay(3000);
                ESP.restart();
            } else {
                String diagnostic = diagnoseSSID(attemptedSSID.c_str());
                if (diagnostic.length() > 0) lastWiFiError = diagnostic;
                
                _ledController.showCheckingLocation();
                delay(1000);

                if (!_fingerprinting.isSameLocation()) {
                    lastWiFiError = "Moved to new location. Please reconfigure.";
                    break; 
                }
            }
            
            if ((scenario == ROUTER_REBOOT || scenario == HAS_CREDENTIALS) && attempt < maxAttempts) {
                delay((scenario == ROUTER_REBOOT ? 10 : 5) * 1000);
            }
        }
    }

    if (!connected) {
        Serial.println("❌ Failed after retries. Restarting...");
        delay(3000);
        ESP.restart();
    }

    Serial.println("✅ WiFi Connected!");
    _fingerprinting.update();
}

void WiFiHandler::loop() {
    static unsigned long lastCheck = 0;
    if (millis() - lastCheck >= 1000) {
        lastCheck = millis();
        // Check for button reset (TODO: This probably belongs in main or passed in)
        if (digitalRead(BUTTON_PIN) == LOW) {
             Serial.println("🔘 Button pressed - resetting WiFi");
             _wifiManager.resetSettings();
             delay(500);
             ESP.restart();
        }
    }

    if (WiFi.status() != WL_CONNECTED) {
        _ledController.blinkRedLED();
        if (millis() - lastReconnectAttempt > 10000) {
            lastReconnectAttempt = millis();
            reconnectAttempts++;
            WiFi.reconnect();
            if (reconnectAttempts >= MAX_WIFI_RETRIES) {
                ESP.restart();
            }
        }
    } else {
        if (reconnectAttempts > 0) reconnectAttempts = 0;
    }
}
