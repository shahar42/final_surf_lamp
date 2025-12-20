/*
 * WIFI HANDLER - IMPLEMENTATION
 *
 * WiFi connection management and diagnostics.
 */

#include "WiFiHandler.h"
#include "LedController.h"

// Global WiFi state (defined here, declared extern in header)
String lastWiFiError = "";
uint8_t lastDisconnectReason = 0;
int reconnectAttempts = 0;
unsigned long lastReconnectAttempt = 0;

const int MAX_WIFI_RETRIES = 10;  // 10 attempts × 30s = ~5 min (covers router boot times)

// ---------------- DIAGNOSTICS ----------------

String getDisconnectReasonText(uint8_t reason) {
    switch(reason) {
        case 1:  return "Unspecified error";
        case 2:  return "Authentication expired - wrong password or security mode";
        case 3:  return "Deauthenticated (AP kicked device)";
        case 4:  return "Disassociated (inactive)";
        case 5:  return "Too many devices connected to AP";
        case 6:  return "Wrong password or WPA/WPA2 mismatch";
        case 7:  return "Wrong password";
        case 8:  return "Association expired (timeout)";
        case 15: return "4-way handshake timeout - likely wrong password";
        case 23: return "Too many authentication failures";
        case 201: return "Beacon timeout - AP disappeared or weak signal";
        case 202: return "No AP found with this SSID";
        case 203: return "Authentication failed - check password and security mode";
        case 204: return "Association failed - AP rejected connection";
        case 205: return "Handshake timeout - wrong password or security mismatch";
        default: return "Unknown error (code: " + String(reason) + ")";
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
    switch(event) {
        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("✅ WiFi connected to AP");
            lastWiFiError = "";  // Clear error on success
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
    // WiFiManager setup with enhanced diagnostics
    wifiManager.setAPCallback(configModeCallback);
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setSaveParamsCallback(saveParamsCallback);
    wifiManager.setConfigPortalTimeout(0); // No timeout - wait indefinitely

    // Load WiFi fingerprint from NVS
    fingerprinting.load();

    // Auto-connect with scenario-based timeout strategy (IoT industry best practices)
    bool connected = false;

    // CRITICAL: Detect credentials state BEFORE entering retry loop
    String savedSSID = WiFi.SSID();
    bool hasCredentials = (savedSSID.length() > 0);

    // Scenario detection for optimal timeout strategy
    enum SetupScenario { FIRST_SETUP, ROUTER_REBOOT, NEW_LOCATION, HAS_CREDENTIALS };
    SetupScenario scenario = HAS_CREDENTIALS;

    if (!hasCredentials) {
        Serial.println("📋 No WiFi credentials saved - opening configuration portal");

        // CRITICAL FIX: Do NOT scan for fingerprinting before AP mode
        // WiFi scanning while AP is active causes watchdog crashes
        // Default to generous timeout for all first-time setup scenarios
        scenario = FIRST_SETUP;
        Serial.println("🆕 FIRST SETUP MODE");
        Serial.println("   Opening configuration portal for 10 minutes");
        wifiManager.setConfigPortalTimeout(600); // 10 minutes - safe for all scenarios
    }

    // Retry loop with scenario-based timeout strategy
    int maxAttempts = (scenario == ROUTER_REBOOT) ? MAX_WIFI_RETRIES : 1;
    for (int attempt = 1; attempt <= maxAttempts && !connected; attempt++) {
        Serial.printf("🔄 WiFi connection attempt %d of %d\n", attempt, maxAttempts);

        // Visual feedback: Trying to connect (all LEDs slow blinking green)
        showTryingToConnect();

        // Set timeout based on scenario
        if (scenario == ROUTER_REBOOT) {
            // ROUTER REBOOT: Exponential backoff - 30s, 60s, 120s, 240s → capped at 300s (5 min)
            int timeout = min(30 * (int)pow(2, attempt - 1), 300);
            wifiManager.setConfigPortalTimeout(timeout);
            Serial.printf("   Portal timeout: %d seconds (exponential backoff for router reboot)\n", timeout);
        } else if (scenario == HAS_CREDENTIALS) {
            // HAS CREDENTIALS but connection failing - standard retry strategy
            if (attempt < MAX_WIFI_RETRIES) {
                wifiManager.setConfigPortalTimeout(30); // Quick retries
            } else {
                wifiManager.setConfigPortalTimeout(0); // Final attempt: indefinite
            }
        }
        // else: FIRST_SETUP and NEW_LOCATION timeouts already set above

        // Inject error message into portal if we have one
        if (lastWiFiError.length() > 0) {
            String customHTML = "<div style='background:#ff4444;color:white;padding:10px;margin:10px 0;border-radius:5px;'>";
            customHTML += "<strong>❌ Connection Failed</strong><br>";
            customHTML += lastWiFiError;
            customHTML += "</div>";
            wifiManager.setCustomHeadElement(customHTML.c_str());
        }

        connected = wifiManager.autoConnect("SurfLamp-Setup", "surf123456");

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
                    delay(3000);
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
                delay(1000);  // Show purple for 1 second before decision

                // Check if moved to new location using fingerprinting
                if (!fingerprinting.isSameLocation()) {
                    Serial.println("🏠 NEW LOCATION DETECTED - Forcing AP mode");
                    lastWiFiError = "Moved to new location. Please reconfigure WiFi.";
                    break;  // Exit retry loop, go straight to AP mode
                }
            }

            // Retry delay for ROUTER_REBOOT and HAS_CREDENTIALS scenarios
            if ((scenario == ROUTER_REBOOT || scenario == HAS_CREDENTIALS) && attempt < maxAttempts) {
                int delaySeconds = (scenario == ROUTER_REBOOT) ? 10 : 5;
                Serial.printf("⏳ Waiting %d seconds before retry...\n", delaySeconds);
                delay(delaySeconds * 1000);
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
            reconnectAttempts = 0;
        }
    }
}

void handleWiFiResetButton(WiFiManager& wifiManager) {
    // Check for button press to reset WiFi (check every 1 second)
    static unsigned long lastButtonCheck = 0;
    unsigned long now = millis();

    if (now - lastButtonCheck >= 1000) {
        lastButtonCheck = now;
        if (digitalRead(BUTTON_PIN) == LOW) {
            Serial.println("🔘 Button pressed - resetting WiFi");
            wifiManager.resetSettings(); // Wipe credentials
            delay(500);
            ESP.restart();
        }
    }
}
