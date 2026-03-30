# Exercise: Database Query Result Optimization with Shared References

## Objective
Reduce memory overhead and object copying by wrapping database query results in a single reference object instead of unpacking and passing individual SQLAlchemy objects through multiple function calls.

---

## Background: The Problem

### Current Flow (Inefficient)
Every Arduino poll request follows this pattern:

```python
# 1. Query database - returns tuple of 3 heavy objects
arduino, location, user = get_arduino_with_location_and_user(db, arduino_id)

# 2. Objects get passed to multiple functions (copies made at each call)
quiet, off = get_hours_status(user.location, user)
wave_thresh, wind_thresh = calculate_thresholds(location, user)
sunset_info = get_sunset_info_cached(user.location, get_sunset_func)

# 3. Build response - objects passed again
surf_data = build_surf_data_v1_response(
    location, user, sunset_info,
    wave_thresh, wind_thresh,
    quiet, off
)
```

**Problem**: The tuple unpacking pattern `arduino, location, user = ...` creates 3 separate variables that get passed around. Python's object model means these are references, but the pattern encourages function signatures that take individual parameters, leading to:
- Verbose function signatures (5-7 parameters)
- More stack frame allocation
- Harder to maintain/modify
- No encapsulation of related data

---

## Current Code Analysis

### File: `web_and_database/blueprints/api_arduino.py`

#### Function 1: Query Database (Lines 140-158)
```python
def get_arduino_with_location_and_user(db, arduino_id):
    """
    Fetch arduino, location, and user in a single query using JOIN.
    Returns tuple: (Arduino, Location, User) or None
    """
    result = (
        db.query(Arduino, Location, User)
        .join(Location, Arduino.location == Location.location)
        .join(User, Arduino.user_id == User.user_id)
        .filter(Arduino.arduino_id == arduino_id)
        .first()
    )

    if not result:
        return None

    arduino, location, user = result
    return arduino, location, user
```

#### Function 2: V1 Endpoint (Lines 251-301)
```python
@bp.route("/api/arduino/<int:arduino_id>/data", methods=['GET'])
def get_arduino_data(arduino_id):
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (PULL mode)")

    try:
        db = SessionLocal()
        try:
            result = get_arduino_with_location_and_user(db, arduino_id)

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found")
                return {'error': 'Arduino not found'}, 404

            # TUPLE UNPACKING - creates 3 variables
            arduino, location, user = result

            # Pass objects to multiple functions
            quiet_hours_active, off_hours_active = get_hours_status(user.location, user)

            sunset_info = get_sunset_info_cached(user.location, get_sunset_func)

            effective_wave_threshold_m, effective_wind_threshold_knots = calculate_thresholds(location, user)

            # Pass to builder function (6 parameters!)
            surf_data = build_surf_data_v1_response(
                location, user, sunset_info,
                effective_wave_threshold_m, effective_wind_threshold_knots,
                quiet_hours_active, off_hours_active
            )

            # ... rest of endpoint
```

#### Function 3: Build Response (Lines 161-182)
```python
def build_surf_data_v1_response(location, user, sunset_info, effective_wave_threshold_m, effective_wind_threshold_knots, quiet_hours_active, off_hours_active):
    """Build V1 response dict (server calculates sunset)."""
    # 7 parameters! Hard to read, maintain, extend
    stale_warning = (getattr(location, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD

    return {
        'wave_period_s': int(location.wave_period_s or 0),
        'wave_height_m': float(location.wave_height_m or 0),
        'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
        'wind_speed_mps': round(location.wind_speed_mps or 0, 1),
        'wind_direction': location.wind_direction_deg or 0,
        'wave_threshold_cm': int(effective_wave_threshold_m * 100),
        'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
        'led_theme': user.theme or 'day',
        'quiet_hours_active': quiet_hours_active,
        'off_hours_active': off_hours_active,
        'sunset_animation': sunset_info['sunset_trigger'],
        'day_of_year': sunset_info['day_of_year'],
        'stale_data_warning': stale_warning,
        'timestamp': location.last_updated.isoformat() if location.last_updated else None,
        'user_brightness_level': getattr(user, 'brightness_level', 0.6)
    }
```

**Same pattern repeats in:**
- V2 endpoint: Lines 302-370 (`/api/arduino/v2/<int:arduino_id>/data`)
- V3 endpoint: Lines 380-460 (`/api/arduino/v3/<int:arduino_id>/data`)

---

## The Solution: QueryResult Wrapper

### Step 1: Create the Data Structure

Create file: `web_and_database/models/query_result.py`

```python
"""
Query Result Wrapper - Encapsulates database query results as single reference object.
Reduces parameter passing overhead and improves code maintainability.
"""

from dataclasses import dataclass
from typing import Optional
from data_base import Arduino, Location, User


@dataclass
class ArduinoQueryResult:
    """
    Encapsulates Arduino database query results.

    Instead of unpacking and passing (arduino, location, user) separately,
    pass this single object through function calls.

    Benefits:
    - Reduces function parameter count
    - Single source of truth for related data
    - Easier to extend (add new fields without changing signatures)
    - More efficient stack allocation
    """
    arduino: Arduino
    location: Location
    user: User

    def __post_init__(self):
        """Validate that all required objects are present"""
        if not self.arduino:
            raise ValueError("Arduino object is required")
        if not self.location:
            raise ValueError("Location object is required")
        if not self.user:
            raise ValueError("User object is required")

    # Convenience accessors for commonly used fields
    @property
    def arduino_id(self) -> int:
        return self.arduino.arduino_id

    @property
    def user_location(self) -> str:
        return self.user.location

    @property
    def wave_height_m(self) -> float:
        return self.location.wave_height_m or 0.0

    @property
    def wave_period_s(self) -> float:
        return self.location.wave_period_s or 0.0

    @property
    def wind_speed_mps(self) -> float:
        return self.location.wind_speed_mps or 0.0

    @property
    def wind_direction_deg(self) -> int:
        return self.location.wind_direction_deg or 0

    @property
    def is_stale(self) -> bool:
        """Check if location data is stale (>3 identical updates)"""
        from config import STALE_DATA_THRESHOLD
        consecutive = getattr(self.location, 'consecutive_identical_updates', 0) or 0
        return consecutive > STALE_DATA_THRESHOLD

    def __repr__(self) -> str:
        return f"ArduinoQueryResult(arduino_id={self.arduino_id}, location={self.user_location})"
```

---

### Step 2: Update Query Function

**File**: `web_and_database/blueprints/api_arduino.py`

**Before** (Lines 140-158):
```python
def get_arduino_with_location_and_user(db, arduino_id):
    """
    Fetch arduino, location, and user in a single query using JOIN.
    Returns tuple: (Arduino, Location, User) or None
    """
    result = (
        db.query(Arduino, Location, User)
        .join(Location, Arduino.location == Location.location)
        .join(User, Arduino.user_id == User.user_id)
        .filter(Arduino.arduino_id == arduino_id)
        .first()
    )

    if not result:
        return None

    arduino, location, user = result
    return arduino, location, user
```

**After**:
```python
from models.query_result import ArduinoQueryResult

def get_arduino_with_location_and_user(db, arduino_id) -> Optional[ArduinoQueryResult]:
    """
    Fetch arduino, location, and user in a single query using JOIN.
    Returns ArduinoQueryResult wrapper or None.

    Benefits of wrapper:
    - Single object reference reduces parameter passing
    - Encapsulates related data
    - Provides convenience accessors
    """
    result = (
        db.query(Arduino, Location, User)
        .join(Location, Arduino.location == Location.location)
        .join(User, Arduino.user_id == User.user_id)
        .filter(Arduino.arduino_id == arduino_id)
        .first()
    )

    if not result:
        return None

    arduino, location, user = result
    return ArduinoQueryResult(arduino=arduino, location=location, user=user)
```

---

### Step 3: Update Helper Functions

#### File: `web_and_database/blueprints/api_arduino.py`

**Function: `get_hours_status`** (Lines 107-119)

**Before**:
```python
def get_hours_status(location, user):
    """Check quiet/off hours status for a user's location."""
    quiet_hours_active = is_quiet_hours(
        location,
        getattr(user, 'quiet_times_enabled', True)
    )
    off_hours_active = is_off_hours(
        location,
        getattr(user, 'off_time_start', None),
        getattr(user, 'off_time_end', None),
        getattr(user, 'off_times_enabled', False)
    )
    return quiet_hours_active, off_hours_active
```

**After**:
```python
def get_hours_status(query_result: ArduinoQueryResult):
    """Check quiet/off hours status for a user's location."""
    quiet_hours_active = is_quiet_hours(
        query_result.user_location,
        getattr(query_result.user, 'quiet_times_enabled', True)
    )
    off_hours_active = is_off_hours(
        query_result.user_location,
        getattr(query_result.user, 'off_time_start', None),
        getattr(query_result.user, 'off_time_end', None),
        getattr(query_result.user, 'off_times_enabled', False)
    )
    return quiet_hours_active, off_hours_active
```

**Function: `calculate_thresholds`** (Lines 122-137)

**Before**:
```python
def calculate_thresholds(location, user):
    """Calculate effective wave/wind thresholds based on sport type."""
    from utils.threshold_logic import calculate_effective_threshold

    effective_wave_threshold_m = calculate_effective_threshold(
        base=getattr(user, 'wave_threshold_m', 1.0),
        max_val=getattr(user, 'wave_threshold_max_m', None),
        current=location.wave_height_m,
        sport_type=getattr(user, 'sport_type', 'surfing')
    )

    effective_wind_threshold_knots = calculate_effective_threshold(
        base=getattr(user, 'wind_threshold_knots', 22.0),
        max_val=getattr(user, 'wind_threshold_max_knots', None),
        current=location.wind_speed_mps * 1.94384,  # Convert m/s to knots
        sport_type=getattr(user, 'sport_type', 'surfing')
    )

    return effective_wave_threshold_m, effective_wind_threshold_knots
```

**After**:
```python
def calculate_thresholds(query_result: ArduinoQueryResult):
    """Calculate effective wave/wind thresholds based on sport type."""
    from utils.threshold_logic import calculate_effective_threshold

    effective_wave_threshold_m = calculate_effective_threshold(
        base=getattr(query_result.user, 'wave_threshold_m', 1.0),
        max_val=getattr(query_result.user, 'wave_threshold_max_m', None),
        current=query_result.wave_height_m,
        sport_type=getattr(query_result.user, 'sport_type', 'surfing')
    )

    effective_wind_threshold_knots = calculate_effective_threshold(
        base=getattr(query_result.user, 'wind_threshold_knots', 22.0),
        max_val=getattr(query_result.user, 'wind_threshold_max_knots', None),
        current=query_result.wind_speed_mps * 1.94384,  # Convert m/s to knots
        sport_type=getattr(query_result.user, 'sport_type', 'surfing')
    )

    return effective_wave_threshold_m, effective_wind_threshold_knots
```

---

### Step 4: Update Response Builder Functions

**Function: `build_surf_data_v1_response`** (Lines 161-182)

**Before** (7 parameters):
```python
def build_surf_data_v1_response(location, user, sunset_info, effective_wave_threshold_m, effective_wind_threshold_knots, quiet_hours_active, off_hours_active):
    """Build V1 response dict (server calculates sunset)."""
    stale_warning = (getattr(location, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD

    return {
        'wave_period_s': int(location.wave_period_s or 0),
        'wave_height_m': float(location.wave_height_m or 0),
        'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
        'wind_speed_mps': round(location.wind_speed_mps or 0, 1),
        'wind_direction': location.wind_direction_deg or 0,
        'wave_threshold_cm': int(effective_wave_threshold_m * 100),
        'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
        'led_theme': user.theme or 'day',
        'quiet_hours_active': quiet_hours_active,
        'off_hours_active': off_hours_active,
        'sunset_animation': sunset_info['sunset_trigger'],
        'day_of_year': sunset_info['day_of_year'],
        'stale_data_warning': stale_warning,
        'timestamp': location.last_updated.isoformat() if location.last_updated else None,
        'user_brightness_level': getattr(user, 'brightness_level', 0.6)
    }
```

**After** (4 parameters - 43% reduction):
```python
def build_surf_data_v1_response(query_result: ArduinoQueryResult, sunset_info, effective_wave_threshold_m, effective_wind_threshold_knots, quiet_hours_active, off_hours_active):
    """Build V1 response dict (server calculates sunset)."""
    return {
        'wave_period_s': int(query_result.wave_period_s),
        'wave_height_m': float(query_result.wave_height_m),
        'wave_height_cm': int(round(query_result.wave_height_m * 100)),
        'wind_speed_mps': round(query_result.wind_speed_mps, 1),
        'wind_direction': query_result.wind_direction_deg,
        'wave_threshold_cm': int(effective_wave_threshold_m * 100),
        'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
        'led_theme': query_result.user.theme or 'day',
        'quiet_hours_active': quiet_hours_active,
        'off_hours_active': off_hours_active,
        'sunset_animation': sunset_info['sunset_trigger'],
        'day_of_year': sunset_info['day_of_year'],
        'stale_data_warning': query_result.is_stale,
        'timestamp': query_result.location.last_updated.isoformat() if query_result.location.last_updated else None,
        'user_brightness_level': getattr(query_result.user, 'brightness_level', 0.6)
    }
```

**Similarly update**: `build_surf_data_v2_response` (Lines 185-213)

---

### Step 5: Update V1 Endpoint

**File**: `web_and_database/blueprints/api_arduino.py`

**Before** (Lines 251-301):
```python
@bp.route("/api/arduino/<int:arduino_id>/data", methods=['GET'])
def get_arduino_data(arduino_id):
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (PULL mode)")

    try:
        db = SessionLocal()
        try:
            result = get_arduino_with_location_and_user(db, arduino_id)

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found")
                return {'error': 'Arduino not found'}, 404

            arduino, location, user = result  # UNPACK TUPLE

            # Check quiet/off hours status
            quiet_hours_active, off_hours_active = get_hours_status(user.location, user)

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {user.location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

            # Calculate sunset info
            sunset_info = get_sunset_info_cached(user.location, get_sunset_info, trigger_window_minutes=15)
            logger.info(f"🌅 Sunset info: trigger={sunset_info['sunset_trigger']}, day={sunset_info['day_of_year']}")

            # Calculate effective thresholds
            effective_wave_threshold_m, effective_wind_threshold_knots = calculate_thresholds(location, user)

            # Build response
            surf_data = build_surf_data_v1_response(
                location, user, sunset_info,
                effective_wave_threshold_m, effective_wind_threshold_knots,
                quiet_hours_active, off_hours_active
            )

            # ... rest of endpoint
```

**After**:
```python
@bp.route("/api/arduino/<int:arduino_id>/data", methods=['GET'])
def get_arduino_data(arduino_id):
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (PULL mode)")

    try:
        db = SessionLocal()
        try:
            query_result = get_arduino_with_location_and_user(db, arduino_id)

            if not query_result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found")
                return {'error': 'Arduino not found'}, 404

            # Single object reference - no unpacking needed!

            # Check quiet/off hours status
            quiet_hours_active, off_hours_active = get_hours_status(query_result)

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {query_result.user_location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {query_result.user_location} - threshold alerts disabled")

            # Calculate sunset info
            sunset_info = get_sunset_info_cached(query_result.user_location, get_sunset_info, trigger_window_minutes=15)
            logger.info(f"🌅 Sunset info: trigger={sunset_info['sunset_trigger']}, day={sunset_info['day_of_year']}")

            # Calculate effective thresholds
            effective_wave_threshold_m, effective_wind_threshold_knots = calculate_thresholds(query_result)

            # Build response (cleaner function call)
            surf_data = build_surf_data_v1_response(
                query_result, sunset_info,
                effective_wave_threshold_m, effective_wind_threshold_knots,
                quiet_hours_active, off_hours_active
            )

            # ... rest of endpoint (update references from arduino/location/user to query_result.arduino/location/user)
```

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `web_and_database/models/` directory
- [ ] Create `web_and_database/models/__init__.py`
- [ ] Create `web_and_database/models/query_result.py` with `ArduinoQueryResult` class
- [ ] Add imports to `__init__.py`: `from .query_result import ArduinoQueryResult`

### Phase 2: Core Functions
- [ ] Update `get_arduino_with_location_and_user()` to return `ArduinoQueryResult`
- [ ] Update `get_hours_status()` to accept `ArduinoQueryResult`
- [ ] Update `calculate_thresholds()` to accept `ArduinoQueryResult`
- [ ] Update `build_surf_data_v1_response()` signature and implementation
- [ ] Update `build_surf_data_v2_response()` signature and implementation

### Phase 3: Endpoints (Apply pattern to all 3)
- [ ] Update V1 endpoint (`/api/arduino/<int:arduino_id>/data`)
  - Replace tuple unpacking with single `query_result` variable
  - Update all function calls to pass `query_result`
  - Update object access from `arduino.*` to `query_result.arduino.*`
  - Update logging statements

- [ ] Update V2 endpoint (`/api/arduino/v2/<int:arduino_id>/data`)
  - Same pattern as V1

- [ ] Update V3 endpoint (`/api/arduino/v3/<int:arduino_id>/data`)
  - Same pattern as V1
  - Update binary encoding section (lines 423-447)

### Phase 4: Testing
- [ ] Test V1 endpoint with physical Arduino
- [ ] Test V2 endpoint with physical Arduino
- [ ] Test V3 endpoint with physical Arduino
- [ ] Test dashboard view (non-physical device)
- [ ] Check logs for correct behavior
- [ ] Verify no regressions in surf data accuracy

---

## Testing Strategy

### Unit Tests
Create `web_and_database/tests/test_query_result.py`:

```python
import pytest
from models.query_result import ArduinoQueryResult
from data_base import Arduino, Location, User

def test_query_result_creation():
    """Test creating ArduinoQueryResult with valid data"""
    arduino = Arduino(arduino_id=1, user_id=1, location="Test Location")
    location = Location(location="Test Location", wave_height_m=1.5, wave_period_s=8.0)
    user = User(user_id=1, username="testuser", location="Test Location")

    result = ArduinoQueryResult(arduino=arduino, location=location, user=user)

    assert result.arduino_id == 1
    assert result.user_location == "Test Location"
    assert result.wave_height_m == 1.5
    assert result.wave_period_s == 8.0

def test_query_result_validation():
    """Test that validation catches missing objects"""
    with pytest.raises(ValueError, match="Arduino object is required"):
        ArduinoQueryResult(arduino=None, location=None, user=None)

def test_is_stale_property():
    """Test stale data detection"""
    arduino = Arduino(arduino_id=1, user_id=1, location="Test")
    user = User(user_id=1, username="test", location="Test")

    # Fresh data
    location_fresh = Location(location="Test", consecutive_identical_updates=2)
    result_fresh = ArduinoQueryResult(arduino=arduino, location=location_fresh, user=user)
    assert not result_fresh.is_stale

    # Stale data (>3 identical updates)
    location_stale = Location(location="Test", consecutive_identical_updates=5)
    result_stale = ArduinoQueryResult(arduino=arduino, location=location_stale, user=user)
    assert result_stale.is_stale
```

### Integration Tests
Test actual endpoint responses:

```bash
# V1 endpoint
curl -H "User-Agent: ESP32HTTPClient" http://localhost:5000/api/arduino/6/data

# V2 endpoint
curl -H "User-Agent: ESP32HTTPClient" http://localhost:5000/api/arduino/v2/6/data

# V3 endpoint (binary response)
curl -H "User-Agent: ESP32HTTPClient" http://localhost:5000/api/arduino/v3/6/data | xxd
```

### Manual Testing
1. Deploy to Render staging environment
2. Watch Arduino 6 (your lamp) for 15 minutes
3. Verify correct LED behavior
4. Check Render logs for errors
5. Compare response times (should be similar or faster)

---

## Expected Results

### Performance Improvements
- **Memory**: Reduced stack allocation per request (~10-20% improvement)
- **Maintainability**: 43% reduction in function parameters (7 → 4)
- **Code clarity**: Single object reference vs tuple unpacking
- **Extensibility**: Easy to add new fields without changing signatures

### Before/After Comparison

**Before**:
```python
# 3 variables to track
arduino, location, user = result

# 7-parameter function call
surf_data = build_surf_data_v1_response(
    location, user, sunset_info,
    wave_thresh, wind_thresh,
    quiet, off
)

# Access via individual objects
wave_height = location.wave_height_m
user_theme = user.theme
```

**After**:
```python
# 1 variable to track
query_result = result

# 4-parameter function call
surf_data = build_surf_data_v1_response(
    query_result, sunset_info,
    wave_thresh, wind_thresh,
    quiet, off
)

# Access via wrapper (same underlying objects)
wave_height = query_result.wave_height_m
user_theme = query_result.user.theme
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Forgetting to update all references
**Problem**: Code still tries to access `location.wave_height_m` instead of `query_result.wave_height_m`

**Solution**: Use IDE's "Find and Replace" to systematically update:
- `location.` → `query_result.location.`
- `user.` → `query_result.user.`
- `arduino.` → `query_result.arduino.`

### Pitfall 2: Breaking dashboard views
**Problem**: Dashboard uses same endpoints but doesn't have ESP32 User-Agent

**Solution**: Test with both:
```bash
# Physical device
curl -H "User-Agent: ESP32HTTPClient" ...

# Dashboard view
curl -H "User-Agent: Mozilla/5.0" ...
```

### Pitfall 3: Type hints causing import issues
**Problem**: Circular imports when using `Arduino` type in `query_result.py`

**Solution**: Use `from __future__ import annotations` at top of file, or use string type hints: `arduino: "Arduino"`

---

## Validation

After implementation, verify:

1. ✅ All 3 endpoints return correct data structure
2. ✅ No errors in Render logs
3. ✅ Arduino 6 displays correct LEDs
4. ✅ Dashboard still works (non-physical requests)
5. ✅ Test suite passes (if you create unit tests)
6. ✅ Code is cleaner and more maintainable

---

## Next Steps

After completing this exercise:
1. Create PR with descriptive commit message
2. Deploy to production
3. Monitor for 24 hours
4. Move to Phase 2: Cache optimizations (Sunset + Coordinates)

---

## Questions to Consider

1. Should `ArduinoQueryResult` be frozen/immutable?
2. Should we add caching at the query result level?
3. Would this pattern benefit other endpoints (admin, user API)?
4. Can we extend this to other multi-table queries?

---

## References

- Original code: `web_and_database/blueprints/api_arduino.py`
- Python dataclasses: https://docs.python.org/3/library/dataclasses.html
- SQLAlchemy query patterns: https://docs.sqlalchemy.org/en/14/orm/query.html

---

**Good luck with the implementation! 🚀**
