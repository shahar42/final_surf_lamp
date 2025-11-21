/**
 * DataFetcher.h
 *
 * Handles fetching surf data from the backend server.
 *
 * RESPONSIBILITIES:
 * - HTTP GET requests to backend API
 * - Server discovery integration
 * - Request timeout handling
 * - Publishing EVENT_DATA_RECEIVED on success
 *
 * EVENTS PUBLISHED:
 * - EVENT_DATA_RECEIVED (with JSON string payload)
 *
 * EVENTS SUBSCRIBED:
 * - None (can be triggered by TaskScheduler or manual HTTP endpoint)
 */

#ifndef DATA_FETCHER_H
#define DATA_FETCHER_H

#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "../core/EventBus.h"
#include "ServerDiscovery.h"
#include "../config/SystemConfig.h"

class DataFetcher {
private:
    EventBus& eventBus;
    ServerDiscovery& serverDiscovery;
    int arduinoId;
    unsigned long lastFetchTime;

public:
    /**
     * Constructor
     * @param events Reference to the global EventBus
     * @param discovery Reference to the ServerDiscovery instance
     * @param deviceId Arduino device ID for API requests
     */
    DataFetcher(EventBus& events, ServerDiscovery& discovery, int deviceId)
        : eventBus(events), serverDiscovery(discovery), arduinoId(deviceId), lastFetchTime(0) {
        Serial.println("📡 DataFetcher initialized");
    }

    /**
     * Fetch surf data from the discovered backend server
     * @return true if fetch successful and data published, false otherwise
     */
    bool fetchSurfData() {
        String apiServer = serverDiscovery.getApiServer();
        if (apiServer.length() == 0) {
            Serial.println("❌ DataFetcher: No API server available");
            return false;
        }

        HTTPClient http;
        WiFiClientSecure client;

        String url = "https://" + apiServer + "/api/arduino/" + String(arduinoId) + "/data";
        Serial.println("🌐 DataFetcher: Fetching from " + url);

        client.setInsecure();  // Skip certificate validation (production should use proper certs)

        http.begin(client, url);
        http.setTimeout(SystemConfig::HTTP_TIMEOUT_MS);

        int httpCode = http.GET();

        if (httpCode == HTTP_CODE_OK) {
            String payload = http.getString();
            http.end();

            Serial.println("📥 DataFetcher: Received " + String(payload.length()) + " bytes");
            lastFetchTime = millis();

            // Publish event with JSON payload (subscribers will parse)
            eventBus.publish(EVENT_DATA_RECEIVED, (void*)payload.c_str());

            return true;
        } else {
            Serial.printf("❌ DataFetcher: HTTP error %d (%s)\n",
                         httpCode, http.errorToString(httpCode).c_str());
            http.end();
            return false;
        }
    }

    /**
     * Get timestamp of last successful fetch
     */
    unsigned long getLastFetchTime() const {
        return lastFetchTime;
    }

    /**
     * Get time since last fetch in milliseconds
     */
    unsigned long getTimeSinceLastFetch() const {
        return millis() - lastFetchTime;
    }

    /**
     * Check if it's time to fetch new data
     * @param interval Fetch interval in milliseconds
     */
    bool shouldFetch(unsigned long interval) const {
        return (millis() - lastFetchTime) >= interval;
    }
};

#endif // DATA_FETCHER_H
