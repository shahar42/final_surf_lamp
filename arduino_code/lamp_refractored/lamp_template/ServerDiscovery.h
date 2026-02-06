/*
author: shahar
about:
*/

#ifndef SERVER_DISCOVERY_H
#define SERVER_DISCOVERY_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WiFiClientSecure.h>

class ServerDiscovery {
private:
    // Discovery URLs: Vercel (primary) → GitHub (fallback)
    // New flashes hit Vercel first. Already-flashed lamps still use the old single-URL build.
    static constexpr const char* DISCOVERY_URLS[] = {
        "https://surf-lamp-discovery.vercel.app/config.json",
        "https://raw.githubusercontent.com/shahar42/final_surf_lamp/master/discovery-config/config.json"
    };
    static constexpr int PRIMARY_ATTEMPTS = 3; // Attempts on Vercel before falling back to GitHub

    String current_server = "";
    unsigned long last_discovery_attempt = 0;
    const unsigned long DISCOVERY_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours
    bool discovery_enabled = true;

public:
    ServerDiscovery() {
        current_server = "";
    }

    // Main method - gets current API server
    String getApiServer() {
        // CRITICAL: If no server available, MUST attempt discovery (ignore interval)
        if (current_server.length() == 0 || shouldTryDiscovery()) {
            String discovered = attemptDiscovery();
            if (discovered.length() > 0) {
                Serial.println("📡 Discovery successful: " + discovered);
                current_server = discovered;
                last_discovery_attempt = millis();
            } else {
                Serial.println("⚠️ Discovery failed - no fallback, will retry later");
                last_discovery_attempt = millis();
            }
        }

        return current_server;
    }
    
    // Force discovery attempt (for testing)
    bool forceDiscovery() {
        String discovered = attemptDiscovery();
        if (discovered.length() > 0) {
            current_server = discovered;
            last_discovery_attempt = millis();
            return true;
        }
        return false;
    }
    
    // Get current server without discovery attempt
    String getCurrentServer() {
        return current_server;
    }
    
    // Enable/disable discovery (for debugging)
    void setDiscoveryEnabled(bool enabled) {
        discovery_enabled = enabled;
    }
    
private:
    bool shouldTryDiscovery() {
        if (!discovery_enabled) return false;
        if (WiFi.status() != WL_CONNECTED) return false;
        
        // Try discovery on first run or after interval
        return (last_discovery_attempt == 0) || 
               (millis() - last_discovery_attempt > DISCOVERY_INTERVAL);
    }
    
    String attemptDiscovery() {
        Serial.println("🔍 Attempting server discovery...");

        const int MAX_ATTEMPTS = 7;
        const int BASE_DELAY_MS = 1000;      // 1 second initial
        const int MAX_DELAY_MS = 60000;      // Cap at 60 seconds

        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            // Attempts 1-3: Vercel (primary). Attempts 4-7: GitHub (fallback).
            bool usingPrimary = (attempt <= PRIMARY_ATTEMPTS);
            const char* url = usingPrimary ? DISCOVERY_URLS[0] : DISCOVERY_URLS[1];

            // Log the source switch on the boundary
            if (attempt == PRIMARY_ATTEMPTS + 1) {
                Serial.println("   ⚡ Vercel failed, switching to GitHub fallback");
            }

            Serial.printf("   Attempt %d/%d [%s]\n", attempt, MAX_ATTEMPTS,
                          usingPrimary ? "Vercel" : "GitHub");

            String result = fetchDiscoveryConfig(url);
            if (result.length() > 0) {
                Serial.println("   ✅ Discovery successful");
                return result;
            }

            if (attempt < MAX_ATTEMPTS) {
                // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s (capped at 60s)
                int baseDelay = BASE_DELAY_MS * (1 << (attempt - 1));
                baseDelay = min(baseDelay, MAX_DELAY_MS);

                // Add jitter: random 0-50% of delay to prevent thundering herd
                int jitter = random(0, baseDelay / 2);
                int totalDelay = baseDelay + jitter;

                Serial.printf("   ⏳ Retry in %d ms (base=%d, jitter=%d)\n", totalDelay, baseDelay, jitter);
                delay(totalDelay);
            }
        }

        Serial.println("   ❌ Discovery failed after all attempts");
        return "";
    }
    
    String fetchDiscoveryConfig(const char* url) {
        HTTPClient http;
        WiFiClientSecure client;

        client.setInsecure(); // Allow insecure connections for discovery

        http.begin(client, url);
        http.setTimeout(10000); // 10 second timeout
        
        int httpCode = http.GET();
        
        if (httpCode == HTTP_CODE_OK) {
            String payload = http.getString();
            http.end();
            
            // Parse JSON and extract server
            return parseDiscoveryResponse(payload);
        } else {
            Serial.printf("   HTTP error: %d (%s)\n", httpCode, http.errorToString(httpCode).c_str());
            http.end();
            return "";
        }
    }
    
    String parseDiscoveryResponse(String jsonString) {
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, jsonString);
        
        if (error) {
            Serial.println("   JSON parsing failed: " + String(error.c_str()));
            return "";
        }
        
        // Extract API server
        const char* api_server = doc["api_server"];
        if (api_server && strlen(api_server) > 0) {
            String server = String(api_server);
            
            // Basic validation
            if (server.indexOf("http") == 0) {
                // Remove http:// or https:// for our use
                server.replace("https://", "");
                server.replace("http://", "");
            }
            
            // Validate server format (basic check)
            if (server.indexOf('.') > 0 && server.length() > 5) {
                return server;
            }
        }
        
        Serial.println("   Invalid server in discovery response");
        return "";
    }
};
#endif 
