# Refactored Codebase Modules

## 1. `maayans_lamp.ino` (Main Orchestrator)
The entry point of the application. It instantiates all the module objects, orchestrates the `setup()` sequence (initializing LEDs, WiFi, and Server), and manages the main `loop()`. It acts as the "glue" code, calling the `update()` or `loop()` methods of each module and coordinating the data flow between them (e.g., fetching data via WebHandler and passing it to LedController).

## 2. `Config.h` (Configuration & Constants)
A single header file containing all the compile-time configuration. This includes hardware pin definitions (`LED_PIN`, `BUTTON_PIN`), LED strip mappings (start/end indices for Wave, Wind, Period strips), physical physics constants (max wave height, wind speed), and system timeouts. It replaces the scattered `#define` macros from the original file, providing a centralized "settings" file.

## 3. `SurfState.h` (Shared Data Types)
Defines the shared data structures used across multiple modules to avoid circular dependencies. Primarily, it defines the `SurfData` struct (which holds the current wave height, wind speed, etc.) and configuration helper structs like `WaveConfig` and `LEDMappingConfig`. This allows the `WebServerHandler` to write data and the `LedController` to read it in a type-safe manner.

## 4. `LedController` (Visuals & Animations)
Encapsulates all `FastLED` logic. It owns the `CRGB leds[]` array and handles the translation of surf data into visual patterns. It contains the logic for the different strips (Wave Height, Period, Wind Speed), handles the blinking animations for threshold alerts, and manages the status LED colors (blue for connecting, green for fresh data).

## 5. `WiFiHandler` (Network Connectivity)
Manages the `WiFiManager` lifecycle and connection logic. It handles the "captive portal" for initial setup, performs the exponential backoff retries if the router reboots, and runs connection diagnostics (checking signal strength, SSID existence). It isolates the messy WiFi event callbacks and state machine from the main application logic.

## 6. `WebServerHandler` (API & Data Fetching)
Handles both the "Server" and "Client" network roles. As a server, it provides the HTTP endpoints (like `/api/status`, `/api/update`) for diagnostics and receiving push updates. As a client, it handles the logic for fetching surf data from the remote API using `HTTPClient`, parsing the JSON response, and updating the shared `SurfData` state.
