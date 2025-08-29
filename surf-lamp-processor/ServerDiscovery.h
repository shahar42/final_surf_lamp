#ifndef SERVER_DISCOVERY_H
#define SERVER_DISCOVERY_H

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

class ServerDiscovery {
private:
    // Hardcoded fallback servers (Phase 1 compatibility)
    const char* fallback_servers[3] = {
        "surf-lamp-api.render.com",
        "backup-api.herokuapp.com", 
        "localhost:5001"  // For development
    };
    
    // Discovery URLs (static files - free and reliable)
    const char* discovery_urls[2] = {
        "https://shahar42.github.io/surflamp-discovery/config.json",
        "https://raw.githubusercontent.com/shahar42/surflamp-discovery/main/config.json"
    };
    
    String current_server = "";
    unsigned long last_discovery_attempt = 0;
    const unsigned long DISCOVERY_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours
    bool discovery_enabled = true;
    
public:
    ServerDiscovery() {
        // Initialize with first fallback server
        current_server = fallback_servers[0];
    }
    
    // Main method - gets current API server
    String getApiServer() {
        // Try discovery if it's time
        if (shouldTryDiscovery()) {
            String discovered = attemptDiscovery();
            if (discovered.length() > 0) {
                Serial.println("📡 Discovery successful: " + discovered);
                current_server = discovered;
                last_discovery_attempt = millis();
            } else {
                Serial.println("⚠️ Discovery failed, using current: " + current_server);
                last_discovery_attempt = millis(); // Don't retry immediately
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
        
        for (int i = 0; i < 2; i++) {
            Serial.printf("   Trying discovery URL %d: %s\n", i+1, discovery_urls[i]);
            
            String result = fetchDiscoveryConfig(discovery_urls[i]);
            if (result.length() > 0) {
                Serial.println("   ✅ Discovery successful from URL " + String(i+1));
                return result;
            }
            
            delay(1000); // Wait between attempts
        }
        
        Serial.println("   ❌ All discovery URLs failed");
        return "";
    }
    
    String fetchDiscoveryConfig(const char* url) {
        HTTPClient http;
        WiFiClient client;
        
        http.begin(client, url);
        http.setTimeout(10000); // 10 second timeout
        
        int httpCode = http.GET();
        
        if (httpCode == HTTP_CODE_OK) {
            String payload = http.getString();
            http.end();
            
            // Parse JSON and extract server
            return parseDiscoveryResponse(payload);
        } else {
            Serial.printf("   HTTP error: %d\n", httpCode);
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