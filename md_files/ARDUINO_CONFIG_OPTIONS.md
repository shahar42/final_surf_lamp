# Arduino Dynamic Configuration System

## Overview

This document outlines options for implementing a dynamic configuration system that allows Arduino lamps to inherit settings from the server without requiring firmware reflashing.

---

## Current State

**What's Already Dynamic**:
- API server address (via `ServerDiscovery.h` + GitHub-hosted `config.json`)
- User preferences (thresholds, color themes) fetched with surf data every 13 minutes

**What's Currently Hardcoded**:
- LED pin assignments
- LEDs per strip count
- Polling intervals (13 minutes)
- Timeout values
- Brightness levels
- Feature flags (quiet hours, alerts, etc.)

---

## Configuration Options

### Option 1: Simple Boot-Time Fetch ⭐ **RECOMMENDED TO START**

**Architecture**:
```
Arduino Boot → WiFi Connect → ServerDiscovery → Fetch /api/lamp-config → Initialize Hardware
```

**API Endpoint**: `GET /api/lamp-config?arduino_id=LAMP_001`

**Response Structure**:
```json
{
  "arduino_id": "LAMP_001",
  "config_version": "1.2.3",
  "user_preferences": {
    "location": "Herzliya, Israel",
    "wave_threshold_m": 1.2,
    "wind_threshold_knots": 10,
    "color_theme": "ocean_breeze",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00"
  },
  "hardware_config": {
    "led_strip_right_pin": 25,
    "led_strip_left_pin": 26,
    "led_strip_center_pin": 27,
    "leds_per_strip": 10,
    "brightness": 128,
    "led_type": "WS2812B"
  },
  "timing_config": {
    "data_poll_interval_minutes": 13,
    "config_refresh_hours": 24,
    "wifi_reconnect_delay_seconds": 30,
    "api_timeout_seconds": 10
  },
  "feature_flags": {
    "enable_threshold_alerts": true,
    "enable_quiet_hours": true,
    "enable_wind_direction": true,
    "enable_web_server": true
  },
  "server_endpoints": {
    "data_endpoint": "/api/lamp-data",
    "config_endpoint": "/api/lamp-config",
    "status_report_endpoint": "/api/lamp-status"
  }
}
```

**Pros**:
- Simple implementation
- Fresh config every reboot
- Server-side config versioning and rollback
- Can fix bugs without reflashing firmware
- Leverages existing ServerDiscovery pattern

**Cons**:
- Requires network connectivity on boot (already needed)
- No offline operation if server is down
- Slightly longer boot time (~2-3 seconds)

**Fallback Strategy**:
```cpp
if (config fetch fails) {
    use hardcoded defaults in firmware
    continue normal operation
    retry config fetch on next boot
}
```

---

### Option 2: NVS-Cached Config with Periodic Refresh

**Architecture**:
```
Boot → Load from NVS (instant) → WiFi Connect → Fetch Config → Update NVS if changed
```

**Flow**:
1. Read cached config from ESP32 Non-Volatile Storage (NVS)
2. Use cached config immediately (fast boot)
3. Connect to WiFi in background
4. Fetch fresh config from server
5. Compare versions, update NVS only if changed
6. Apply new config without rebooting

**Pros**:
- Works offline (uses cached config)
- Fast boot time (<1 second)
- Only updates when config actually changes
- Survives power cycles and network outages
- Graceful degradation

**Cons**:
- More complex implementation (NVS read/write logic)
- Stale config if offline for extended periods
- Need to handle NVS corruption/wear leveling
- Requires config versioning system

**Storage Requirements**:
- JSON config: ~1-2KB
- ESP32 NVS: 512KB available (plenty of space)

---

### Option 3: Hybrid Approach (Maximum Resilience)

**Architecture**:
```
Boot → Check NVS → Load Cached → WiFi Connect → Fetch Fresh → Compare → Update NVS
                                                              ↓
                                              Hardcoded Defaults (fallback)
```

**Boot Logic**:
```cpp
if (NVS has config) {
    loadConfigFromNVS();           // Use cached immediately
    if (WiFi.connect()) {
        fetchConfigFromServer();
        if (config version changed) {
            applyNewConfig();       // Hot reload
            saveToNVS();
        }
    }
} else {
    // First boot or NVS corrupt
    useHardcodedDefaults();
    if (WiFi.connect()) {
        fetchConfigFromServer();
        saveToNVS();
    }
}
```

**Pros**:
- Best of both worlds
- Fast boot with cached config
- Always attempts fresh config
- Multiple fallback layers (cached → defaults)
- Resilient to network and storage failures

**Cons**:
- Most complex to implement and test
- Requires careful version management
- More edge cases to handle

---

## Configuration Categories

### High Priority (Change Frequently)
Should be fetched regularly, possibly with surf data:
- User thresholds (wave height, wind speed)
- Color themes
- Quiet hours times
- Feature flags (alerts, quiet mode, wind direction)

### Medium Priority (Change Occasionally)
Loaded on boot, cached in NVS:
- Brightness levels
- Poll intervals
- Timeout values
- Server endpoints
- LED strip lengths (if user adds more LEDs)

### Low Priority (Rarely Change)
Set once during manufacturing/setup:
- Pin assignments
- LED type (WS2812B vs APA102)
- Hardware revision
- WiFi credentials (already configurable via captive portal)

---

## Proposed Implementation

### New File: `ConfigManager.h`

```cpp
#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <ArduinoJson.h>
#include <Preferences.h>

struct HardwareConfig {
    int ledStripRightPin;
    int ledStripLeftPin;
    int ledStripCenterPin;
    int ledsPerStrip;
    int brightness;
    String ledType;
};

struct TimingConfig {
    int dataPollIntervalMinutes;
    int configRefreshHours;
    int wifiReconnectDelaySeconds;
    int apiTimeoutSeconds;
};

struct UserPreferences {
    String location;
    float waveThresholdM;
    float windThresholdKnots;
    String colorTheme;
    String quietHoursStart;
    String quietHoursEnd;
};

struct FeatureFlags {
    bool enableThresholdAlerts;
    bool enableQuietHours;
    bool enableWindDirection;
    bool enableWebServer;
};

struct ServerEndpoints {
    String dataEndpoint;
    String configEndpoint;
    String statusReportEndpoint;
};

struct LampConfig {
    String arduinoId;
    String configVersion;
    HardwareConfig hardware;
    TimingConfig timing;
    UserPreferences user;
    FeatureFlags features;
    ServerEndpoints endpoints;
};

class ConfigManager {
private:
    LampConfig currentConfig;
    Preferences nvs;
    bool hasValidConfig;

    void setHardcodedDefaults();
    bool parseJsonConfig(const String& json);
    String serializeConfig();

public:
    ConfigManager();

    // Boot-time operations
    bool loadFromNVS();
    bool fetchFromServer(const String& serverUrl, const String& arduinoId);
    bool saveToNVS();

    // Runtime operations
    LampConfig& getConfig();
    bool applyConfig(const String& jsonConfig);
    bool validateConfig(const LampConfig& config);
    void printConfig();  // Debug helper

    // Getters
    String getVersion();
    bool hasConfig();

    // Factory reset
    void clearNVS();
};

#endif
```

### Integration with `arduinomain_lamp.ino`

```cpp
#include "ConfigManager.h"

ConfigManager configManager;

void setup() {
    Serial.begin(115200);
    Serial.println("Surf Lamp Starting...");

    // Try loading cached config from NVS
    if (configManager.loadFromNVS()) {
        Serial.println("Loaded config from NVS");
    } else {
        Serial.println("No cached config, using defaults");
    }

    // Connect to WiFi
    connectWiFi();

    // Fetch fresh config from server
    if (WiFi.status() == WL_CONNECTED) {
        String serverUrl = serverDiscovery.getServer();
        if (configManager.fetchFromServer(serverUrl, ARDUINO_ID)) {
            Serial.println("Fetched fresh config from server");
            configManager.saveToNVS();
        }
    }

    // Get active config
    LampConfig cfg = configManager.getConfig();

    // Initialize hardware with config values
    initLEDStrips(
        cfg.hardware.ledStripRightPin,
        cfg.hardware.ledStripLeftPin,
        cfg.hardware.ledStripCenterPin,
        cfg.hardware.ledsPerStrip
    );

    setBrightness(cfg.hardware.brightness);

    // Start services
    if (cfg.features.enableWebServer) {
        startWebServer();
    }

    // Set polling interval from config
    dataFetchInterval = cfg.timing.dataPollIntervalMinutes * 60 * 1000;

    Serial.println("Surf Lamp Ready!");
    configManager.printConfig();
}

void loop() {
    // Existing loop logic...

    // Optional: Periodic config refresh (e.g., every 24 hours)
    static unsigned long lastConfigFetch = 0;
    LampConfig cfg = configManager.getConfig();
    unsigned long configRefreshInterval = cfg.timing.configRefreshHours * 60 * 60 * 1000;

    if (millis() - lastConfigFetch > configRefreshInterval) {
        String serverUrl = serverDiscovery.getServer();
        if (configManager.fetchFromServer(serverUrl, ARDUINO_ID)) {
            configManager.saveToNVS();
            Serial.println("Config refreshed");
        }
        lastConfigFetch = millis();
    }
}
```

---

## Backend Implementation

### Database Schema Addition

Add new table `lamp_configs`:
```sql
CREATE TABLE lamp_configs (
    lamp_id INT PRIMARY KEY REFERENCES lamps(lamp_id),
    config_version VARCHAR(20) DEFAULT '1.0.0',
    hardware_config JSONB,
    timing_config JSONB,
    feature_flags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Flask Endpoint

```python
@app.route('/api/lamp-config')
def get_lamp_config():
    arduino_id = request.args.get('arduino_id')
    client_version = request.args.get('version', '0.0.0')

    # Fetch lamp and user data
    lamp = db.query(Lamp).filter_by(arduino_id=arduino_id).first()
    if not lamp:
        return jsonify({"error": "Lamp not found"}), 404

    user = lamp.user
    config = lamp.config or get_default_config()

    # Check if client has latest version
    if client_version == config.config_version:
        return '', 304  # Not Modified

    # Build config response
    response = {
        "arduino_id": arduino_id,
        "config_version": config.config_version,
        "user_preferences": {
            "location": user.location,
            "wave_threshold_m": user.wave_threshold_m,
            "wind_threshold_knots": user.wind_threshold_knots,
            "color_theme": user.theme,
            "quiet_hours_start": config.quiet_hours_start,
            "quiet_hours_end": config.quiet_hours_end
        },
        "hardware_config": config.hardware_config,
        "timing_config": config.timing_config,
        "feature_flags": config.feature_flags,
        "server_endpoints": {
            "data_endpoint": "/api/lamp-data",
            "config_endpoint": "/api/lamp-config",
            "status_report_endpoint": "/api/lamp-status"
        }
    }

    return jsonify(response)
```

---

## Configuration Versioning

### Semantic Versioning
```
MAJOR.MINOR.PATCH (e.g., 2.1.3)

MAJOR: Breaking changes (requires firmware update)
MINOR: New features (backward compatible)
PATCH: Bug fixes, threshold changes
```

### Version Comparison
```cpp
bool isNewerVersion(String current, String fetched) {
    // Parse and compare semantic versions
    // Return true if fetched > current
}
```

---

## Validation & Safety

### Config Validation Rules

```cpp
bool ConfigManager::validateConfig(const LampConfig& config) {
    // Sanity checks
    if (config.hardware.ledsPerStrip < 1 ||
        config.hardware.ledsPerStrip > 300) {
        return false;
    }

    if (config.hardware.brightness < 0 ||
        config.hardware.brightness > 255) {
        return false;
    }

    if (config.timing.dataPollIntervalMinutes < 1) {
        return false;
    }

    // Pin validation
    if (config.hardware.ledStripRightPin < 0 ||
        config.hardware.ledStripRightPin > 39) {
        return false;
    }

    // More validation rules...

    return true;
}
```

### Rollback Strategy

If bad config is applied:
1. **Arduino detects failure** (e.g., LEDs won't initialize)
2. **Reverts to previous NVS config**
3. **Reports error to server** via `/api/lamp-status`
4. **Increments failure counter**
5. **After 3 failures, uses hardcoded defaults**

---

## Testing Strategy

### Unit Tests
- Config parsing from JSON
- NVS read/write operations
- Version comparison logic
- Validation rules

### Integration Tests
- Boot with no NVS config (first run)
- Boot with cached config (offline mode)
- Boot with server available (fetch fresh)
- Config version mismatch scenarios
- Network failure during fetch
- Corrupted NVS data recovery

### User Acceptance Tests
- Change threshold via dashboard → Arduino updates within 13 minutes
- Change LED brightness → Arduino updates on next boot
- Push bad config → Arduino rejects and uses previous
- Factory reset → Arduino clears NVS and re-fetches

---

## Rollout Plan

### Phase 1: Basic Boot-Time Fetch (Week 1)
- [ ] Create `ConfigManager.h` with hardcoded defaults
- [ ] Implement simple JSON parsing
- [ ] Add `/api/lamp-config` Flask endpoint
- [ ] Test with single lamp
- [ ] Deploy to production

### Phase 2: NVS Caching (Week 2)
- [ ] Implement NVS read/write in `ConfigManager`
- [ ] Add config versioning
- [ ] Test offline operation
- [ ] Add validation rules
- [ ] Deploy to production

### Phase 3: Hot Reload (Week 3)
- [ ] Implement runtime config updates (no reboot)
- [ ] Add config change detection
- [ ] Test LED re-initialization
- [ ] Add rollback mechanism
- [ ] Deploy to production

### Phase 4: Dashboard Integration (Week 4)
- [ ] Add config editor to web dashboard
- [ ] Allow per-lamp config overrides
- [ ] Add config history/audit log
- [ ] Implement config templates
- [ ] Deploy to production

---

## Decision Checklist

Before implementing, consider:

1. **Offline Operation Priority**
   - [ ] Must work without server → Use NVS caching
   - [ ] Server always available → Simple fetch-on-boot

2. **Config Change Frequency**
   - [ ] Daily/weekly changes → Cache with periodic refresh
   - [ ] Rarely change → Boot-time fetch sufficient

3. **Bad Config Handling**
   - [ ] Validation in Arduino (reject invalid configs)
   - [ ] Trust server + physical reset button

4. **User Override Capability**
   - [ ] Physical buttons for local adjustments
   - [ ] Everything via web dashboard only

5. **Version Management**
   - [ ] Semantic versioning (MAJOR.MINOR.PATCH)
   - [ ] Timestamp-based versioning
   - [ ] Git commit hash

---

## Recommendation

**Start with Option 1 (Simple Boot-Time Fetch)**

**Reasoning**:
- Simplest to implement and debug
- Covers 90% of use cases
- Leverages existing ServerDiscovery pattern
- Can add NVS caching later if needed
- Low risk, immediate value

**Upgrade Path**:
1. **Now**: Boot-time fetch with hardcoded defaults
2. **Later**: Add NVS caching for offline resilience
3. **Future**: Add hot reload without rebooting

---

*Last Updated: 2025-09-29*
*Status: Design Phase - Ready for Implementation*