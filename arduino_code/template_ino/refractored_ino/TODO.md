# Refactoring To-Do List

## Phase 1: Foundation (Shared Types & Config)
- [x] Create `Config.h` - Move all `#define` constants, configuration macros, and pin definitions here.
- [x] Create `SurfState.h` - Move `SurfData` struct, `WaveConfig` struct, and `LEDMappingConfig` struct here.

## Phase 2: Network & Web
- [x] Create `WiFiHandler.h` and `WiFiHandler.cpp` - Encapsulate WiFiManager, connection logic, and diagnostics.
- [x] Create `WebServerHandler.h` and `WebServerHandler.cpp` - Encapsulate `WebServer`, API endpoints, and JSON parsing.

## Phase 3: Visuals
- [x] Create `LedController.h` and `LedController.cpp` - Encapsulate FastLED setup, `CRGB` array, animations, and theme logic.

## Phase 4: Integration
- [x] Update `maayans_lamp.ino` - Strip out moved code, include new headers, instantiate classes, and wire them together in `setup()` and `loop()`.
- [x] Verify compilation and dependencies.
