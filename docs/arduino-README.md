# Surf Lamp Arduino Firmware

This directory contains the firmware for the ESP32 microcontroller that powers the Surf Lamp. This guide provides all the necessary information to set up the hardware, configure the development environment, and flash the firmware.

## 🏗️ Project Architecture

The firmware is written in C++ using the Arduino framework. It is designed to be resilient and user-friendly, with the following key features:

*   **Web-Based Wi-Fi Configuration:** On first boot or after a connection failure, the device creates a "SurfLamp-Setup" Wi-Fi Access Point. A captive portal allows the user to easily configure their network credentials without needing to re-flash the device.
*   **Dynamic Server Discovery:** The firmware is not tied to a hardcoded server IP. It fetches a configuration file from GitHub Pages to discover the correct backend API endpoint, with hardcoded fallbacks for resilience.
*   **Rich LED Visualization:** The FastLED library is used to display multiple real-time data points across three LED strips:
    *   **Right Strip:** Wave Height
    *   **Left Strip:** Wave Period
    *   **Center Strip:** Wind Speed
    *   **Top-Center LED:** Wind Direction (indicated by a color code).
*   **Local API for Control and Debugging:** The device runs a local web server with endpoints for status checks, diagnostics, and manual data fetching.

## 硬件要求

*   **Microcontroller:** ESP32 (tested with ESP32-WROOM-32).
*   **LED Strips:** WS2812B Addressable LEDs (or compatible, like SK6812).
    *   1x Strip for Wind (e.g., 12 LEDs)
    *   2x Strips for Waves (e.g., 9 LEDs each)
*   **Power Supply:** 5V power supply capable of providing enough current for all LEDs (a good rule of thumb is ~60mA per LED at full brightness).
*   **Wires and Connectors:** For connecting the components.

## 🔌 Wiring Diagram

Connect the components as follows. **Note:** It is highly recommended to power the LED strips directly from the 5V power supply, not from the ESP32's 5V pin, to avoid damaging the board. Connect the grounds together.

| Component          | ESP32 Pin |
| ------------------ | --------- |
| **Center LED Strip** (Wind) | `GPIO 4`  |
| **Right LED Strip** (Wave Height) | `GPIO 2`  |
| **Left LED Strip** (Wave Period) | `GPIO 5`  |

## 📚 Software & Library Dependencies

The firmware relies on several Arduino libraries. These can be installed via the Arduino IDE's Library Manager (`Sketch` > `Include Library` > `Manage Libraries...`).

*   `WiFi` (built-in with ESP32 core)
*   `WebServer` (built-in with ESP32 core)
*   `Preferences` (built-in with ESP32 core)
*   `ArduinoJson` by Benoit Blanchon (install version 6.x)
*   `FastLED` by Daniel Garcia

## 💻 Development Environment Setup

### Arduino IDE

1.  **Install Arduino IDE:** Download and install the latest version from the [Arduino website](https://www.arduino.cc/en/software).
2.  **Install ESP32 Board Support:**
    *   Open `File` > `Preferences`.
    *   In the "Additional Boards Manager URLs" field, add the following URL:
        ```
        https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
        ```
    *   Open `Tools` > `Board` > `Boards Manager...`.
    *   Search for "esp32" and install the package by Espressif Systems.
3.  **Select Board and Port:**
    *   Go to `Tools` > `Board` and select a generic "ESP32 Dev Module" or your specific board model.
    *   Connect your ESP32 to your computer and select the correct COM/Serial port under `Tools` > `Port`.
4.  **Install Libraries:** Install the libraries listed in the "Software & Library Dependencies" section using the Library Manager.

## ⚙️ Configuration

Before flashing, you **must** set a unique ID for each device. This ID is used to associate the physical lamp with a user's account in the database.

1.  Open `arduinomain_lamp.ino` in the Arduino IDE.
2.  Find the following line (around line 28):
    ```cpp
    const int ARDUINO_ID = 4433;  // ✨ CHANGE THIS for each Arduino device
    ```
3.  Change `4433` to a unique integer ID. This ID must match the `arduino_id` you used when registering the lamp in the web dashboard.

## 🚀 Compilation and Flashing

1.  With the `arduinomain_lamp.ino` sketch open in the Arduino IDE, click the "Verify" button (checkmark icon) to compile the code. This will check for any errors.
2.  If compilation is successful, click the "Upload" button (right arrow icon) to flash the firmware to the ESP32.
3.  Open the Serial Monitor (`Tools` > `Serial Monitor`) and set the baud rate to `115200` to view the device logs.

## 📶 Wi-Fi Setup

1.  The first time you power on the device, it will fail to connect to a known Wi-Fi network and will create its own network with the SSID `SurfLamp-Setup`.
2.  Connect to this network with your phone or computer. The password is `surf123456`.
3.  A captive portal should open automatically. If not, open a web browser and navigate to `http://192.168.4.1`.
4.  Enter your home Wi-Fi SSID and password and click "Connect to WiFi".
5.  The device will save the credentials to its non-volatile memory, reboot, and automatically connect to your network.

## 📡 Device API

The firmware runs a local web server that exposes the following endpoints, which are useful for debugging and integration:

*   `GET /api/status`: Returns a JSON object with the device's current status, including Wi-Fi signal strength, uptime, free memory, and the last data received.
*   `GET /api/info`: Returns detailed information about the ESP32 chip, firmware version, and configured LED strips.
*   `GET /api/led-test`: Triggers a visual test sequence on all LED strips to confirm they are working correctly.
*   `GET /api/fetch`: Manually triggers a request to the backend server to fetch the latest surf data.
*   `GET /api/discovery-test`: Forces a server discovery attempt and returns the server that was found.

### Data Payload

The device receives data from the backend via a `GET` request to `/api/arduino/<arduino_id>/data`. The expected JSON payload from the server is:

```json
{
  "wave_height_cm": 125,
  "wave_period_s": 8.5,
  "wind_speed_mps": 5,
  "wind_direction_deg": 270,
  "wave_threshold_cm": 100,
  "wind_speed_threshold_knots": 15,
  "led_theme": "day"
}
```

## 🔧 Troubleshooting

*   **Problem: Can't connect to "SurfLamp-Setup" network.**
    *   **Solution:** Make sure the ESP32 is powered on. Check the serial monitor output; if it successfully connected to a previously saved network, the setup AP will not be created. You can erase the ESP32's flash to force it back into setup mode.

*   **Problem: Device is connected to Wi-Fi but LEDs are not updating.**
    *   **Solution:**
        1.  Check the serial monitor for errors when fetching data.
        2.  Ensure the `ARDUINO_ID` in the firmware matches the ID in the web dashboard.
        3.  Use the `GET /api/fetch` endpoint to manually trigger an update and check the logs.
        4.  Verify the backend server is running and accessible from the same network.

*   **Problem: LEDs show strange colors or flicker.**
    *   **Solution:**
        1.  Ensure you have a stable 5V power supply with enough current for the LEDs.
        2.  Check for a solid ground connection between the ESP32 and the LED strips' power supply.
        3.  Make sure the `DATA_PIN` definitions in the code match your wiring.