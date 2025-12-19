#ifndef WEB_SERVER_HANDLER_H
#define WEB_SERVER_HANDLER_H

#include <WebServer.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

#include "Config.h"
#include "SurfState.h"
#include "LedController.h"
#include "WiFiHandler.h"
#include "ServerDiscovery.h"

class WebServerHandler {
public:
    WebServerHandler(SurfData& surfData, LedController& ledController, WiFiHandler& wifiHandler, ServerDiscovery& serverDiscovery);

    void setup();
    void handleClient(); // Call in loop

    // Client functions (Fetching data)
    bool fetchSurfDataFromServer();
    unsigned long getLastFetchTime() const { return lastDataFetch; }

private:
    WebServer server;
    SurfData& _surfData;
    LedController& _ledController;
    WiFiHandler& _wifiHandler;
    ServerDiscovery& _serverDiscovery;
    
    unsigned long lastDataFetch = 0;

    // Route Handlers
    void handleSurfDataUpdate();
    void handleStatusRequest();
    void handleTestRequest();
    void handleLEDTestRequest();
    void handleStatusLEDTestRequest();
    void handleDeviceInfoRequest();
    void handleManualFetchRequest();
    void handleWiFiDiagnostics();
    void handleDiscoveryTest();

    // Helpers
    bool processSurfData(const String& jsonData);
};

#endif // WEB_SERVER_HANDLER_H
