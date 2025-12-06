# Surf Lamp WiFi Diagnostics Guide

## Overview

The Surf Lamp now includes **professional WiFi diagnostics** to help you understand WHY your lamp fails to connect at certain homes. Instead of generic "blue LEDs = setup mode", you'll get specific error feedback through LED blink patterns and detailed serial logs.

## What Was Added

### 1. Pre-Scan Diagnostics
Before attempting to connect, the lamp now:
- **Scans for your SSID** to verify it exists
- **Checks signal strength** (RSSI in dBm)
- **Verifies WiFi channel** (ESP32 supports 1-13, not 5GHz)
- **Checks security mode** (WPA2/WPA3 compatibility)

### 2. Disconnect Reason Codes
When connection fails, the lamp captures the **exact ESP32 disconnect reason code** and translates it to human-readable messages:
- Wrong password (reason codes 6, 7, 15)
- Security mode mismatch (WPA3 vs WPA2)
- Weak signal (beacon timeout, reason 201)
- SSID not found (reason 202)
- Router rejected connection (reason 204)

### 3. LED Error Patterns
Different LED blink patterns now indicate **specific problems**:

| LED Pattern | Meaning | Action Required |
|-------------|---------|-----------------|
| **Fast Red Blink** (100ms) | SSID not found | Check SSID spelling, ensure 2.4GHz enabled |
| **Purple Blink** (200ms) | WPA3 incompatible | Change router to WPA2/WPA3 mixed mode |
| **Orange Blink** (300ms) | Weak signal | Move lamp closer to router or use WiFi extender |
| **Slow Red Blink** (500ms) | Generic error (wrong password) | Check password, review serial logs |
| **Blue Breathing** | Setup mode / Connecting | Normal - waiting for credentials |
| **Green Breathing** | Connected & operational | All good! |

### 4. HTTP Diagnostics Endpoint
Once connected (or in config mode with fallback IP), access:
```
http://<lamp-ip>/api/wifi-diagnostics
```

Returns JSON with:
```json
{
  "current_ssid": "YourNetwork",
  "connected": true,
  "ip_address": "192.168.1.100",
  "signal_strength_dbm": -45,
  "last_error": "Wrong password",
  "last_disconnect_reason_code": 15,
  "channel": 6,
  "security_type": 3
}
```

## Common Issues & Solutions

### Issue 1: Works at Your Home, Fails at Others

**Possible Causes:**

1. **WPA3 Security**
   - **Symptom:** Purple LED blink after entering credentials
   - **Why:** ESP32 only supports WPA2, some routers default to WPA3
   - **Fix:** Change router security to "WPA2/WPA3 Mixed Mode"
   - **Log Message:** `"Router uses WPA3 security. ESP32 requires WPA2."`

2. **WiFi Channel > 11**
   - **Symptom:** SSID found in scan but connection fails
   - **Why:** ESP32 officially supports channels 1-11 (region dependent)
   - **Fix:** Change router channel to 1-11
   - **Log Message:** `"Warning: Channel 12 may not be supported in all regions"`

3. **5GHz Band Only**
   - **Symptom:** Fast red blink (SSID not found)
   - **Why:** ESP32 is 2.4GHz only, router may have hidden 2.4GHz band
   - **Fix:** Enable 2.4GHz band in router settings
   - **Log Message:** `"Network 'YourSSID' not found. Is router's 2.4GHz band enabled?"`

4. **Weak Signal**
   - **Symptom:** Orange LED blink
   - **Why:** Signal < -85 dBm is too weak for stable connection
   - **Fix:** Move lamp closer or use WiFi extender
   - **Log Message:** `"Weak signal (-87 dBm). Move lamp closer to router."`

5. **Special Characters in Password**
   - **Symptom:** Wrong password error despite correct entry
   - **Why:** Some special chars (quotes, backslashes) may not parse correctly
   - **Fix:** Use alphanumeric passwords or test with simpler password
   - **Log Message:** `"Handshake timeout - wrong password or security mismatch"`

### Issue 2: SSID Not Found

**Fast Red Blink (100ms intervals)**

**Checklist:**
1. Is SSID spelled correctly? (case-sensitive)
2. Is router's 2.4GHz band enabled? (not just 5GHz)
3. Is router in range? (signal visible on phone)
4. Is network hidden? (ESP32 struggles with hidden SSIDs)

**Serial Log Example:**
```
🔍 Scanning for SSID: MyNetwork
📡 Found 12 networks
   0: Neighbor-WiFi (Ch 1, -65 dBm, Auth 3)
   1: CoffeeShop (Ch 6, -80 dBm, Auth 4)
❌ Network 'MyNetwork' not found
```

### Issue 3: Wrong Password

**Slow Red Blink (500ms intervals)**

**Disconnect Reasons:**
- Reason 6: "Wrong password or WPA/WPA2 mismatch"
- Reason 7: "Wrong password"
- Reason 15: "4-way handshake timeout - likely wrong password"

**Checklist:**
1. Password entered correctly? (case-sensitive)
2. Any special characters that might cause issues? (`"`, `\`, etc.)
3. Router using WPA2 (not WPA3)?

## How to Read Serial Logs

Connect lamp to computer via USB, open serial monitor at **115200 baud**.

**Successful Connection:**
```
🔄 WiFi connection attempt 1 of 5
🔍 Scanning for SSID: HomeNetwork
📡 Found 8 networks
✅ Found target network:
   Signal: -55 dBm
   Channel: 6
   Security: 3 (WPA2)
✅ WiFi connected to AP
✅ Got IP: 192.168.1.100
✅ WiFi Connected!
```

**Failed Connection with Diagnostics:**
```
🔄 WiFi connection attempt 1 of 5
❌ Connection failed - running diagnostics...
🔍 Diagnosing connection to: GuestNetwork
📡 Found 8 networks
✅ Found target network:
   Signal: -88 dBm
   Channel: 11
   Security: 3
🔴 DIAGNOSTIC RESULT:
Weak signal (-88 dBm). Move lamp closer to router or use WiFi extender.
🔴 ==========================================
[Orange LED blink pattern]
⏳ Waiting 5 seconds before retry...
```

## Testing Your Changes

After uploading updated firmware:

1. **Reset WiFi credentials** (hold boot button, wait for restart)
2. **Connect to SurfLamp-Setup** AP (password: surf123456)
3. **Enter WRONG SSID first** to test "SSID not found" diagnostics
   - Expect: Fast red blink + serial log showing available networks
4. **Enter CORRECT SSID but WRONG password**
   - Expect: Slow red blink + disconnect reason code 15 or 7
5. **Test with router in WPA3 mode** (if available)
   - Expect: Purple blink + "WPA3 incompatible" message
6. **Move lamp far from router** (< -85 dBm signal)
   - Expect: Orange blink + "Weak signal" message

## For Users (Non-Technical)

**"My lamp stays blue and won't connect"**

1. Watch the LED pattern after entering WiFi password:
   - **Fast red blinks** = Wrong network name (check spelling)
   - **Purple blinks** = Router too new (needs setting change)
   - **Orange blinks** = Too far from router (move closer)
   - **Slow red blinks** = Wrong password

2. Check your router settings:
   - **2.4GHz WiFi must be ON** (not just 5GHz)
   - **Security should be "WPA2" or "WPA2/WPA3 Mixed"** (not WPA3 only)
   - **WiFi channel should be 1-11** (not 12, 13, or 14)

3. If still stuck, connect laptop to lamp via USB and send us the serial logs

## Implementation Details (for Developers)

### Files Modified
- `surf_lamp_wooden.ino:93-94` - Added diagnostic state variables
- `surf_lamp_wooden.ino:289-449` - WiFi diagnostic functions
- `surf_lamp_wooden.ino:708-737` - HTTP diagnostics endpoint
- `surf_lamp_wooden.ino:1088-1238` - Enhanced setup() with diagnostics

### Key Functions

**`diagnoseSSID(const char* targetSSID)`** - Line 345
- Scans for SSID availability
- Checks signal strength (< -85 dBm = weak)
- Checks security mode (WPA3 = incompatible)
- Returns error message or empty string

**`WiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info)`** - Line 319
- Captures ARDUINO_EVENT_WIFI_STA_DISCONNECTED
- Extracts disconnect reason code from `info.wifi_sta_disconnected.reason`
- Translates to human-readable message via `getDisconnectReasonText()`

**`getDisconnectReasonText(uint8_t reason)`** - Line 295
- Maps ESP-IDF `wifi_err_reason_t` codes to actionable messages
- Covers 15 common failure reasons

### LED Feedback Integration
- Lines 1172-1202: Visual error patterns based on diagnostic results
- Pattern duration gives user time to observe and record the error type
- Different blink speeds make errors distinguishable without serial monitor

## References

- [ESP-IDF WiFi Disconnect Reasons](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/wifi.html#wi-fi-reason-code)
- [Perplexity Research on ESP32 WiFi Best Practices](https://www.perplexity.ai/)
- Original implementation: surf_lamp_wooden.ino (Arduino ID 2)

---

**Result:** Users at "other homes" will now see:
1. Specific LED error patterns (not just generic blue)
2. Detailed serial logs explaining the root cause
3. Actionable next steps (change router setting, move closer, fix password, etc.)

This eliminates guesswork and provides professional-grade diagnostics for IoT WiFi issues.
