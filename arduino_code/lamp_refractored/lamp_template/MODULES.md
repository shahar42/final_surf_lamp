# Surf Lamp Template - Module Architecture

**Version**: 3.0.0
**Created**: 2025-12-20
**Architecture**: Modular template following Scott Meyers principles

---

## Module Breakdown

| Module | Lines | Purpose | User Edits? |
|--------|-------|---------|-------------|
| **Config.h** | 261 | Lamp configuration & compile-time validation | ✅ YES |
| **SurfState.h** | 75 | Data structures (SurfData, etc.) | ❌ NO |
| **Themes.h/cpp** | 136 | Color theme management | ❌ NO |
| **LedController.h/cpp** | 696 | LED display & animations | ❌ NO |
| **WebServerHandler.h/cpp** | 469 | HTTP endpoints | ❌ NO |
| **WiFiHandler.h/cpp** | 463 | WiFi connection & diagnostics | ❌ NO |
| **lamp_template.ino** | 191 | Main orchestration | ❌ NO |
| **README.md** | 422 | Usage documentation | ❌ NO |
| **Total** | **2713** | **Modular template** | **1 file only** |

**Reusable modules** (copied as-is):
- animation.h (6.8KB) - Sunset animations
- ServerDiscovery.h (5.0KB) - API discovery
- WiFiFingerprinting.h (5.0KB) - Location detection

---

## Design Principles Applied

### Scott Meyers' "Effective C++"

1. **Item 18: Easy to use correctly, hard to use incorrectly**
   - Config.h has clear "DO NOT EDIT" boundary
   - Auto-calculated values prevent math errors
   - Compile-time validation with `static_assert`

2. **Item 23: Prefer non-member non-friend functions**
   - LedController uses free functions
   - Better encapsulation than class methods
   - Clear dependencies via parameters

3. **Single Responsibility Principle**
   - Each module has exactly one job
   - Config: Configuration only
   - LedController: LED manipulation only
   - WebServerHandler: HTTP only
   - WiFiHandler: WiFi only

4. **Minimize Compilation Dependencies**
   - Headers include only what they need
   - Forward declarations where possible
   - No circular dependencies

---

## Module Responsibilities

### Config.h (User Configuration)

**Lines**: 261 (78 user-editable, 183 auto-calculated + validation)

**Responsibilities**:
- Device identity (ARDUINO_ID)
- Hardware setup (LED_PIN, TOTAL_LEDS, LED_TYPE)
- LED strip mapping (BOTTOM/TOP indices for 3 strips)
- Surf data scaling (MAX_WAVE_HEIGHT, MAX_WIND_SPEED)
- Wave animation parameters (brightness, speed, length)
- Auto-calculation of derived values (directions, lengths, indices)
- Compile-time validation (static_assert checks)
- Configuration structs (WaveConfig, LEDMappingConfig)

**Why users edit this**:
- ONLY file that changes between lamp configurations
- Clear boundary between editable and generated code
- Self-documenting parameter names
- Compilation fails if configuration is invalid

### SurfState.h (Data Structures)

**Lines**: 75

**Responsibilities**:
- SurfData struct definition (surf conditions & user preferences)
- Unit conversion helpers (meters ↔ cm)
- Operating mode flags (quietHours, offHours, sunset)
- State tracking (dataReceived, needsDisplayUpdate)

**Design**:
- Struct over class (simple POD, no hidden behavior)
- Const helpers prevent accidental modification
- Inline conversions = zero runtime cost
- Clear unit documentation (meters vs cm, m/s vs knots)

### Themes.h/cpp (Color Management)

**Lines**: 63 (header) + 73 (implementation) = 136

**Responsibilities**:
- ThemeColors struct (wave, wind, period colors)
- getThemeColors() function (5 themes + legacy support)
- Convenience accessors (getWaveHeightColor, etc.)
- Color maps (legacy, preserved for future features)

**Themes**:
1. classic_surf - Blue waves, white wind, yellow period
2. vibrant_mix - Purple waves, green wind, blue period
3. tropical_paradise - Green waves, cyan wind, magenta period
4. ocean_sunset - Blue waves, orange wind, pink period
5. electric_vibes - Cyan waves, yellow wind, purple period

**Design**:
- Pure functions (no global state, no side effects)
- Const references prevent accidental modification
- Inline accessors = zero overhead (eliminated by compiler)
- Easy to extend (add themes in one place)

### LedController.h/cpp (LED Display)

**Lines**: 191 (header) + 505 (implementation) = 696

**Responsibilities**:
- LED initialization (FastLED setup)
- LED testing (performLEDTest, testAllStatusLEDStates)
- Status patterns (showAPMode, showTryingToConnect, etc.)
- Status LED blinking (blinkGreenLED, blinkRedLED, etc.)
- Data display (updateWaveHeightLEDs, updateWindSpeedLEDs, etc.)
- Wind direction indicator (setWindDirection)
- Threshold animations (updateBlinkingWaveHeightLEDs, etc.)
- High-level display updates (updateSurfDisplay, updateBlinkingAnimation)

**Design**:
- Non-member functions (Scott Meyers Item 23)
- Each function has single responsibility
- Direction handling abstracted (users don't see FORWARD/REVERSE)
- Bounds checking prevents buffer overruns (constrain())
- File-static variables hide implementation details

### WebServerHandler.h/cpp (HTTP Endpoints)

**Lines**: 118 (header) + 351 (implementation) = 469

**Responsibilities**:
- HTTP server setup (setupHTTPEndpoints)
- Data endpoints (handleSurfDataUpdate, handleManualFetchRequest)
- Status endpoints (handleStatusRequest, handleDeviceInfoRequest)
- Test endpoints (handleTestRequest, handleLEDTestRequest)
- Diagnostics (handleWiFiDiagnostics, handleDiscoveryTest)
- Data processing (processSurfData, fetchSurfDataFromServer)

**Endpoints**:
- POST /api/update - Receive surf data from backend
- GET /api/status - Full device status
- GET /api/test - Connectivity test
- GET /api/led-test - LED test sequence
- GET /api/info - Hardware specs
- GET /api/fetch - Manual surf data fetch
- GET /api/wifi-diagnostics - WiFi diagnostics
- GET /api/discovery-test - API discovery test

**Design**:
- Dependency injection (WebServer passed by reference)
- Separation: HTTP handling vs data processing
- Handlers match WebServer callback signature
- Easy to add endpoints without modifying other code

### WiFiHandler.h/cpp (WiFi Management)

**Lines**: 112 (header) + 351 (implementation) = 463

**Responsibilities**:
- WiFi connection setup (setupWiFi)
- Scenario-based timeout strategy (FIRST_SETUP, ROUTER_REBOOT, etc.)
- WiFi health monitoring (handleWiFiHealth)
- WiFi reset button (handleWiFiResetButton)
- Diagnostics (diagnoseSSID, getDisconnectReasonText)
- Event handlers (WiFiEvent, configModeCallback, etc.)

**WiFi Scenarios**:
1. FIRST_SETUP - 10 minutes for new device configuration
2. ROUTER_REBOOT - Exponential backoff (30s, 60s, 120s, 240s, 300s max)
3. HAS_CREDENTIALS - Standard retries with portal
4. NEW_LOCATION - Forces reconfiguration

**Design**:
- Single entry point: setupWiFi()
- Pure functions for diagnostics (testable)
- State exposure limited to what's needed for display
- Event handlers encapsulated

### lamp_template.ino (Main Orchestration)

**Lines**: 191

**Responsibilities**:
- Global instances (WebServer, WiFiManager, etc.)
- Global state definitions (lastSurfData, waveConfig, ledMapping)
- setup() - Hardware init, WiFi connection, HTTP server setup
- loop() - WiFi health, HTTP handling, data fetch, display updates, animations

**Design**:
- Pure orchestration (no business logic)
- Clear control flow (setup → loop)
- All complexity delegated to modules
- Identical across all lamps (only Config.h differs)

---

## Data Flow

```
User edits Config.h
       ↓
Compilation validates config (static_assert)
       ↓
setup() initializes all modules
       ↓
loop() orchestrates:
       ├─→ WiFiHandler (connection health)
       ├─→ WebServerHandler (HTTP requests)
       ├─→ fetchSurfDataFromServer() → processSurfData()
       │                                      ↓
       │                              Updates lastSurfData
       │                                      ↓
       ├─→ updateSurfDisplay() ←─── Reads lastSurfData
       ├─→ updateBlinkingAnimation() ←─── Reads lastSurfData
       └─→ updateStatusLED() ←─── Reads lastSurfData
```

**Key Properties**:
- Config.h: Read by all modules (compile-time constants)
- SurfState: Central mutable state (extern declared)
- No circular dependencies
- Clear ownership (SurfData defined in .ino)

---

## Error Prevention

### Compile-Time Validation

```cpp
// From Config.h
static_assert(TOTAL_LEDS > 0, "TOTAL_LEDS must be positive");
static_assert(WAVE_HEIGHT_LENGTH > 0, "Wave height strip empty");
static_assert(WIND_SPEED_LENGTH >= 3, "Wind strip needs min 3 LEDs");
static_assert(STATUS_LED_INDEX < TOTAL_LEDS, "Status LED out of range");
```

**Benefits**:
- Catches configuration errors before upload
- Clear error messages guide users
- Impossible to compile invalid configuration

### Runtime Protection

```cpp
// From LedController.cpp
void updateWaveHeightLEDs(int numActiveLeds, CHSV color) {
    numActiveLeds = constrain(numActiveLeds, 0, WAVE_HEIGHT_LENGTH);
    // Prevents buffer overruns
}
```

**Benefits**:
- Graceful handling of unexpected values
- No crashes from out-of-bounds access
- Defensive programming

---

## Template Usage Workflow

### Creating New Lamp

1. **Copy template** → `cp -r lamp_template bens_lamp`
2. **Edit Config.h** → Change ARDUINO_ID, TOTAL_LEDS, LED indices
3. **Rename .ino** → `mv lamp_template.ino bens_lamp.ino`
4. **Compile** → Arduino IDE automatically includes all files
5. **Upload** → Done in < 10 minutes

### Updating Existing Lamp

1. **Update modules** → Copy new .h/.cpp files to lamp directory
2. **Keep Config.h** → Lamp-specific configuration unchanged
3. **Recompile** → Benefits from bug fixes and new features

---

## Advantages Summary

### For Lamp Creators
✅ Edit ONE file only (Config.h)
✅ Clear parameter names with units
✅ Compile catches configuration errors
✅ Can't break reusable code
✅ 10-minute lamp creation time

### For Maintainers
✅ Fix bugs once → all lamps benefit
✅ Add features once → all lamps get them
✅ Each module < 700 lines
✅ Clear responsibility per file
✅ Testable components

### Performance
✅ Zero overhead vs monolithic
✅ Same machine code generated
✅ Inline helpers eliminated by compiler
✅ Const references = no copies
✅ Static asserts = zero runtime cost

---

## Comparison: Monolithic vs Modular

| Aspect | Monolithic v2.0 | Modular v3.0 |
|--------|----------------|--------------|
| **File count** | 1 file | 15 files |
| **Total lines** | 1634 lines | 2713 lines |
| **User edits** | Lines 1-78 | Config.h only |
| **Reusability** | Copy entire file | Copy template, edit config |
| **Bug fixes** | Per-lamp | Once for all |
| **New features** | Per-lamp | Once for all |
| **Compile-time validation** | None | Static asserts |
| **Module boundaries** | None | Clear separation |
| **Time to create new lamp** | ~30 min (copy + edit) | ~10 min (config only) |
| **Risk of breaking code** | High | Zero |

---

## Future Enhancements

### Easy to Add
- New themes (Themes.cpp)
- New HTTP endpoints (WebServerHandler.cpp)
- New LED patterns (LedController.cpp)
- New WiFi diagnostics (WiFiHandler.cpp)

### Requires Planning
- Support for > 3 strips (would need Config.h redesign)
- Multiple lamps per Arduino (would need SurfState redesign)
- Non-linear LED mappings (would need LedController redesign)

---

## Credits

**Architecture**: Based on Scott Meyers' "Effective C++" principles
**Created**: 2025-12-20
**Authors**: Shahar & Claude
**Version**: 3.0.0

**Original Monolithic Code**: 1634 lines (Maayan's lamp)
**Modular Template**: 2713 lines (reusable across all lamps)
**Net Benefit**: One-time 66% increase, infinite reusability
