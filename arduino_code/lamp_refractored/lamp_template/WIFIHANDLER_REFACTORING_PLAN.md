# Scott Meyers Refactoring Plan for WiFiHandler.cpp

*Following Effective C++ principles for cleaner, more maintainable code*

**Updated after WiFi.begin() fix - 12 phases, small focused changes**

---

## Current State After Bug Fix

The code now correctly uses:
- `WiFi.begin()` for ROUTER_REBOOT (no AP during retries)
- `autoConnect()` for FIRST_SETUP (opens AP for credentials)
- Time-based retry (5 minutes) instead of attempt-based
- Exponential backoff for both timeouts and delays

Main function still ~200 lines with deep nesting. Ready for refactoring.

---

## Phase 1: Extract Timeout Constants

**Current Issue:**
- Timeout values `1020`, `20`, `60`, `300000` scattered throughout
- Line 236: `1020`
- Line 244: `300000`
- Line 270: `1020`
- Line 293: `20 * pow(2, attempt - 1), 60`

**Action:**
```cpp
// At top of WiFiHandler.cpp or in Config.h
namespace WiFiTimeouts {
    const int PORTAL_TIMEOUT_GENEROUS_SEC = 1020;    // 17 minutes
    const int INITIAL_CONNECTION_TIMEOUT_SEC = 20;   // First attempt
    const int MAX_CONNECTION_TIMEOUT_SEC = 60;       // Cap for exponential backoff
    const unsigned long ROUTER_REBOOT_TIMEOUT_MS = 300000;  // 5 minutes total
}
```

**Replace:**
- Line 236: `WiFiTimeouts::PORTAL_TIMEOUT_GENEROUS_SEC`
- Line 244: `WiFiTimeouts::ROUTER_REBOOT_TIMEOUT_MS`
- Line 270: `WiFiTimeouts::PORTAL_TIMEOUT_GENEROUS_SEC`
- Line 293: Use with `WiFiTimeouts::INITIAL_CONNECTION_TIMEOUT_SEC` and `WiFiTimeouts::MAX_CONNECTION_TIMEOUT_SEC`

**Benefit:** Clear intent, single place to adjust timings

**Lines Changed:** ~6 replacements

---

## Phase 2: Extract Delay Constants

**Current Issue:**
- Delay values `5000`, `5`, `60`, `1000`, `3000`, `500` mixed throughout
- Line 296: `500` (connection polling)
- Line 316: `3000` (restart delay)
- Line 340: `1000` (location check display)
- Line 353: `5 * pow(2, attempt - 1), 60` (exponential delay)
- Line 355: `delaySeconds * 1000`
- Line 358: `5000` (HAS_CREDENTIALS retry delay)

**Action:**
```cpp
namespace WiFiDelays {
    const int INITIAL_RETRY_DELAY_SEC = 5;           // First retry delay
    const int MAX_RETRY_DELAY_SEC = 60;              // Cap for exponential backoff
    const int LOCATION_CHECK_DISPLAY_MS = 1000;      // Show purple LED
    const int RESTART_DELAY_MS = 3000;               // Before ESP.restart()
    const int CONNECTION_POLL_MS = 500;              // WiFi.status() polling interval
}
```

**Benefit:** Self-documenting delays, easy to tune

**Lines Changed:** ~8 replacements

---

## Phase 3: Move Enum to File Scope

**Current Issue:**
- `enum SetupScenario` defined inside `setupWiFi()` at line 225
- Can't reuse in helper functions

**Action:**
Move enum definition to top of file (before any functions):
```cpp
// Near top of WiFiHandler.cpp, before setupWiFi()
enum class WiFiSetupScenario {
    FIRST_SETUP,       // No credentials saved
    ROUTER_REBOOT,     // Has credentials, same location
    NEW_LOCATION,      // Has credentials, moved to different location
    HAS_CREDENTIALS    // Has credentials (generic fallback)
};
```

**Change line 225-226 from:**
```cpp
enum SetupScenario { FIRST_SETUP, ROUTER_REBOOT, NEW_LOCATION, HAS_CREDENTIALS };
SetupScenario scenario = hasCredentials ? ROUTER_REBOOT : FIRST_SETUP;
```

**To:**
```cpp
WiFiSetupScenario scenario = hasCredentials ? WiFiSetupScenario::ROUTER_REBOOT : WiFiSetupScenario::FIRST_SETUP;
```

**Benefit:** Can use in function signatures, clearer scope, type safety

**Lines Changed:** Move 1 line to file scope, update all enum references

---

## Phase 4: Extract Scenario Detection Function

**Current Issue:**
- Lines 218-226 do credential detection and scenario assignment
- Mixed in main function

**Action:**
```cpp
WiFiSetupScenario detectWiFiScenario() {
    // Initialize WiFi mode first so WiFi.SSID() can read persistent storage
    WiFi.mode(WIFI_STA);
    String savedSSID = WiFi.SSID();
    bool hasCredentials = (savedSSID.length() > 0);

    if (!hasCredentials) {
        return WiFiSetupScenario::FIRST_SETUP;
    }

    return WiFiSetupScenario::ROUTER_REBOOT;
}
```

**Replace lines 218-226 with:**
```cpp
WiFiSetupScenario scenario = detectWiFiScenario();
```

**Benefit:** Single responsibility, testable, clear intent

**Lines Changed:** Extract ~9 lines into function, replace with 1 line call

---

## Phase 5: Extract Scenario Configuration Function

**Current Issue:**
- Lines 228-240 configure portal based on scenario
- Mixing configuration with detection

**Action:**
```cpp
void configurePortalForScenario(WiFiManager& wifiManager, WiFiSetupScenario scenario) {
    if (scenario == WiFiSetupScenario::FIRST_SETUP) {
        Serial.println("📋 No WiFi credentials saved - opening configuration portal");
        Serial.println("🆕 FIRST SETUP MODE");
        Serial.println("   Opening configuration portal for 17 minutes");
        wifiManager.setConfigPortalTimeout(WiFiTimeouts::PORTAL_TIMEOUT_GENEROUS_SEC);
    } else {
        Serial.println("🔌 WiFi credentials found - assuming router reboot scenario");
        Serial.println("   Will retry for 5 minutes with exponential backoff");
    }
}
```

**Replace lines 228-240 with:**
```cpp
configurePortalForScenario(wifiManager, scenario);
```

**Benefit:** Configuration isolated, clear what each scenario does

**Lines Changed:** Extract ~13 lines into function, replace with 1 line call

---

## Phase 6: Extract Timeout Calculation Function

**Current Issue:**
- Exponential timeout calculation inline at line 293: `min(20 * (int)pow(2, attempt - 1), 60)`
- Formula not reusable

**Action:**
```cpp
int calculateExponentialTimeout(int attempt, int initialSeconds, int maxSeconds) {
    return min(initialSeconds * (int)pow(2, attempt - 1), maxSeconds);
}
```

**Replace line 293 with:**
```cpp
int timeout = calculateExponentialTimeout(
    attempt,
    WiFiTimeouts::INITIAL_CONNECTION_TIMEOUT_SEC,
    WiFiTimeouts::MAX_CONNECTION_TIMEOUT_SEC
);
```

**Benefit:** Reusable, testable, self-documenting

**Lines Changed:** Extract 1-liner into function, replace with named call

---

## Phase 7: Extract Delay Calculation Function

**Current Issue:**
- Delay calculation at line 353: `min(5 * (int)pow(2, attempt - 1), 60)`
- Same formula pattern as timeout

**Action:**
```cpp
int calculateExponentialDelay(int attempt, int initialSeconds, int maxSeconds) {
    return min(initialSeconds * (int)pow(2, attempt - 1), maxSeconds);
}
```

**Replace line 353 with:**
```cpp
int delaySeconds = calculateExponentialDelay(
    attempt,
    WiFiDelays::INITIAL_RETRY_DELAY_SEC,
    WiFiDelays::MAX_RETRY_DELAY_SEC
);
```

**Benefit:** Consistent with timeout calc, DRY principle

**Lines Changed:** Extract 1-liner into function, replace with named call

---

## Phase 8: Extract Visual Feedback Functions

**Current Issue:**
- Display logic scattered at lines 258-260, 264, 339-340
- Visual feedback mixed with logic

**Action:**
```cpp
void displayConnectionAttempt(int attempt, unsigned long elapsedSec, WiFiSetupScenario scenario) {
    if (scenario == WiFiSetupScenario::ROUTER_REBOOT) {
        Serial.printf("🔄 WiFi connection attempt %d (elapsed: %lu seconds)\n", attempt, elapsedSec);
    } else {
        Serial.printf("🔄 WiFi connection attempt %d\n", attempt);
    }
    showTryingToConnect();
}

void displayLocationCheck() {
    Serial.println("👀 Checking if same location...");
    showCheckingLocation();
    delay(WiFiDelays::LOCATION_CHECK_DISPLAY_MS);
}
```

**Replace lines 258-264 with:**
```cpp
displayConnectionAttempt(attempt, (millis() - retryStartTime) / 1000, scenario);
```

**Replace lines 339-340 with:**
```cpp
displayLocationCheck();
```

**Benefit:** UI logic separated, easier to modify visuals

**Lines Changed:** Extract ~8 scattered lines into 2 focused functions

---

## Phase 9: Extract Diagnostic Logic

**Current Issue:**
- Diagnostic logic (lines 305-348) is ~43 lines
- Mixed with retry loop
- Handles SSID checking, error messages, location detection

**Action:**
```cpp
struct DiagnosticResult {
    String errorMessage;
    bool isNewLocation;
    bool shouldRestart;
};

DiagnosticResult diagnoseConnectionFailure(
    WiFiFingerprinting& fingerprinting,
    WiFiSetupScenario scenario
) {
    String attemptedSSID = WiFi.SSID();

    if (attemptedSSID.length() == 0) {
        Serial.println("⚠️ No SSID stored - user did not enter credentials");
        bool shouldRestart = (scenario == WiFiSetupScenario::FIRST_SETUP ||
                             scenario == WiFiSetupScenario::NEW_LOCATION);
        return {"No credentials entered", false, shouldRestart};
    }

    Serial.printf("🔍 Diagnosing connection to: %s\n", attemptedSSID.c_str());
    String diagnostic = diagnoseSSID(attemptedSSID.c_str());

    if (diagnostic.length() > 0) {
        lastWiFiError = diagnostic;
        Serial.println("🔴 DIAGNOSTIC RESULT:");
        Serial.println(diagnostic);
        Serial.println("🔴 ==========================================");
    } else if (lastDisconnectReason != 0) {
        Serial.println("🔴 DISCONNECT REASON:");
        Serial.println(lastWiFiError);
        Serial.println("🔴 ==========================================");
    }

    displayLocationCheck();

    bool newLocation = !fingerprinting.isSameLocation();
    if (newLocation) {
        Serial.println("🏠 NEW LOCATION DETECTED - Forcing AP mode");
        lastWiFiError = "Moved to new location. Please reconfigure WiFi.";
    }

    return {diagnostic, newLocation, false};
}
```

**Replace lines 305-348 with:**
```cpp
DiagnosticResult diag = diagnoseConnectionFailure(fingerprinting, scenario);
if (diag.shouldRestart) {
    Serial.println("🔄 Restarting to reopen configuration portal...");
    delay(WiFiDelays::RESTART_DELAY_MS);
    ESP.restart();
}
if (diag.isNewLocation) {
    break; // Exit retry loop
}
```

**Benefit:** Huge reduction in nesting, diagnostic logic isolated, clear output

**Lines Changed:** Extract ~43 lines into function, replace with ~8 lines

---

## Phase 10: Extract Retry Delay Logic

**Current Issue:**
- Retry delay logic (lines 350-359) handles multiple scenarios
- Logic for "should we delay?" mixed with "how long?"

**Action:**
```cpp
void delayBeforeRetry(WiFiSetupScenario scenario, int attempt) {
    if (scenario == WiFiSetupScenario::ROUTER_REBOOT) {
        int delaySeconds = calculateExponentialDelay(
            attempt,
            WiFiDelays::INITIAL_RETRY_DELAY_SEC,
            WiFiDelays::MAX_RETRY_DELAY_SEC
        );
        Serial.printf("⏳ Waiting %d seconds before retry...\n", delaySeconds);
        delay(delaySeconds * 1000);
    } else if (scenario == WiFiSetupScenario::HAS_CREDENTIALS && attempt < MAX_WIFI_RETRIES) {
        Serial.println("⏳ Waiting 5 seconds before retry...");
        delay(WiFiDelays::INITIAL_RETRY_DELAY_SEC * 1000);
    }
}
```

**Replace lines 350-359 with:**
```cpp
delayBeforeRetry(scenario, attempt);
```

**Benefit:** Delay strategy in one place, easier to modify

**Lines Changed:** Extract ~10 lines into function, replace with 1 line call

---

## Phase 11: Extract Connection Attempt Logic

**Current Issue:**
- Connection attempt logic (lines 280-302) handles two different methods
- Router reboot uses WiFi.begin() with manual polling
- Other scenarios use autoConnect()
- 22 lines doing connection with different strategies

**Action:**
```cpp
bool attemptWiFiConnection(
    WiFiManager& wifiManager,
    WiFiSetupScenario scenario,
    int attempt
) {
    // Enable error injection for non-first-setup scenarios
    if (scenario != WiFiSetupScenario::FIRST_SETUP) {
        allowErrorInjection = true;
    }

    if (scenario == WiFiSetupScenario::ROUTER_REBOOT) {
        // ROUTER_REBOOT: Retry with saved credentials, NO AP portal
        Serial.println("   Attempting connection with saved credentials (no AP)...");
        WiFi.begin();  // Reconnect with saved credentials

        // Wait for connection with exponential backoff timeout
        int timeout = calculateExponentialTimeout(
            attempt,
            WiFiTimeouts::INITIAL_CONNECTION_TIMEOUT_SEC,
            WiFiTimeouts::MAX_CONNECTION_TIMEOUT_SEC
        );

        unsigned long startTime = millis();
        while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < (timeout * 1000)) {
            delay(WiFiDelays::CONNECTION_POLL_MS);
        }
        return (WiFi.status() == WL_CONNECTED);
    } else {
        // FIRST_SETUP or other scenarios: Use autoConnect (opens AP portal)
        return wifiManager.autoConnect("SurfLamp-Setup", "surf123456");
    }
}
```

**Replace lines 266-302 with:**
```cpp
connected = attemptWiFiConnection(wifiManager, scenario, attempt);
```

**Benefit:** Clean separation of two connection strategies, cleaner call site

**Lines Changed:** Extract ~37 lines into function, replace with 1 line call

---

## Phase 12: Simplify Main Loop Structure

**Current Issue:**
- Main retry loop (lines 247-361) is ~114 lines
- Hard to see control flow
- Deep nesting

**Action - Final Simplified Structure:**
```cpp
bool setupWiFi(WiFiManager& wifiManager, WiFiFingerprinting& fingerprinting) {
    Serial.println("📶 Starting WiFi setup...");

    wifiManager.setConfigPortalTimeout(0);  // Default: indefinite
    fingerprinting.load();

    WiFiSetupScenario scenario = detectWiFiScenario();
    configurePortalForScenario(wifiManager, scenario);

    unsigned long retryStartTime = millis();
    int attempt = 0;
    bool connected = false;

    // Main retry loop
    while (!connected) {
        attempt++;

        // Check time limit for router reboot scenario
        if (scenario == WiFiSetupScenario::ROUTER_REBOOT) {
            unsigned long elapsed = millis() - retryStartTime;
            if (elapsed >= WiFiTimeouts::ROUTER_REBOOT_TIMEOUT_MS) {
                Serial.println("⏱️ 5 minutes elapsed, opening AP indefinitely");
                wifiManager.setConfigPortalTimeout(0);
                break;
            }
        }

        // Display attempt status
        displayConnectionAttempt(attempt, (millis() - retryStartTime) / 1000, scenario);

        // Break for single-attempt scenarios
        if (scenario == WiFiSetupScenario::FIRST_SETUP && attempt > 1) {
            break;
        }

        // Attempt connection
        connected = attemptWiFiConnection(wifiManager, scenario, attempt);

        // Handle connection failure
        if (!connected) {
            Serial.println("❌ Connection failed - running diagnostics...");

            DiagnosticResult diag = diagnoseConnectionFailure(fingerprinting, scenario);

            if (diag.shouldRestart) {
                Serial.println("🔄 Restarting to reopen configuration portal...");
                delay(WiFiDelays::RESTART_DELAY_MS);
                ESP.restart();
            }

            if (diag.isNewLocation) {
                Serial.println("🏠 Exiting retry loop - new location detected");
                break;
            }

            delayBeforeRetry(scenario, attempt);
        }
    }

    // Handle not connected case (existing code continues...)
    if (!connected) {
        // ... AP mode logic ...
    }

    return connected;
}
```

**Benefit:** Main function now ~50 lines, clear flow, easy to understand

**Lines Changed:** Reorganize ~114 lines into cleaner structure using extracted functions

---

## Summary of Benefits (Scott Meyers Principles)

### Item 18: Make interfaces easy to use correctly, hard to use incorrectly
- Named constants prevent wrong timeout values
- Clear function signatures show intent
- Return types like `DiagnosticResult` prevent misinterpretation

### Item 20: Prefer pass-by-reference-to-const
- Maintained throughout refactoring

### Item 23: Prefer non-member non-friend functions
- All helper functions are standalone
- Operate on passed parameters, not hidden state

### Single Responsibility Principle
- Each function has ONE clear job
- Detection → detect scenario
- Configuration → configure portal
- Diagnostic → diagnose failure
- Delay → calculate and execute delay
- Connection → attempt connection

### Don't Repeat Yourself (DRY)
- Exponential backoff formula extracted once (used for both timeout and delay)
- Display logic in dedicated functions
- Connection logic in one place

### Clear Separation of Concerns
```
Detection → Configuration → Retry Loop → Attempt → Diagnose → Delay → Repeat
```

---

## Metrics

**Before Refactoring:**
- Main function: ~200 lines
- Max nesting level: 5
- Functions: 1 giant function
- Magic numbers: 12+
- Testable units: 0 (must test entire WiFi stack)
- Connection strategies: Mixed inline

**After Refactoring (12 phases):**
- Main function: ~50 lines
- Max nesting level: 2
- Functions: 11 focused functions (5-35 lines each)
- Magic numbers: 0 (all named constants)
- Testable units: 10 functions
- Connection strategies: Cleanly separated

**Maintainability Improvements:**
- Change retry strategy → modify `attemptWiFiConnection()` or delay functions
- Adjust timeouts → modify constants
- Add new scenario → add enum value + update switch cases
- Change visual feedback → modify display functions
- Fix connection logic → modify `attemptWiFiConnection()` only

**Readability:**
- Function names describe intent
- Constants self-document
- Clear control flow in main loop
- Each phase is independently testable

---

## Implementation Order

**Safe order (each phase independently compilable):**
1. Phase 1 (timeout constants)
2. Phase 2 (delay constants)
3. Phase 6 (timeout calculation)
4. Phase 7 (delay calculation)
5. Phase 3 (move enum to file scope)
6. Phase 4 (detect scenario)
7. Phase 5 (configure scenario)
8. Phase 8 (visual feedback)
9. Phase 10 (retry delay)
10. Phase 9 (diagnostics - big one)
11. Phase 11 (connection attempt - big one)
12. Phase 12 (simplify main)

**Each phase:**
- Compiles successfully
- Maintains existing behavior
- Improves one aspect of code quality
- Takes 10-30 minutes to implement

**Test after phases 3, 6, 9, 11, 12** to ensure behavior unchanged
