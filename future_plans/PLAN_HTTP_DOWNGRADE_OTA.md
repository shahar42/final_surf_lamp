# HTTP Downgrade & OTA Plan (Flash Optimization)

**Goal:** Reduce firmware size by ~600KB to fit OTA functionality into the standard 4MB partition.
**Method:** Replace `WiFiClientSecure` (HTTPS/TLS) with standard `WiFiClient` (HTTP) for surf data fetching.
**Constraint:** Must ensure backward compatibility and handle Render's "Force HTTPS" behavior.

---

## 🏗️ Phase 1: Server-Side Preparation (The Proxy)
*The main Render service likely forces HTTPS. We need a "dumb pipe" entry point for HTTP lamps.*

### Option A: Disable Force HTTPS (Simplest)
1.  Go to Render Dashboard -> Settings.
2.  Find "Force HTTPS" or "HTTP -> HTTPS Redirect".
3.  **Disable it.**
    *   *Risk:* Your Admin Dashboard (`/admin`) is now accessible over HTTP. You must ensure your Flask app handles this by forcing HTTPS for `/admin` routes specifically in code (`@before_request`).

### Option B: The "Lightweight Proxy" (Recommended for Security)
1.  Deploy a tiny **Go/Node.js** service on Render (e.g., `surf-lamp-proxy`).
2.  **Config:**
    *   Exposes Port 80.
    *   **No SSL:** Intentionally uses `http://`.
3.  **Logic:**
    *   Receives `GET /api/v3/{id}/data`.
    *   Forwards request to `https://final-surf-lamp-web.onrender.com/...` (using its own SSL cert).
    *   Returns binary payload to lamp.
4.  **Cost:** Minimal (Starter service $7/mo).

---

## ✂️ Phase 2: Firmware Diet (Code Changes)

### 1. Header Replacements (`lamp_template.ino`, `WebServerHandler.h`)
**Remove:**
```cpp
#include <WiFiClientSecure.h>
```
**Add:**
```cpp
#include <WiFiClient.h>
```

### 2. Global Object Update (`WebServerHandler.cpp`)
**Change:**
```cpp
WiFiClientSecure globalHttpsClient;
```
**To:**
```cpp
WiFiClient globalHttpClient;
```

### 3. Fetch Logic Update (`WebServerHandler.cpp`)
**In `fetchSurfDataFromServer`:**
1.  **URL:** Change `"https://"` to `"http://"`.
2.  **Client:** Use `WiFiClient` instead of `WiFiClientSecure`.
3.  **Remove:** `client.setInsecure()` (It doesn't exist for standard HTTP).

### 4. Discovery Update (`ServerDiscovery.h`)
Ensure the discovery logic returns the **HTTP** URL (or the Proxy URL), not the HTTPS one.

---

## 📦 Phase 3: Partition Scheme & OTA

### 1. Partition Selection
In `platformio.ini` or Arduino IDE:
*   **Old:** "Huge APP (3MB No OTA)"
*   **New:** "Default 4MB with SPIFFS" (1.2MB App / 1.5MB SPIFFS / 1.2MB OTA)

### 2. Add OTA Library
**In `lamp_template.ino`:**
```cpp
#include <ArduinoOTA.h>

void setup() {
    // ... WiFi Setup ...
    ArduinoOTA.setHostname("SurfLamp-New");
    ArduinoOTA.onStart([]() { Serial.println("Start OTA"); });
    ArduinoOTA.onEnd([]() { Serial.println("\nEnd"); });
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
    });
    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("Error[%u]: ", error);
    });
    ArduinoOTA.begin();
}

void loop() {
    ArduinoOTA.handle(); // Critical: Needs to run frequently
    // ... rest of loop ...
}
```

---

## 🛡️ Security Note
Switching to HTTP removes TLS encryption.
*   **Risk:** Man-in-the-Middle (MitM) attacks can sniff the 26-byte payload (Wave Height).
*   **Impact:** Low. Surf data is public.
*   **Mitigation (Future):** Implement AES-128 encryption on the payload itself. The proxy encrypts it, the lamp decrypts it. This is ~5KB of code vs 600KB for TLS.

---

## 📅 Execution Steps
1.  **Test:** Create a `test_http_branch` in git.
2.  **Refactor:** Apply code changes to remove SSL.
3.  **Compile:** Verify binary size drops < 1.2MB.
4.  **Deploy Proxy:** Set up the HTTP entry point.
5.  **Flash:** Test on a physical ESP32.
6.  **Verify OTA:** Perform an OTA update to confirm it works.
