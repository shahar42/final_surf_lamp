# Plan: Server-Side Max Value Configuration

## Motivation

Currently, `MAX_WAVE_HEIGHT` and `MAX_WIND_SPEED` are hardcoded in Arduino firmware. This creates challenges for:
- International markets with different wave/wind scales (Hawaii vs Mediterranean vs North Sea)
- Users wanting personalized sensitivity (beginners vs advanced surfers/kiters)
- Requiring firmware reflashing to change max values

**Solution:** Move LED count calculation from Arduino to server, allowing per-user max value configuration.

---

## Current Architecture

**Arduino Side:**
```cpp
#define MAX_WAVE_HEIGHT 3.0  // meters (hardcoded)
#define MAX_WIND_SPEED 30.0  // knots (hardcoded)

// Arduino receives raw values from server
float wave_height = 1.5;  // meters
float wind_speed = 15.0;  // knots

// Arduino calculates LED count
int wave_leds = (wave_height / MAX_WAVE_HEIGHT) * NUM_LEDS;
int wind_leds = (wind_speed / MAX_WIND_SPEED) * NUM_LEDS;
```

**Server Side:**
- Sends raw surf data: `wave_height_m`, `wind_speed_knots`
- No LED calculation logic

---

## New Architecture (Server-Side Calculation)

### 1. Database Changes

**Add columns to `users` table:**
```sql
ALTER TABLE users ADD COLUMN max_wave_height_m FLOAT DEFAULT 3.0;
ALTER TABLE users ADD COLUMN max_wind_speed_knots FLOAT DEFAULT 30.0;
```

**Rationale:**
- Per-user configuration (not per-arduino, since multiple arduinos share user preferences)
- Default values match current Arduino hardcoded values (backward compatibility)
- Units match existing fields (meters for waves, knots for wind)

### 2. API Changes

**Endpoint:** `/api/arduino/{arduino_id}/data`

**Current Response:**
```json
{
  "wave_height_m": 1.5,
  "wave_period_s": 8,
  "wind_speed_knots": 15,
  "wind_direction_deg": 180,
  "wave_threshold_m": 1.0,
  "wind_threshold_knots": 10
}
```

**New Response (backward compatible):**
```json
{
  "wave_height_m": 1.5,           // OLD - kept for old Arduinos
  "wave_period_s": 8,              // OLD - kept
  "wind_speed_knots": 15,          // OLD - kept for old Arduinos
  "wind_direction_deg": 180,       // OLD - kept
  "wave_threshold_m": 1.0,         // OLD - kept
  "wind_threshold_knots": 10,      // OLD - kept

  "wave_leds_count": 5,            // NEW - server calculated LED count
  "wind_leds_count": 8,            // NEW - server calculated LED count
  "max_wave_height_m": 3.0,        // NEW - user's max wave setting
  "max_wind_speed_knots": 30.0     // NEW - user's max wind setting
}
```

**CRITICAL: Server sends BOTH old AND new fields for backward compatibility**

**What happens with existing lamps:**
- **Old Arduinos** (current firmware):
  - Parse `wave_height_m`, `wind_speed_knots` (fields they know)
  - **Ignore** `wave_leds_count`, `wind_leds_count`, `max_*` (fields they don't recognize)
  - Calculate LEDs locally with hardcoded `MAX_WAVE_HEIGHT = 3.0` and `MAX_WIND_SPEED = 30.0`
  - Continue working exactly as before - **zero impact**

- **New Arduinos** (updated firmware):
  - Parse `wave_leds_count`, `wind_leds_count` (pre-calculated by server)
  - Use those values directly (no local calculation needed)
  - Respect user's custom max values set in dashboard
  - Ignore raw `wave_height_m`, `wind_speed_knots` for LED calculation

**Result:** Old lamps keep working forever with no changes required. New firmware is optional upgrade for per-user customization.

**Server Calculation Logic:**
```python
# In /api/arduino/{arduino_id}/data endpoint
wave_leds_count = min(
    int((current_wave_height / user.max_wave_height_m) * NUM_LEDS),
    NUM_LEDS
)

wind_leds_count = min(
    int((current_wind_speed / user.max_wind_speed_knots) * NUM_LEDS),
    NUM_LEDS
)
```

### 3. Arduino Changes

**New Firmware (v2):**
```cpp
// Parse new fields from JSON
int wave_leds_count = doc["wave_leds_count"] | -1;  // -1 = not present
int wind_leds_count = doc["wind_leds_count"] | -1;

if (wave_leds_count != -1 && wind_leds_count != -1) {
    // NEW: Use server-calculated LED counts
    lightWaveLEDs(wave_leds_count);
    lightWindLEDs(wind_leds_count);
} else {
    // FALLBACK: Old behavior (for backward compatibility)
    float wave_height = doc["wave_height_m"];
    float wind_speed = doc["wind_speed_knots"];
    int wave_leds = (wave_height / MAX_WAVE_HEIGHT) * NUM_LEDS;
    int wind_leds = (wind_speed / MAX_WIND_SPEED) * NUM_LEDS;
    lightWaveLEDs(wave_leds);
    lightWindLEDs(wind_leds);
}
```

**Deployment Strategy:**
- Server deploys first (adds new fields, Arduino ignores them)
- New Arduinos use server LED counts
- Old Arduinos continue using local calculation (graceful degradation)
- No forced firmware update required

### 4. Dashboard Changes

**Add User Settings Section:**

**UI Location:** Dashboard → User Settings (below theme/units)

**New Controls:**
```
┌─────────────────────────────────────┐
│ Wave & Wind Scale Settings          │
├─────────────────────────────────────┤
│ Max Wave Height (meters)             │
│ [====o==========] 3.0m               │
│ Range: 1.0m - 10.0m                  │
│                                      │
│ Max Wind Speed (knots)               │
│ [=======o=======] 30 knots           │
│ Range: 10 - 60 knots                 │
│                                      │
│ [Save Settings]                      │
└─────────────────────────────────────┘
```

**Tooltips:**
- Max Wave Height: "The wave height that lights all LEDs. Lower = more sensitive."
- Max Wind Speed: "The wind speed that lights all LEDs. Lower = more sensitive."

**Update Endpoint:** `POST /api/user/preferences`
```json
{
  "max_wave_height_m": 3.0,
  "max_wind_speed_knots": 30.0
}
```

---

## Implementation Checklist

### Phase 1: Database & Backend
- [ ] Add `max_wave_height_m` column to `users` table (default: 3.0)
- [ ] Add `max_wind_speed_knots` column to `users` table (default: 30.0)
- [ ] Modify `/api/arduino/{arduino_id}/data` to calculate LED counts
- [ ] Add new response fields: `wave_leds_count`, `wind_leds_count`, `max_wave_height_m`, `max_wind_speed_knots`
- [ ] Test backward compatibility with existing Arduinos

### Phase 2: Dashboard UI
- [ ] Add max value sliders to user settings section
- [ ] Create `POST /api/user/preferences` endpoint for updating max values
- [ ] Add helpful tooltips explaining sensitivity impact
- [ ] Test UI updates and verify API integration

### Phase 3: Arduino Firmware (Optional)
- [ ] Modify Arduino code to parse `wave_leds_count` / `wind_leds_count`
- [ ] Implement fallback to local calculation if fields missing
- [ ] Test with server-side LED counts
- [ ] Test backward compatibility (old server response)
- [ ] Deploy firmware update (non-breaking, optional)

---

## Benefits

1. **Per-User Customization**
   - Hawaii surfers: Higher max wave height (e.g., 5m)
   - Mediterranean kiters: Lower max wind speed (e.g., 20 knots)
   - Beginners: More sensitive scale for earlier detection

2. **No Reflashing Required**
   - Users change settings via dashboard instantly
   - No technical knowledge needed
   - No physical access to lamp required

3. **A/B Testing & Data Collection**
   - Track which max values users prefer by region
   - Optimize defaults for new markets
   - Gather feedback on sensitivity preferences

4. **Backward Compatibility**
   - Old Arduinos continue working with local calculation
   - New Arduinos use server-calculated values
   - Graceful degradation if server fields missing

---

## Regional Max Value Suggestions

| Region          | Max Wave Height | Max Wind Speed | Rationale                          |
|-----------------|-----------------|----------------|------------------------------------|
| Mediterranean   | 2.0m            | 25 knots       | Smaller swell window, lighter winds |
| North Sea       | 4.0m            | 40 knots       | Larger swells, stronger winds       |
| Hawaii          | 5.0m            | 30 knots       | Big wave surf culture               |
| Caribbean       | 2.5m            | 35 knots       | Moderate swells, strong trade winds |
| California      | 3.0m            | 30 knots       | Varied conditions (current default) |

**Note:** These are starting suggestions. Users can customize further based on personal preference.

---

## Open Questions

1. Should max values be per-arduino or per-user?
   - **Recommendation:** Per-user (simpler, most users have one location)
   - **Alternative:** Per-arduino (if user has lamps in multiple regions)

2. Should we set regional defaults during registration?
   - **Recommendation:** Yes - detect location and suggest appropriate max values
   - **Implementation:** Map `user.location` → regional preset during account creation

3. Should we limit how low max values can go?
   - **Recommendation:** Yes - enforce minimums (e.g., 1.0m waves, 10 knots wind)
   - **Rationale:** Too low = all LEDs always lit (useless)

4. Should we show "scale sensitivity" instead of raw max values?
   - **Recommendation:** Future enhancement - slider from "Beginner" to "Expert"
   - **Behind the scenes:** Maps to max value ranges
   - **Benefit:** More intuitive for non-technical users

---

## Future Enhancements

- **Smart Defaults:** Auto-adjust max values based on 30-day historical data for user's location
- **Preset Modes:** "Beginner", "Intermediate", "Expert" sensitivity levels
- **Visual Preview:** Show example LED patterns for current conditions with different max values
- **Community Sharing:** See what max values other users in your area use
