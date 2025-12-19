# Error State LED Testing Guide

## Overview
This guide helps you test all possible LED error states and visual feedback patterns on the Surf Lamp.

---

## Test Method 1: HTTP Endpoint Testing (Requires WiFi Connection)

### Prerequisites
- Lamp connected to WiFi
- Know the lamp's IP address (check serial monitor or router)

### Test Endpoints

**1. Basic Connection Test**
```bash
curl http://<LAMP_IP>/api/test
```
Expected: JSON response with status "ok"

**2. LED Strip Test**
```bash
curl http://<LAMP_IP>/api/led-test
```
Tests all surf display strips in sequence (blue, yellow, white, rainbow)

**3. Add Status LED Error State Test (NEW)**
Add this endpoint to test all status LED colors:
```bash
curl http://<LAMP_IP>/api/status-led-test
```

---

## Test Method 2: Manual State Simulation (Via Code)

Add this function to `main_reference.ino` after `performLEDTest()`:

```cpp
void testAllStatusLEDStates() {
    Serial.println("🧪 Testing all status LED states...");

    // 1. RED - WiFi Error
    Serial.println("   🔴 RED - WiFi Disconnected");
    for (int i = 0; i < 3; i++) {
        blinkRedLED();
        delay(500);
    }
    delay(2000);

    // 2. BLUE - Connecting
    Serial.println("   🔵 BLUE - Connecting to WiFi");
    for (int i = 0; i < 3; i++) {
        blinkBlueLED();
        delay(500);
    }
    delay(2000);

    // 3. GREEN - Connected & Fresh Data
    Serial.println("   🟢 GREEN - Connected & Fresh Data");
    for (int i = 0; i < 3; i++) {
        blinkGreenLED();
        delay(500);
    }
    delay(2000);

    // 4. ORANGE - Stale Data
    Serial.println("   🟠 ORANGE - Stale Data / Server Issues");
    for (int i = 0; i < 3; i++) {
        blinkOrangeLED();
        delay(500);
    }
    delay(2000);

    // 5. YELLOW - Config Mode
    Serial.println("   🟡 YELLOW - Configuration Portal");
    for (int i = 0; i < 3; i++) {
        blinkYellowLED();
        delay(500);
    }
    delay(2000);

    clearLEDs();
    Serial.println("✅ Status LED test completed");
}
```

Add endpoint registration in `setupHTTPEndpoints()`:
```cpp
server.on("/api/status-led-test", HTTP_GET, []() {
    Serial.println("🧪 Status LED test requested via HTTP");
    testAllStatusLEDStates();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Status LED test completed\"}");
});
```

---

## Test Method 3: Full System State Patterns

### Pattern 1: WiFi Connection Sequence (Startup)
**Trigger:** Power cycle the lamp or press reset button

**Expected LED Sequence:**
1. **Rainbow sweep** - Brief startup test (2-3 seconds)
2. **Green blinking (slow)** - Attempting WiFi connection (~30s per attempt)
3. **Purple blinking (slow)** - Checking location fingerprint (~1 second)
4. If successful:
   - **Status LED GREEN** - Connected & operational
5. If failed after 10 attempts:
   - **Red/White/Green strips** - Config portal (AP mode)
   - **Status LED YELLOW** - Waiting for user configuration

**Serial Output Check:**
```
🔄 WiFi connection attempt 1 of 10
📍 Loaded fingerprint: 4 neighbors
🔍 Checking if same location...
✅ Match found: 'NeighborNetwork1' - SAME LOCATION
✅ WiFi Connected!
```

---

### Pattern 2: Config Portal Mode (AP Mode)
**Trigger:** Press boot button for 3+ seconds

**Expected LED State:**
- **Wave Height strip (right):** Solid RED
- **Wind Speed strip (middle):** Solid WHITE
- **Wave Period strip (left):** Solid GREEN
- **Status LED:** Blinking YELLOW

**Serial Output Check:**
```
🔘 Button pressed - resetting WiFi
🔧 Config mode started
📱 AP: SurfLamp-Setup
```

**User Action:**
1. Connect to WiFi network "SurfLamp-Setup" (password: surf123456)
2. Navigate to http://192.168.4.1
3. Enter WiFi credentials

---

### Pattern 3: New Location Detection
**Trigger:** Move lamp to completely new location (different house, 0% WiFi neighbor match)

**Expected LED Sequence:**
1. **Green blinking** - First connection attempt (~30s)
2. **Purple blinking** - Location check (~1s)
3. **Immediate config portal** - Skips remaining 9 retry attempts
4. **Red/White/Green strips + Yellow status LED**

**Serial Output Check:**
```
🔍 Checking if same location...
❌ 0% match - NEW LOCATION (moved to new house)
🏠 NEW LOCATION DETECTED - Forcing AP mode
```

---

### Pattern 4: Stale Data Warning
**Trigger:** Disconnect backend server or wait 30+ minutes without data update

**Expected LED State:**
- **Status LED:** Blinking ORANGE (continuous)
- Surf display shows last known data

**Serial Output Check:**
```
⚠️ Status: ORANGE - Data is 35 min old (threshold: 30 min)
```

**Manual Trigger (Testing):**
```bash
# Stop backend processor service
# Wait 30 minutes
# Or manually modify lastSurfData.lastUpdate timestamp in code
```

---

### Pattern 5: WiFi Disconnection During Operation
**Trigger:** Power off router or disable WiFi while lamp is running

**Expected LED State:**
- **Status LED:** Blinking RED (immediate)
- Lamp attempts reconnection every 10 seconds

**Serial Output Check:**
```
❌ WiFi disconnected - Reason: Beacon timeout - AP disappeared or weak signal
🔄 WiFi disconnected - reconnection attempt 1 of 10
```

**After 10 failed reconnections:**
```
❌ Failed to reconnect after 10 attempts - restarting for config portal
```
Lamp restarts → Config portal mode

---

## Test Method 4: Diagnostic Error Scenarios

### Scenario 1: SSID Not Found (2.4GHz Disabled)
**Setup:** Configure lamp with 5GHz-only network or non-existent SSID

**Expected Behavior:**
- Green blinking during attempts (~30s each)
- Purple blinking for location check
- After 10 attempts → Config portal
- Error message in portal: "Network 'MyWiFi5G' not found. Check if 2.4GHz enabled"

**Test Command:**
1. Factory reset lamp (boot button)
2. Enter non-existent SSID in config portal
3. Observe retry sequence

---

### Scenario 2: Weak Signal (RSSI < -85 dBm)
**Setup:** Place lamp far from router or in shielded room

**Expected Behavior:**
- Connection attempts fail repeatedly
- Diagnostic shows: "Weak signal (-87 dBm)"
- Retries 10 times over ~5 minutes
- Eventually enters config portal

**Serial Output Check:**
```
🔍 Diagnosing connection to: MyNetwork
✅ Found target network:
   Signal: -87 dBm
   Channel: 6
   Security: 3
🔴 DIAGNOSTIC RESULT:
Weak signal (-87 dBm). Move lamp closer to router or use WiFi extender.
```

---

### Scenario 3: Wrong Password
**Setup:** Enter incorrect WiFi password

**Expected Behavior:**
- Immediate disconnect after connection attempt
- Error stored: "Authentication failed - check password and security mode"
- Red banner in config portal showing reason code 203
- Retries 10 times

**Serial Output Check:**
```
❌ WiFi disconnected - Reason: Authentication failed - check password and security mode
```

---

### Scenario 4: WPA3-Only Router
**Setup:** Configure router to WPA3-only mode (no WPA2)

**Expected Behavior:**
- Diagnostic detects WPA3: "Router uses WPA3 security. ESP32 requires WPA2."
- Error shown in config portal
- Retries 10 times → Config portal

---

## Status LED Color Reference

| Color | State | How to Trigger | Expected Blink Rate |
|-------|-------|----------------|---------------------|
| 🔴 **RED** | WiFi Error | Disconnect router, wrong password | 1 blink/sec |
| 🟢 **GREEN** | Fresh Data | Normal operation, data < 30 min old | 1 blink/sec |
| 🟠 **ORANGE** | Stale Data | Stop server, wait 30+ min | 1 blink/sec |
| 🔵 **BLUE** | Connecting | Power cycle lamp, first boot | 1 blink/sec |
| 🟡 **YELLOW** | Config Mode | Boot button press, 10 failed connections | 1 blink/sec |

---

## Full System LED Patterns Reference

| Pattern | State | How to Trigger |
|---------|-------|----------------|
| **Rainbow sweep** | Startup test | Power cycle lamp |
| **All GREEN blinking (slow)** | Attempting WiFi connection | Startup, wrong credentials |
| **All PURPLE blinking (slow)** | Checking location fingerprint | After each failed connection attempt |
| **Red/White/Green strips + YELLOW status** | Config portal (AP mode) | Boot button, 10 failed attempts, new location |
| **Normal surf display** | Operational | Connected with fresh data |

---

## Verification Checklist

Use this checklist to verify all error states work correctly:

### Status LED States:
- [ ] 🔴 RED - WiFi disconnected (power off router)
- [ ] 🟢 GREEN - Connected with fresh data (normal operation)
- [ ] 🟠 ORANGE - Stale data (stop server, wait 30 min)
- [ ] 🔵 BLUE - Connecting (power cycle lamp)
- [ ] 🟡 YELLOW - Config mode (boot button press)

### Full System Patterns:
- [ ] Rainbow startup test (power cycle)
- [ ] Green blinking - Connection attempts (wrong SSID)
- [ ] Purple blinking - Location check (failed connection)
- [ ] AP mode pattern - Red/White/Green strips (boot button)

### Diagnostic Scenarios:
- [ ] SSID not found error (enter fake SSID)
- [ ] Weak signal warning (place lamp far from router)
- [ ] Wrong password error (enter wrong password)
- [ ] New location detection (move lamp to different house)
- [ ] 10 retry attempts before AP mode (~5 minutes)

### Edge Cases:
- [ ] Router reboot during operation (power cycle router)
- [ ] Backend server down (stop processor service)
- [ ] Data staleness threshold (30 min without update)
- [ ] Immediate AP mode on new location (0% fingerprint match)

---

## Troubleshooting Test Failures

**Problem:** Status LED stuck on one color
- Check serial monitor for error messages
- Verify WiFi credentials
- Try manual factory reset (boot button)

**Problem:** No LED response at all
- Check power supply (5V, adequate current)
- Verify LED_PIN configuration (GPIO 2)
- Test with `/api/led-test` endpoint

**Problem:** Config portal not appearing
- Wait full 5 minutes (10 × 30s attempts)
- Check if lamp is in same location (fingerprint may be retrying)
- Force AP mode with boot button

**Problem:** Purple blinking never shows
- Location fingerprint check is very fast (~1 second)
- Watch serial monitor for "🔍 Checking if same location..."
- May be skipped if no stored fingerprint (first boot)

---

## Serial Monitor Commands for Testing

**Enable verbose WiFi debugging:**
```cpp
// Add to setup()
WiFi.setAutoReconnect(false);  // Manual control for testing
Serial.setDebugOutput(true);   // Verbose ESP32 WiFi logs
```

**Force specific error state:**
```cpp
// In loop(), add temporary test code:
if (Serial.available()) {
    char cmd = Serial.read();
    switch(cmd) {
        case 'r': blinkRedLED(); break;
        case 'g': blinkGreenLED(); break;
        case 'o': blinkOrangeLED(); break;
        case 'b': blinkBlueLED(); break;
        case 'y': blinkYellowLED(); break;
        case 't': testAllStatusLEDStates(); break;
    }
}
```

Then send commands via Serial Monitor:
- `r` = Test RED LED
- `g` = Test GREEN LED
- `o` = Test ORANGE LED
- `b` = Test BLUE LED
- `y` = Test YELLOW LED
- `t` = Test all states in sequence

---

**Last Updated:** 2025-12-17
**Firmware Version:** Configuration-driven template (main_reference.ino)
