# Scott Meyers Refactoring Plan for WiFiHandler.cpp

*Following Effective C++ principles for cleaner, more maintainable code*

**12 phases - small, focused changes following "little by little" approach**

---

## Phase 1: Extract Timeout Constants

**Current Issue:**
- Timeout values `1020`, `20`, `60` scattered throughout
- Unclear what each timeout represents

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

**Replace all hardcoded timeout numbers with named constants**

**Benefit:** Clear intent, single place to adjust timings

**Lines Changed:** ~10 replacements

---

## Phase 2: Extract Delay Constants

**Current Issue:**
- Delay values `5000`, `10`, `5`, `1000` mixed throughout
- Hard to see delay strategy at a glance

**Action:**
```cpp
namespace WiFiDelays {
    const int INITIAL_RETRY_DELAY_SEC = 5;           // First retry delay
    const int MAX_RETRY_DELAY_SEC = 60;              // Cap for exponential backoff
    const int LOCATION_CHECK_DISPLAY_MS = 1000;      // Show purple LED
    const int RESTART_DELAY_MS = 3000;               // Before ESP.restart()
}
```

**Replace all hardcoded delay numbers with named constants**

**Benefit:** Self-documenting delays, easy to tune

**Lines Changed:** ~8 replacements

---

## Phase 3: Move Enum to File Scope

**Current Issue:**
- `enum SetupScenario` defined inside `setupWiFi()` function
- Can't reuse in helper functions

**Action:**
Move enum definition to top of file:
```cpp
// Near top of WiFiHandler.cpp, before any functions
enum class WiFiSetupScenario {
    FIRST_SETUP,       // No credentials saved
    ROUTER_REBOOT,     // Has credentials, same location
    NEW_LOCATION,      // Has credentials, moved to different location
    HAS_CREDENTIALS    // Has credentials (generic fallback)
};
```

**Benefit:** Can use in function signatures, clearer scope

**Lines Changed:** Move 4 lines from inside function to file scope

---

## Phase 4: Extract Scenario Detection Function

**Current Issue:**
- Credential checking and scenario logic mixed in main function
- Lines 218-226 do one logical thing but aren't separated

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

**In main function, replace lines 218-226 with:**
```cpp
WiFiSetupScenario scenario = detectWiFiScenario();
```

**Benefit:** Single responsibility, testable, clear intent

**Lines Changed:** Extract ~9 lines into new function, replace with 1 line call

---

## Phase 5: Extract Scenario Configuration Function

**Current Issue:**
- Portal timeout configuration logic for each scenario (lines 228-240)
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

**Lines Changed:** Extract ~13 lines into new function, replace with 1 line call

---

## Phase 6: Extract Timeout Calculation Function

**Current Issue:**
- Exponential backoff calculation inline: `min(20 * (int)pow(2, attempt - 1), 60)`
- Formula duplicated, unclear intent

**Action:**
```cpp
int calculateExponentialTimeout(int attempt, int initialSeconds, int maxSeconds) {
    return min(initialSeconds * (int)pow(2, attempt - 1), maxSeconds);
}
```

**Replace timeout calculation (line 269) with:**
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
- Delay calculation also uses exponential backoff: `min(5 * (int)pow(2, attempt - 1), 60)`
- Same formula pattern as timeout

**Action:**
```cpp
int calculateExponentialDelay(int attempt, int initialSeconds, int maxSeconds) {
    return min(initialSeconds * (int)pow(2, attempt - 1), maxSeconds);
}
```

**Replace delay calculation (line 342) with:**
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
- `showTryingToConnect()`, `showCheckingLocation()` calls scattered
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

**Benefit:** UI logic separated, easier to modify visuals

**Lines Changed:** Extract ~5 scattered lines into 2 focused functions

---

## Phase 9: Extract Diagnostic Logic

**Current Issue:**
- Diagnostic logic (lines 274-325) mixed with retry loop
- ~50 lines doing diagnosis and location checking

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

**Replace lines 274-337 with:**
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

**Lines Changed:** Extract ~50 lines into function, replace with ~8 lines

---

## Phase 10: Extract Retry Delay Logic

**Current Issue:**
- Retry delay logic (lines 339-348) handles multiple scenarios
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

**Replace lines 339-348 with:**
```cpp
delayBeforeRetry(scenario, attempt);
```

**Benefit:** Delay strategy in one place, easier to modify

**Lines Changed:** Extract ~10 lines into function, replace with 1 line call

---

## Phase 11: Extract Connection Attempt Logic

**Current Issue:**
- Core connection attempt (lines 285-290) buried in diagnostics
- Unclear what's the "attempt" vs what's the "response"

**Action:**
```cpp
bool attemptWiFiConnection(
    WiFiManager& wifiManager,
    WiFiSetupScenario scenario,
    int timeoutSeconds
) {
    if (scenario != WiFiSetupScenario::FIRST_SETUP) {
        allowErrorInjection = true;
    }

    wifiManager.setConfigPortalTimeout(timeoutSeconds);
    return wifiManager.autoConnect("SurfLamp-Setup", "surf123456");
}
```

**Replace connection attempt with:**
```cpp
int timeout = calculateExponentialTimeout(...);
bool connected = attemptWiFiConnection(wifiManager, scenario, timeout);
```

**Benefit:** Clean separation of attempt from result handling

**Lines Changed:** Extract ~5 lines into function, cleaner call site

---

## Phase 12: Simplify Main Loop Structure

**Current Issue:**
- Main retry loop (lines 247-350) is ~100 lines
- Hard to see control flow

**Action - Final Simplified Structure:**
```cpp
bool setupWiFi(WiFiManager& wifiManager, WiFiFingerprinting& fingerprinting) {
    wifiManager.setConfigPortalTimeout(0);  // Default: indefinite
    fingerprinting.load();

    WiFiSetupScenario scenario = detectWiFiScenario();
    configurePortalForScenario(wifiManager, scenario);

    unsigned long retryStartTime = millis();
    int attempt = 0;
    bool connected = false;

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

        displayConnectionAttempt(attempt, (millis() - retryStartTime) / 1000, scenario);

        int timeout = calculateTimeout(scenario, attempt);
        connected = attemptWiFiConnection(wifiManager, scenario, timeout);

        if (!connected) {
            DiagnosticResult diag = diagnoseConnectionFailure(fingerprinting, scenario);

            if (diag.shouldRestart) {
                delay(WiFiDelays::RESTART_DELAY_MS);
                ESP.restart();
            }

            if (diag.isNewLocation) {
                break;  // Exit to AP mode
            }

            // Break for single-attempt scenarios
            if (scenario == WiFiSetupScenario::FIRST_SETUP && attempt > 1) {
                break;
            }

            delayBeforeRetry(scenario, attempt);
        }
    }

    // Handle not connected case (existing code from line 352+)
    if (!connected) {
        // ... AP mode logic ...
    }

    return connected;
}
```

**Where `calculateTimeout()` is:**
```cpp
int calculateTimeout(WiFiSetupScenario scenario, int attempt) {
    if (scenario == WiFiSetupScenario::ROUTER_REBOOT) {
        return calculateExponentialTimeout(
            attempt,
            WiFiTimeouts::INITIAL_CONNECTION_TIMEOUT_SEC,
            WiFiTimeouts::MAX_CONNECTION_TIMEOUT_SEC
        );
    } else if (scenario == WiFiSetupScenario::HAS_CREDENTIALS) {
        return (attempt < MAX_WIFI_RETRIES)
            ? WiFiTimeouts::PORTAL_TIMEOUT_GENEROUS_SEC
            : 0;  // Indefinite on final attempt
    }
    return 0;  // Already set for FIRST_SETUP
}
```

**Benefit:** Main function now ~40 lines, clear flow, easy to understand

**Lines Changed:** Reorganize ~100 lines into cleaner structure using extracted functions

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
- Diagnostic → diagnose
- Delay calculation → calculate delay
- Visual feedback → display

### Don't Repeat Yourself (DRY)
- Exponential backoff formula extracted once
- Timeout/delay strategy in named functions

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

**After Refactoring (12 phases):**
- Main function: ~40 lines
- Max nesting level: 2
- Functions: 11 focused functions (5-30 lines each)
- Magic numbers: 0 (all named constants)
- Testable units: 10 functions

**Maintainability Improvements:**
- Change retry strategy → modify 1 function
- Adjust timeouts → modify constants
- Add new scenario → add enum value + case in switch
- Change visual feedback → modify display functions

**Readability:**
- Function names describe intent
- Constants self-document
- Clear control flow in main loop
- Each phase is independently testable

---

## Implementation Order

**Safe order (each phase independently compilable):**
1. Phase 1 (timeouts)
2. Phase 2 (delays)
3. Phase 6 (timeout calc)
4. Phase 7 (delay calc)
5. Phase 3 (move enum)
6. Phase 4 (detect scenario)
7. Phase 5 (configure scenario)
8. Phase 8 (visual feedback)
9. Phase 11 (connection attempt)
10. Phase 10 (retry delay)
11. Phase 9 (diagnostics - big one)
12. Phase 12 (simplify main)

**Each phase:**
- Compiles successfully
- Maintains existing behavior
- Improves one aspect of code quality
- Takes 10-30 minutes to implement
