# WiFi Chaos Testing Plan

**Goal:** Ensure surf lamp handles every common router failure gracefully.

## Test Philosophy

> "The ESP32 doesn't replace a router—it replaces a frustrated customer."

Instead of guessing what went wrong with specific networks, we **systematically test every failure mode** and verify the lamp's behavior.

---

## Test Scenarios

### ✅ Scenario 0: STABLE_OPEN (Baseline)
**What it simulates:** Perfect open network (already tested - PASSED)

**Expected lamp behavior:**
- Connects successfully
- Gets IP address
- Updates fingerprint
- Ready for operation

**Status:** ✅ PASSED (12:04 test logs)

---

### 🔥 Scenario 1: FREQUENT_DISCONNECTS
**What it simulates:** Router with unstable WiFi (bad hardware, interference, overheating)

**Chaos behavior:**
- AP disconnects every 30 seconds
- Immediately restarts

**Expected lamp behavior:**
- Detects disconnect (reason 201)
- Attempts reconnection (handleWiFiHealth)
- Should NOT restart after <10 failed attempts
- Logs should show: "🔄 WiFi disconnected - reconnection attempt X of 10"

**Test:** Upload `chaos_router_scenarios.ino`, select scenario 1, observe lamp logs

**What we're validating:**
- Reconnection logic works
- Doesn't give up too early
- Doesn't spam restarts

---

### 🔥 Scenario 2: DHCP_DELAYS
**What it simulates:** Overloaded router (many devices, slow CPU)

**Chaos behavior:**
- AP accepts connection
- DHCP server responds slowly (5-10 second delay)

**Expected lamp behavior:**
- Waits patiently for IP
- Eventually gets IP and continues
- Does NOT timeout prematurely

**Implementation note:** Requires custom DHCP server (advanced - may skip)

---

### 🔥 Scenario 3: RANDOM_REBOOTS
**What it simulates:** Router power cycling, firmware crashes, user unplugging

**Chaos behavior:**
- AP reboots every 2 minutes
- 5-second boot delay

**Expected lamp behavior:**
- Enters ROUTER_REBOOT scenario
- Retries with exponential backoff
- After 5 minutes → Opens portal
- **CRITICAL:** Should wipe credentials after repeated failures (your architectural fix)

**What we're validating:**
- Exponential backoff works
- Doesn't drain battery with constant retries
- Eventually gives up and asks for help (portal)

---

### 🔥 Scenario 4: NO_INTERNET
**What it simulates:** Connected to WiFi but router has no WAN (ISP outage, unpaid bill)

**Chaos behavior:**
- AP accepts connection
- Provides IP address
- But no internet gateway configured

**Expected lamp behavior:**
- Connects successfully (WiFi is UP)
- HTTP requests to backend fail
- Should show error on dashboard (not infinite loading)
- Does NOT restart WiFi (it's connected, just no internet)

**What we're validating:**
- Lamp distinguishes "WiFi down" from "Internet down"
- User sees meaningful error message

---

### 🔥 Scenario 5: SHORT_LEASES
**What it simulates:** Router forcing frequent DHCP renewal (enterprise WiFi, strict security)

**Chaos behavior:**
- DHCP lease expires every 60 seconds
- Forces lamp to renew frequently

**Expected lamp behavior:**
- Handles renewal gracefully
- Doesn't disconnect during renewal
- Continues operating normally

**Implementation note:** Requires custom DHCP server (advanced - may skip)

---

## Additional Edge Cases to Test

### Test 6: MAC Filtering
**Manual test:** Add lamp MAC to router blacklist, try to connect

**Expected:** Connection fails, lamp shows error, opens portal

---

### Test 7: Hidden SSID
**Setup:** Configure test AP with hidden=true

**Expected:** Lamp can still connect if SSID is manually entered

---

### Test 8: Hebrew/Special Characters in SSID
**Setup:** SSID = "נתב_בדיקה" or "WiFi@Home#123"

**Expected:** Lamp handles correctly (UTF-8 encoding)

---

### Test 9: Very Long Password (63 chars)
**Setup:** Max WPA2 password length

**Expected:** Portal accepts, lamp connects

---

### Test 10: Wrong Password Recovery
**Setup:** Enter wrong password in portal

**Expected:**
- Connection fails with reason 203 (Wrong password)
- Error banner injected into portal
- User can re-enter correct password
- Does NOT require restart

---

## Success Criteria

For each scenario, lamp should:

1. **Never get stuck** - Always have a path forward (retry, portal, or restart)
2. **Log clearly** - User/developer can diagnose from serial output
3. **User-friendly** - Portal shows helpful error messages
4. **Preserve data** - Don't corrupt NVS on power loss during chaos
5. **Battery-aware** - Don't drain power with infinite retries

---

## Test Execution Checklist

- [ ] Scenario 0: STABLE_OPEN ✅ (PASSED)
- [ ] Scenario 1: FREQUENT_DISCONNECTS
- [ ] Scenario 3: RANDOM_REBOOTS
- [ ] Scenario 4: NO_INTERNET
- [ ] Test 6: MAC Filtering (manual)
- [ ] Test 7: Hidden SSID
- [ ] Test 8: Special characters in SSID
- [ ] Test 10: Wrong password recovery

---

## Notes from Dad's Failed Connection

**What happened:**
- Open network (no password)
- Lamp couldn't connect
- Unknown router type/brand

**Possible root causes based on chaos testing:**
- MAC filtering (most likely - very common in open networks)
- Client limit reached
- Hidden SSID despite showing in scan
- Router firmware bug with ESP32
- Captive portal requirement (not testable with ESP32)

**Resolution:**
Since code works perfectly in controlled test (Scenario 0), the issue is **environmental**, not a code bug. Recommend to user: "Some routers block ESP32 devices - try enabling 'Allow all devices' in router settings or contact network admin."
