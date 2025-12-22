# Perfect Conditions Personalization Feature

## Concept
During registration, ask users to define their ideal surf conditions. Use this data to personalize dashboard messages and trigger special Arduino animations when conditions match their preferences.

## User Input (Registration Flow)

### Wave Height
- Perfect wave height: [dropdown/input]
  - Options: "Above X meters", "Between X-Y meters", "Below X meters", "Doesn't matter"

### Wind Speed
- Perfect wind speed: [dropdown/input]
  - Options: "Above X knots", "Between X-Y knots", "Below X knots", "Doesn't matter"

### Wind Direction
- Perfect wind direction: [multi-select checkboxes]
  - Options: N, NE, E, SE, S, SW, W, NW, "Doesn't matter"

### Wave Period
- Perfect wave period: [dropdown/input]
  - Options: "Above X seconds", "Between X-Y seconds", "Below X seconds", "Doesn't matter"

## Database Schema Changes

Add to `users` table:
```sql
-- Perfect condition preferences
perfect_wave_min FLOAT,
perfect_wave_max FLOAT,
perfect_wind_min FLOAT,
perfect_wind_max FLOAT,
perfect_wind_directions TEXT,  -- JSON array: ["N", "NE", "NW"] or "any"
perfect_period_min FLOAT,
perfect_period_max FLOAT
```

## Dashboard Personalization

### Hero Message Logic
Compare current conditions against user's perfect ranges (wave height, wind speed, wind direction, wave period):

**All 4 conditions match:**
- **"🔥 PERFECT CONDITIONS FOR YOU! GO SURF NOW!"** (green gradient, large text)

**Partial match (3/4 conditions):**
- **"✨ Almost perfect - {wave_height}, {wind_speed}, and {wind_direction} match your preferences!"**

**Partial match (2/4 conditions):**
- **"👍 Decent conditions - {wave_height} and {wind_speed} are in your sweet spot!"**

**No match or 1/4:**
- **"💤 Not your ideal conditions today"**

**Edge case:** If user selected "doesn't matter" for all four → treat as no preferences set, show generic status

## Arduino Integration

### Special Animation Trigger
When backend detects perfect conditions match (all 4 parameters match user preferences):
- Send special flag in API response: `"perfect_conditions": true`
- Arduino plays celebration animation (different from threshold blink)

### LED Display Options

**Option 1: Color Modulation (Recommended)**
- LEDs still display data proportionally (wave height/wind speed/period bars)
- Perfect conditions → all LEDs pulse with rainbow gradient overlay
- Data bars remain visible underneath the pulsing effect
- Implementation: `rainbow_pulse()` function cycles colors while maintaining LED count

**Option 2: Sequential Animation**
- Perfect conditions → play 3-second celebration animation (rainbow wave/sparkle)
- After animation → return to normal data display
- Repeat every 30 seconds while conditions remain perfect
- Implementation: Timer-based mode switch between `celebration_mode` and `data_mode`

### API Response Addition
```json
{
  "wave_height_m": 1.8,
  "wind_speed_mps": 5.2,
  "wind_direction_deg": 45,
  "wave_period_s": 10,
  "perfect_conditions": true,  // NEW FLAG - triggers celebration animation
  "perfect_match_count": 4     // How many out of 4 params matched (for partial matches)
}
```

### Match Logic (Backend)
```python
def check_perfect_conditions(user, conditions):
    matches = 0

    # Wave height check
    if user.perfect_wave_min and user.perfect_wave_max:
        if user.perfect_wave_min <= conditions.wave_height_m <= user.perfect_wave_max:
            matches += 1
    elif not user.perfect_wave_min:  # "doesn't matter"
        matches += 1

    # Wind speed check
    if user.perfect_wind_min and user.perfect_wind_max:
        wind_knots = conditions.wind_speed_mps * 1.944
        if user.perfect_wind_min <= wind_knots <= user.perfect_wind_max:
            matches += 1
    elif not user.perfect_wind_min:
        matches += 1

    # Wind direction check
    if user.perfect_wind_directions and user.perfect_wind_directions != "any":
        current_dir = degrees_to_cardinal(conditions.wind_direction_deg)
        if current_dir in json.loads(user.perfect_wind_directions):
            matches += 1
    elif user.perfect_wind_directions == "any":
        matches += 1

    # Wave period check
    if user.perfect_period_min and user.perfect_period_max:
        if user.perfect_period_min <= conditions.wave_period_s <= user.perfect_period_max:
            matches += 1
    elif not user.perfect_period_min:
        matches += 1

    return {
        "perfect_conditions": matches == 4,
        "perfect_match_count": matches
    }
```

## Implementation Priority
**Phase 1:** Database schema + registration form
**Phase 2:** Dashboard personalized messaging
**Phase 3:** Arduino celebration animation

## User Value
- Emotional connection: "The lamp knows what I like"
- Reduces cognitive load: Don't need to interpret data yourself
- Gamification: Waiting for that perfect day becomes exciting
- Differentiation: Not just a data display, it's YOUR surf companion

## Relationship with Existing Thresholds

**Two separate systems working together:**

1. **Thresholds (Alert System)** - "Pay attention!"
   - Wave threshold: "Blink when waves exceed 1.5m" (epic swell alert)
   - Wind threshold: "Blink when wind exceeds 22 knots" (too windy warning)
   - LED behavior: Blinking animation on all strips
   - Purpose: Upper limit warnings

2. **Perfect Conditions (Celebration System)** - "THIS IS YOUR DAY!"
   - All 4 parameters match user's ideal ranges
   - LED behavior: Rainbow pulse/celebration animation
   - Purpose: Personalized sweet spot detection

**Example:** Advanced surfer sets perfect = 1.5-2.5m waves, threshold = 1.5m
- 1.8m waves + matching wind/period → both systems trigger (blink + rainbow celebration)
- User knows: "Epic conditions AND they're in my sweet spot!"

## Edge Cases
1. User sets "doesn't matter" for all four → No personalization, show standard status
2. Impossible ranges (e.g., wave height 0-0) → Validation on registration form
3. User updates preferences later → Add settings page to edit perfect conditions
4. First-time users → Skip this during registration, add as optional "Set Your Perfect Day" prompt on dashboard
5. Wind direction critical → Offshore is usually preferred, allow multiple direction selections (e.g., N, NE, NW for certain beach orientations)
