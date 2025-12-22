# WiFi Configuration Portal Timeout Changes

**Changed**: All WiFi configuration portal timeouts to 17 minutes

---

## What Was Changed

### Before → After

**First Setup (no credentials)**:
- ❌ 10 minutes → ✅ 17 minutes
- When lamp boots for first time or after WiFi reset
- Portal opens: `SurfLamp-Setup` with 17-minute timeout

**Router Reboot Scenario**:
- ❌ Exponential backoff capped at 5 minutes → ✅ Capped at 17 minutes
- Sequence: 30s, 60s, 120s, 240s, 480s, 960s → capped at 1020s (17 min)

**Credential Retry**:
- ❌ 30 seconds quick retries → ✅ 17 minutes
- When connection fails with saved credentials
- Gives user more time to fix issues

**Final Fallback**:
- ✅ Still indefinite (timeout = 0)
- Last retry attempt waits forever until user configures
- No change - this was already indefinite

---

## What Was NOT Changed

**HTTP Request Timeout**:
- ⏱️ Still 15 seconds (`HTTP_TIMEOUT_MS = 15000`)
- Used for server API requests
- Should stay short (network requests shouldn't hang for 17 minutes)

**WiFi Connection Timeout**:
- ⏱️ Still 30 seconds (`WIFI_TIMEOUT = 30`)
- Individual connection attempt duration
- Different from portal timeout (this is connection handshake time)

---

## User Experience Impact

### Scenario 1: Boot Button Pressed (WiFi Reset)
**Before**:
1. Credentials wiped
2. ESP restarts
3. AP opens for 10 minutes
4. If timeout: restart → AP opens again for 10 minutes (loop)

**After**:
1. Credentials wiped
2. ESP restarts
3. AP opens for **17 minutes**
4. If timeout: restart → AP opens again for 17 minutes (loop)

**Result**: User gets more time per session before automatic restart

### Scenario 2: First Time Setup (New Lamp)
**Before**:
- 10 minutes to scan WiFi, enter password, connect

**After**:
- 17 minutes to scan WiFi, enter password, connect

**Result**: Less pressure on user during setup

### Scenario 3: Connection Failure (Bad Credentials)
**Before**:
- 30 seconds to fix and retry (very short)

**After**:
- 17 minutes to realize issue and reconfigure

**Result**: Much better troubleshooting window

---

## Code Changes

**File**: `arduino_code/lamp_refractored/WiFiHandler.cpp`

**Lines Changed**:
- Line 194: `600` → `1020` (first setup)
- Line 208: `300` → `1020` (router reboot cap)
- Line 214: `30` → `1020` (credential retry)

**Total Changes**: 3 timeout values updated

---

## Rationale

**Why 17 minutes?**
- Long enough for user to:
  - Find phone/computer
  - Connect to SurfLamp-Setup AP
  - Open browser (or wait for captive portal redirect)
  - Scan for WiFi networks (can take 30-60 seconds)
  - Enter password carefully
  - Troubleshoot if password wrong
  - Try different network if first fails

**Why not indefinite?**
- Prevents stuck AP state if something goes wrong
- Auto-restart gives fresh chance to connect
- User can always manually restart if needed

**Why keep final retry indefinite?**
- After multiple 17-minute sessions, clearly something is wrong
- Final attempt lets user fix manually without time pressure
- Safety net to prevent infinite restart loops

---

## Testing Checklist

- [ ] Press boot button → WiFi reset
- [ ] Serial shows "Opening configuration portal for 17 minutes"
- [ ] AP stays open for full 17 minutes if not configured
- [ ] After 17 minutes: ESP restarts and reopens AP
- [ ] User can connect and configure within 17-minute window
- [ ] After successful config: normal operation resumes

---

**Change complete and pushed to GitHub.**
