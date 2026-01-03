# Open Network Test Hotspot

**Purpose:** Debug lamp connection issues with passwordless WiFi networks.

## Problem Being Investigated

Your dad's lamp couldn't connect to an open network (no password). This test setup helps us capture serial logs to identify the root cause.

## Hardware Needed

- Any spare ESP32 or ESP8266 board
- USB cable for serial monitoring

## Setup Instructions

### 1. Upload Hotspot Code

```bash
# Open Arduino IDE
# Load: open_network_hotspot.ino
# Select Board: ESP32 Dev Module (or ESP8266)
# Upload
```

### 2. Monitor Hotspot Serial Output

- Open Serial Monitor (115200 baud)
- Should show: "TestOpenNetwork" created
- Leave this running to see when lamp connects

### 3. Connect Lamp to Test Network

**On the surf lamp:**
1. Reset WiFi (hold button 2 seconds) or ensure it enters AP mode
2. Connect phone to "SurfLamp-Setup"
3. Portal opens → select "TestOpenNetwork"
4. **Leave password field BLANK**
5. Click Save

### 4. Watch BOTH Serial Monitors

**Hotspot monitor shows:**
- "NEW DEVICE CONNECTED" when lamp connects

**Lamp monitor shows (what we need):**
```
🔍 Diagnosing connection to: TestOpenNetwork
   Security: 0  ← Should be 0 (open network)
❌ WiFi disconnected - Reason: <ERROR MESSAGE>
```

**The disconnect reason is what we need to fix the bug.**

## What To Look For

### If Lamp Connects ✅
- Hotspot shows "NEW DEVICE CONNECTED"
- Lamp shows "✅ WiFi Connected!"
- **Bug is environmental** (specific to dad's network)

### If Lamp Fails ❌
- Check lamp logs for disconnect reason code
- Look for "Security: 0" in diagnostics
- Capture full serial output and send to Claude

## Expected Behavior

**Working scenario:**
```
[Lamp] 🔍 Diagnosing connection to: TestOpenNetwork
[Lamp]    Security: 0
[Lamp] ℹ️ This is an OPEN network (no password)
[Hotspot] NEW DEVICE CONNECTED!
[Lamp] ✅ WiFi Connected!
```

**Failing scenario (ESP32 bug):**
```
[Lamp] 🔍 Diagnosing connection to: TestOpenNetwork
[Lamp]    Security: 0
[Lamp] ❌ WiFi disconnected - Reason: <code>
[Hotspot] (no connection)
```

## Cleanup

After testing, you can delete this directory or keep it for future network debugging.
