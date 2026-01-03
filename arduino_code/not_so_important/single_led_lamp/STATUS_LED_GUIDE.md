# Status LED Indication Guide

## Overview
The status LED (bottom LED of the wind speed strip) provides real-time feedback about the lamp's connectivity and data freshness.

## Status Colors

| LED Color | Status | Meaning | Action Required |
|-----------|--------|---------|-----------------|
| 🔴 **RED** (blinking) | No WiFi | Lamp disconnected from WiFi network | Check router, verify WiFi credentials |
| 🟢 **GREEN** (blinking) | Online & Fresh | WiFi connected, surf data is fresh (< 30 min old) | None - operating normally |
| 🟠 **ORANGE** (blinking) | Data Warning | WiFi connected but data is stale or server unreachable | Check server status, wait for next fetch |
| 🔵 **BLUE** (blinking) | Connecting | Attempting to connect to WiFi | Wait for connection |
| 🟡 **YELLOW** (blinking) | Config Mode | WiFi configuration portal active | Connect to "SurfLamp-Setup" network |

## Detailed Status Explanations

### 🔴 RED - WiFi Disconnected
**When it appears:**
- WiFi network is unavailable
- Router is powered off or out of range
- WiFi credentials are incorrect

**What the lamp does:**
- Attempts to reconnect every 10 seconds
- After 5 failed reconnection attempts, restarts into config portal mode
- LED display shows last cached surf data (if any)

**How to fix:**
1. Check if router is powered on and in range
2. Verify 2.4GHz WiFi is enabled (ESP32 doesn't support 5GHz)
3. If issue persists, press boot button to reset WiFi settings

---

### 🟢 GREEN - Fresh Data Available
**When it appears:**
- WiFi is connected
- Surf data was successfully fetched within last 30 minutes
- Server is responding normally

**What this means:**
- Lamp is displaying current surf conditions
- Data is reliable and up-to-date
- System is operating as expected

**Normal behavior:**
- Lamp fetches new data every 13 minutes
- GREEN should be the most common status during normal operation

---

### 🟠 ORANGE - Stale Data Warning
**When it appears:**
- WiFi is connected BUT one of these conditions:
  - Surf data is older than 30 minutes (2+ missed fetches)
  - Server is unreachable
  - Lamp never received data since boot

**What this means:**
- LED display may be showing outdated surf conditions
- Server may be down for maintenance
- API endpoint may be experiencing issues

**How to diagnose:**
1. Check serial monitor for error messages (115200 baud):
   - `⚠️ Status: ORANGE - No data received yet` = Server unreachable since boot
   - `⚠️ Status: ORANGE - Data is X min old` = Last successful fetch time
2. Wait 13 minutes for next automatic fetch attempt
3. Force manual fetch: `http://<lamp-ip>/api/fetch`
4. Check server status via Render MCP tools

**Common causes:**
- Background processor service down
- API rate limiting
- Database connection issues
- Network firewall blocking HTTPS requests

---

### 🔵 BLUE - Connecting to WiFi
**When it appears:**
- During lamp startup
- Attempting to connect to saved WiFi network
- Brief transition state

**What to expect:**
- Should transition to GREEN within 30 seconds on successful connection
- If stays BLUE for >1 minute, WiFi connection is failing

---

### 🟡 YELLOW - Configuration Mode
**When it appears:**
- First-time setup (no WiFi credentials saved)
- After pressing boot button to reset WiFi
- After 5 failed reconnection attempts

**What to do:**
1. Connect phone/computer to WiFi network: `SurfLamp-Setup`
2. Password: `surf123456`
3. Browser should auto-open to configuration page
4. If not, navigate to: `http://192.168.4.1`
5. Enter your WiFi credentials
6. Lamp will restart and connect to your network

---

## Data Staleness Threshold

**Threshold:** 30 minutes (1,800,000 milliseconds)

**Why 30 minutes?**
- Fetch interval: 13 minutes
- 2 consecutive missed fetches: ~26 minutes
- Grace period for network delays: 4 minutes
- **Total:** 30 minutes before showing ORANGE warning

This ensures users aren't warned prematurely for temporary network hiccups, but are alerted if data becomes unreliable.

---

## Troubleshooting Guide

### Status LED is RED
1. Check router power and WiFi signal strength
2. Verify 2.4GHz band is enabled (ESP32 requirement)
3. Move lamp closer to router or use WiFi extender
4. Check WiFi credentials via serial monitor
5. Reset WiFi settings (press boot button) and reconfigure

### Status LED is ORANGE for extended period
1. Check serial monitor for specific error messages
2. Verify server is running: Check Render deployment status
3. Test manual fetch: `http://<lamp-ip>/api/fetch`
4. Check background processor logs for API errors
5. Verify lamp can reach server: Check firewall rules

### Status LED stuck on BLUE
1. WiFi connection is failing repeatedly
2. Check serial monitor for disconnect reason codes
3. Common issues:
   - Wrong password (reason code 15 or 203)
   - WPA3-only router (ESP32 requires WPA2)
   - Weak signal (RSSI < -85 dBm)
   - Hidden SSID or MAC filtering

---

## Serial Monitor Debug Output

Connect to lamp via USB at 115200 baud to see detailed status:

```
✅ WiFi Connected!
📍 IP Address: 192.168.1.42
🔄 Attempting initial surf data fetch...
✅ Initial surf data fetch successful
🎨 LEDs Updated - Wind: 3, Wave: 2, Period: 5, Direction: 340°

[Every 60 seconds if ORANGE:]
⚠️ Status: ORANGE - Data is 35 min old (threshold: 30 min)
```

---

## LED Mapping Reference

**Wooden Lamp (Arduino ID 2):**
- Status LED: LED #101 (bottom of wind speed strip)

**Ben's Lamp (Arduino ID 4):**
- Status LED: LED #101 (bottom of wind speed strip)

---

## Configuration Constants

Location in code: `surf_lamp_wooden.ino` / `surf_lamp_ben.ino`

```cpp
const unsigned long FETCH_INTERVAL = 780000;              // 13 minutes
const unsigned long DATA_STALENESS_THRESHOLD = 1800000;   // 30 minutes
const int MAX_WIFI_RETRIES = 5;                           // Reconnection attempts
```

---

**Last Updated:** 2025-12-12
**Firmware Version:** 2.0.0-wooden-lamp
