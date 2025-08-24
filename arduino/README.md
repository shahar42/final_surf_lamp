# Surf Lamp Arduino Firmware

This directory contains the firmware for the ESP32 microcontroller that powers the Surf Lamp.

## Overview

The firmware is written in C++ using the Arduino framework. It handles connecting the device to Wi-Fi, receiving surf data from the backend server, and visualizing that data on three addressable LED strips. It also includes a user-friendly web portal for initial Wi-Fi setup.

## Features

*   **Web-Based Wi-Fi Configuration:** If the device can't connect to a known network, it automatically starts a Wi-Fi Access Point. The user can then connect to this network and use a simple web page to enter their Wi-Fi credentials.
*   **Dynamic Server Discovery:** The firmware doesn't rely on a hardcoded server address. It dynamically discovers the location of the backend API by fetching a configuration file from GitHub Pages.
*   **Rich LED Visualization:** Uses the FastLED library to display multiple data points simultaneously:
    *   **Wave Height:** Visualized on the right LED strip.
    *   **Wave Period:** Visualized on the left LED strip.
    *   **Wind Speed:** Visualized on the center LED strip.
    *   **Wind Direction:** Indicated by a color-coded LED at the top of the center strip.
*   **Local API for Control and Debugging:** The device runs a local web server that exposes several endpoints for receiving data and for diagnostics.

## Hardware Requirements

*   **Microcontroller:** ESP32
*   **LEDs:** WS2812B Addressable LEDs (or compatible)
*   **Button:** A momentary push button connected to GPIO pin 0 for manual actions.

## Software Dependencies (Arduino Libraries)

*   `WiFi`
*   `WebServer`
*   `Preferences` (for saving Wi-Fi credentials)
*   `ArduinoJson`
*   `FastLED`

## Configuration

### 1. Unique Device ID

Before flashing, you **must** set a unique ID for each device by changing the following line in `fixed_surf_lamp.ino`:

```cpp
const int ARDUINO_ID = 4433;  // ✨ CHANGE THIS for each Arduino device
```

This ID must match the `arduino_id` you used when registering the lamp in the web dashboard.

### 2. Wi-Fi Setup

1.  The first time you power on the device, it will fail to connect to Wi-Fi and will create its own network with the SSID `SurfLamp-Setup`.
2.  Connect to this network with your phone or computer. The password is `surf123456`.
3.  A captive portal should open automatically, or you can navigate to `http://192.168.4.1` in your browser.
4.  Enter your home Wi-Fi SSID and password and click "Connect".
5.  The device will save the credentials and reboot, connecting to your network automatically from now on.

## Device API

The firmware runs a local web server that exposes the following endpoints:

*   `POST /api/update`: The main endpoint used by the backend processor to push new surf data to the lamp.
*   `GET /api/status`: Returns a JSON object with the device's current status, including Wi-Fi signal strength, uptime, and the last data received.
*   `GET /api/info`: Returns detailed information about the ESP32 chip and firmware.
*   `GET /api/led-test`: Triggers a visual test sequence on all LED strips.

## Data Payload

The device expects to receive a JSON payload at the `/api/update` endpoint with the following structure. **Note:** For efficiency, certain values are sent as integers.

```json
{
  "wave_height_cm": 125,      // Wave height in centimeters (integer)
  "wave_period_s": 8.5,
  "wind_speed_mps": 5,         // Wind speed in m/s (integer)
  "wind_direction_deg": 270,
  "wave_threshold_cm": 100     // User's alert threshold in cm (integer)
}
```
