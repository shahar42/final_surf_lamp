#ifndef SERVER_DISCOVERY_H
#define SERVER_DISCOVERY_H

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WiFiClientSecure.h>

class ServerDiscovery {
private:
    // Discovery URLs (static files - free and reliable)
    const char* discovery_urls[2] = {
        "https://shahar42.github.io/final_surf_lamp/discovery-config/config.json",
        "https://raw.githubusercontent.com/shahar42/final_surf_lamp/master/discovery-config/config.json"
    };

    String current_server = "";  // MUST be discovered from GitHub, no fallback
    unsigned long last_discovery_attempt = 0;
    const unsigned long DISCOVERY_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours
    bool discovery_enabled = true;

public:
    ServerDiscovery() {
        // No fallback - server MUST be discovered from GitHub
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
                Serial.println("⚠️ Discovery failed - NO FALLBACK, will return empty");
                last_discovery_attempt = millis(); // Don't retry immediately
            }
        }

        return current_server;  // Empty if discovery never succeeded
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

        const int MAX_ATTEMPTS = 5;

        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            // Alternate between the two discovery URLs
            int urlIndex = (attempt - 1) % 2;
            Serial.printf("   Attempt %d/%d - Trying discovery URL %d: %s\n",
                         attempt, MAX_ATTEMPTS, urlIndex + 1, discovery_urls[urlIndex]);

            String result = fetchDiscoveryConfig(discovery_urls[urlIndex]);
            if (result.length() > 0) {
                Serial.println("   ✅ Discovery successful from URL " + String(urlIndex + 1));
                return result;
            }

            if (attempt < MAX_ATTEMPTS) {
                // Exponential backoff: 5s, 10s, 20s, 40s
                int delaySeconds = min(5 * (int)pow(2, attempt - 1), 40);
                Serial.printf("   ⏳ Waiting %d seconds before next attempt...\n", delaySeconds);
                delay(delaySeconds * 1000);
            }
        }

        Serial.println("   ❌ All discovery attempts failed");
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
