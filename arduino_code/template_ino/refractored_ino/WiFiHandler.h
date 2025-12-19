#ifndef WIFI_HANDLER_H
#define WIFI_HANDLER_H

#include <WiFi.h>
#include <WiFiManager.h>
#include "Config.h"
#include "WiFiFingerprinting.h"
#include "SurfState.h"

// Forward declaration to avoid circular includes
class LedController;

class WiFiHandler {
public:
    WiFiHandler(LedController& ledController, WiFiFingerprinting& fingerprinting);

    void setup();
    void loop();
    
    // Diagnostics
    String getLastWiFiError() const { return lastWiFiError; }
    uint8_t getLastDisconnectReason() const { return lastDisconnectReason; }
    String getDisconnectReasonText(uint8_t reason);
    String diagnoseSSID(const char* targetSSID);

    // Callbacks (must be public to be accessible by global wrappers if needed, 
    // though friend functions are also an option)
    void onConfigMode(WiFiManager *myWiFiManager);
    void onSaveConfig();
    void onSaveParams();
    void handleWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info);

private:
    LedController& _ledController;
    WiFiFingerprinting& _fingerprinting;
    WiFiManager _wifiManager;

    String lastWiFiError = "";
    uint8_t lastDisconnectReason = 0;
    int reconnectAttempts = 0;
    unsigned long lastReconnectAttempt = 0;

    // Helper for visual feedback
    void updateConnectionVisuals();
};

#endif // WIFI_HANDLER_H
