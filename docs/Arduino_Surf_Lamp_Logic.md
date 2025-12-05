# Arduino Surf Lamp Logic

This document provides a detailed reference for the Surf Lamp's device behavior, including its LED visualization system, operational states, and internal logic.

## 💡 LED System

The lamp uses three LED strips to visualize four different surf conditions simultaneously. The system is designed to be intuitive and readable at a glance.

### LED Strip Layout

*   **Right Strip (`GPIO 2`, 9 LEDs):** Displays wave height.
*   **Left Strip (`GPIO 5`, 9 LEDs):** Displays wave period.
*   **Center Strip (`GPIO 4`, 12 LEDs):** Displays wind speed and direction.

### Data-to-LED Mapping

The number of lit LEDs on each strip corresponds to the intensity of the surf condition.

*   **Wave Height (Right Strip):**
    *   **Logic:** `Number of LEDs = wave_height_cm / 25 + 1`
    *   **Example:** A wave height of 100cm (1 meter) will light up `100 / 25 + 1 = 5` LEDs on the right strip.

*   **Wave Period (Left Strip):**
    *   **Logic:** `Number of LEDs = wave_period_s`
    *   **Example:** A wave period of 8.5 seconds will light up 8 LEDs on the left strip.

*   **Wind Speed (Center Strip):**
    *   **Logic:** `Number of LEDs = wind_speed_mps * 10 / 22`
    *   **Explanation:** Wind speed is linearly scaled from 0-22 m/s to 0-10 LEDs, optimized for typical surf conditions.
    *   **Example:** A wind speed of 11 m/s will light up `11 * 10 / 22 = 5` LEDs. A wind speed of 22 m/s will light up all 10 available LEDs.

### 🧭 Wind Direction Colors

The topmost LED of the center strip (`LED #11`) indicates the wind direction using a standard color code. This provides crucial information about whether the wind is onshore, offshore, or cross-shore.

| Direction        | Degrees             | Color  | Meaning for Surfing (example) |
| ---------------- | ------------------- | ------ | ----------------------------- |
| **North**        | 315° - 44°          | Green  | Cross-shore                   |
| **East**         | 45° - 134°          | Yellow | Offshore (good conditions)    |
| **South**        | 135° - 224°         | Red    | Cross-shore                   |
| **West**         | 225° - 314°         | Blue   | Onshore (choppy conditions)   |

### ⚠️ Threshold Alerts (Blinking)

When surf conditions exceed the user-defined thresholds, the corresponding LED strip will start to pulse smoothly to draw attention.

*   **Wave Height Alert:**
    *   **Trigger:** `wave_height_cm >= wave_threshold_cm`
    *   **Behavior:** The right LED strip (wave height) will blink in a theme-based color.

*   **Wind Speed Alert:**
    *   **Trigger:** `wind_speed_knots >= wind_speed_threshold_knots`
    *   **Behavior:** The center LED strip (wind speed) will blink in a theme-based color.

### ✨ Status LED

The first LED of the center strip (`LED #0`) serves as a status indicator, providing at-a-glance information about the device's state.

| Color          | Blinking Pattern | Meaning                                       |
| -------------- | ---------------- | --------------------------------------------- |
| **Blue**       | Slow Blink       | Connecting to Wi-Fi.                          |
| **Green**      | Slow Blink       | Connected to Wi-Fi and has received fresh data. |
| **Red**        | Slow Blink       | Wi-Fi connection failed.                      |
| **Yellow**     | Slow Blink       | In Wi-Fi configuration mode (Access Point is active). |
| **Blue (Solid)** | Solid            | No recent data received (older than 30 minutes). |

## 📶 WiFi Configuration Process

If the device cannot connect to a saved Wi-Fi network, it enters configuration mode.

1.  **Access Point Creation:** The device creates a Wi-Fi network with the SSID `SurfLamp-Setup` and the password `surf123456`.
2.  **Connect:** The user connects a phone or computer to this network.
3.  **Captive Portal:** A captive portal should automatically open in the user's browser. If not, they can manually navigate to `http://192.168.4.1`.
4.  **Enter Credentials:** The user enters their home Wi-Fi SSID and password into the web form.
5.  **Save and Reboot:** The device saves the credentials to its non-volatile memory and reboots.
6.  **Connection:** The device then attempts to connect to the user-provided network.

## 📡 Device API Behavior

The device hosts a local API for diagnostics and control.

*   `GET /api/status`
    *   **Behavior:** Returns a detailed JSON object with the device's current operational status.
    *   **Example Response:**
        ```json
        {
          "arduino_id": 4433,
          "status": "online",
          "wifi_connected": true,
          "ip_address": "192.168.1.100",
          "ssid": "MyHomeWiFi",
          "signal_strength": -55,
          "uptime_ms": 1200000,
          "free_heap": 150000,
          "last_surf_data": {
            "received": true,
            "wave_height_m": 1.25,
            "wave_period_s": 8.5,
            "wind_speed_mps": 5,
            "wind_direction_deg": 270,
            "last_update_ms": 60000
          }
        }
        ```

*   `GET /api/info`
    *   **Behavior:** Returns static information about the device hardware and firmware.
    *   **Example Response:**
        ```json
        {
          "device_name": "Surf Lamp",
          "arduino_id": 4433,
          "model": "ESP32-D0WD-V3",
          "firmware_version": "1.0.0",
          "led_strips": {
            "center": 12,
            "right": 9,
            "left": 9
          }
        }
        ```

*   `GET /api/led-test`
    *   **Behavior:** Initiates a sequence that tests all LED strips with various colors and patterns. Returns a confirmation message.

*   `GET /api/fetch`
    *   **Behavior:** Forces the device to immediately attempt a data fetch from the backend server. Useful for debugging.

*   `GET /api/discovery-test`
    *   **Behavior:** Forces the device to run its server discovery protocol and returns the server URL it found.

## 🚨 Error States and Recovery Procedures

The firmware is designed to be self-recovering from common error conditions.

*   **Error: Wi-Fi Connection Failed**
    *   **Detection:** `WiFi.status()` is not `WL_CONNECTED`.
    *   **Indication:** The status LED blinks **Red**.
    *   **Recovery:** The device will automatically attempt to reconnect to the last known Wi-Fi network every 30 seconds.
    *   **User Action:** If reconnection fails repeatedly, the user can power cycle the device. If it still fails, it will enter configuration mode.

*   **Error: Failed to Fetch Surf Data**
    *   **Detection:** The HTTP request to the backend server returns an error code or times out.
    *   **Indication:** The serial monitor will print an error message (e.g., `❌ HTTP error fetching surf data`). The device will continue to display the last known data.
    *   **Recovery:** The device will automatically retry fetching data at the next scheduled interval (every 13 minutes).
    *   **User Action:** The user can manually trigger a fetch via the `/api/fetch` endpoint to test the connection.

*   **Error: Failed to Parse JSON Data**
    *   **Detection:** The `ArduinoJson` library fails to parse the HTTP response from the server.
    *   **Indication:** The serial monitor will print a `JSON parsing failed` error.
    *   **Recovery:** The device will ignore the invalid data and wait for the next fetch interval.

*   **Error: Server Discovery Fails**
    *   **Detection:** The device cannot fetch or parse the `config.json` file from any of the discovery URLs.
    *   **Indication:** The serial monitor will print `Discovery failed`.
    *   **Recovery:** The device will fall back to using its hardcoded list of known servers, starting with `final-surf-lamp.onrender.com`.
