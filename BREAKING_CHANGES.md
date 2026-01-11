# Schema Refactor - Breaking Changes Documentation

## Overview
Migration from lamp-centric to arduino-centric + location-centric architecture.

**Core principle:** One API call per location updates `locations` table → all arduinos at that location inherit the data.

---

## Database Schema Changes

### DELETED Tables
```sql
❌ lamps              → Replaced by arduinos
❌ current_conditions → Merged into locations
❌ daily_usage        → Replaced by locations.wave_api_url/wind_api_url
❌ location_websites  → Replaced by locations table
❌ usage_lamps        → Replaced by locations table
```

### NEW Tables
```sql
✅ arduinos (arduino_id PK, user_id FK, location FK)
✅ locations (location PK, wave_api_url, wind_api_url, surf conditions data)
```

### MODIFIED Tables
```sql
users: No changes (location column stays as dashboard default view)
error_reports: lamp_id → arduino_id (column rename)
```

---

## Code Breaking Changes by File

### 1. **web_and_database/data_base.py**
**ORM Models to Update:**

```python
# DELETE
class Lamp(Base):
    __tablename__ = 'lamps'
    lamp_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    arduino_id = Column(Integer, nullable=True)
    last_updated = Column(DateTime)

class CurrentConditions(Base):
    __tablename__ = 'current_conditions'
    lamp_id = Column(Integer, ForeignKey('lamps.lamp_id'), primary_key=True)
    wave_height_m = Column(Float)
    wave_period_s = Column(Float)
    wind_speed_mps = Column(Float)
    wind_direction_deg = Column(Integer)
    last_updated = Column(DateTime)

# ADD
class Arduino(Base):
    __tablename__ = 'arduinos'
    arduino_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    location = Column(String(255), ForeignKey('locations.location'), nullable=False)
    last_poll_time = Column(DateTime, default=datetime.utcnow)

class Location(Base):
    __tablename__ = 'locations'
    location = Column(String(255), primary_key=True)
    wave_api_url = Column(Text, nullable=False)
    wind_api_url = Column(Text, nullable=False)
    wave_height_m = Column(Float)
    wave_period_s = Column(Float)
    wind_speed_mps = Column(Float)
    wind_direction_deg = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow)
```

---

### 2. **web_and_database/blueprints/api_arduino.py**
**Query Pattern Changes:**

**OLD:**
```python
# Line 102-106
result = db.query(Lamp, CurrentConditions, User).select_from(Lamp) \
    .outerjoin(CurrentConditions, Lamp.lamp_id == CurrentConditions.lamp_id) \
    .join(User, Lamp.user_id == User.user_id) \
    .filter(Lamp.arduino_id == arduino_id) \
    .first()

lamp, conditions, user = result
```

**NEW:**
```python
result = db.query(Arduino, Location, User).select_from(Arduino) \
    .join(User, Arduino.user_id == User.user_id) \
    .join(Location, Arduino.location == Location.location) \
    .filter(Arduino.arduino_id == arduino_id) \
    .first()

arduino, location, user = result
```

**Data Access Changes:**
```python
# OLD: conditions.wave_height_m
# NEW: location.wave_height_m

# OLD: lamp.last_updated
# NEW: arduino.last_poll_time

# OLD: lamp.lamp_id
# NEW: arduino.arduino_id (same value now, no separate ID)
```

**Affected Lines:**
- Line 7: Import `Arduino, Location` instead of `Lamp, CurrentConditions`
- Lines 50, 102-106, 198-202, 324-326: Update queries
- Lines 58, 64, 70: Remove `lamp.lamp_id` references
- Lines 135-152, 238-256: Check `if not location:` instead of `if not conditions:`
- Lines 156-170, 258-274: Use `location.wave_height_m` instead of `conditions.wave_height_m`
- Lines 173, 277: Update `arduino.last_poll_time` instead of `lamp.last_updated`
- Lines 332-346: Status endpoint returns `arduino_id` (no separate lamp_id)
- Line 384: `error_reports.lamp_id` → `error_reports.arduino_id`

---

### 3. **surf-lamp-processor/lamp_repository.py**
**CRITICAL: Complete rewrite needed**

**OLD Functions (DELETE):**
```python
get_location_based_configs()  # Queries usage_lamps table
get_lamps_for_location()      # Returns lamp_id
update_lamp_timestamp()       # Updates lamps.last_updated
update_current_conditions()   # Updates current_conditions per lamp
batch_update_lamp_timestamps()
batch_update_current_conditions()
```

**NEW Functions (CREATE):**
```python
def get_location_api_configs(engine):
    """
    Returns: {location: {'wave_api_url': ..., 'wind_api_url': ...}}
    Query: SELECT location, wave_api_url, wind_api_url FROM locations
    """

def get_arduinos_for_location(engine, location):
    """
    Returns: [{'arduino_id': 4433, 'user_id': 6, 'location': 'Hadera, Israel'}, ...]
    Query: SELECT arduino_id, user_id, location FROM arduinos WHERE location = ?
    """

def update_location_conditions(engine, location, surf_data):
    """
    Updates locations table (ONCE per location, not per arduino)
    Query: UPDATE locations SET wave_height_m=?, wind_speed_mps=?, last_updated=NOW() WHERE location=?
    """

def batch_update_arduino_timestamps(engine, arduino_ids):
    """
    Updates arduino last_poll_time for multiple arduinos
    Query: UPDATE arduinos SET last_poll_time=NOW() WHERE arduino_id IN (...)
    """
```

**Key Architectural Change:**
- **OLD:** Update `current_conditions` for EACH lamp (N updates per location)
- **NEW:** Update `locations` table ONCE per location (1 update per location)

---

### 4. **surf-lamp-processor/background_processor.py**
**Processing Loop Changes:**

**OLD Logic (Lines 131-203):**
```python
for location, config in location_configs.items():
    lamps = get_lamps_for_location(engine, location)

    # Fetch combined surf data from multiple APIs
    combined_surf_data = {...}

    # Update EACH lamp individually
    for lamp in lamps:
        update_current_conditions(engine, lamp['lamp_id'], combined_surf_data)
        update_lamp_timestamp(engine, lamp['lamp_id'])
```

**NEW Logic:**
```python
for location, config in location_configs.items():
    arduinos = get_arduinos_for_location(engine, location)

    # Fetch combined surf data from multiple APIs
    combined_surf_data = {...}

    # Update location table ONCE (all arduinos inherit)
    update_location_conditions(engine, location, combined_surf_data)

    # Update arduino timestamps to track polling activity
    arduino_ids = [a['arduino_id'] for a in arduinos]
    batch_update_arduino_timestamps(engine, arduino_ids)
```

**Performance Impact:**
- Reduces database writes from N updates per location to 2 updates per location
- Example: 5 arduinos in Hadera → 1 location update + 1 batch timestamp update (instead of 5 individual updates)

---

### 5. **web_and_database/blueprints/dashboard.py**
**Query Changes:**

```python
# OLD: Get user's lamp and conditions
lamp = db.query(Lamp).filter(Lamp.user_id == user_id).first()
conditions = db.query(CurrentConditions).filter(CurrentConditions.lamp_id == lamp.lamp_id).first()

# NEW: Get user's arduinos and location conditions
arduinos = db.query(Arduino).filter(Arduino.user_id == user_id).all()
# For dashboard default view:
user_location = db.query(User.location).filter(User.user_id == user_id).scalar()
conditions = db.query(Location).filter(Location.location == user_location).first()
```

**UI Changes Needed:**
- Display multiple arduinos if user has more than one
- Each arduino can have different location
- Allow user to configure arduino → location mapping

---

### 6. **web_and_database/blueprints/reports.py**
**Error Reports:**

```python
# Line references to lamp_id → arduino_id
# Update any queries joining error_reports to lamps table
```

---

### 7. **web_and_database/blueprints/admin.py**
**Admin Panel:**

```python
# OLD: Query lamps table with lamp_id, arduino_id as separate columns
# NEW: Query arduinos table with arduino_id as PK

# Update any admin views showing lamp management
```

---

## Migration Checklist

- [ ] Run `migration_schema_refactor.sql` on development database
- [ ] Update `data_base.py` ORM models (Arduino, Location)
- [ ] Rewrite `lamp_repository.py` with new functions
- [ ] Update `background_processor.py` processing loop
- [ ] Update `api_arduino.py` queries and responses
- [ ] Update `dashboard.py` to display multiple arduinos per user
- [ ] Update `admin.py` for arduino management
- [ ] Update `reports.py` for arduino_id column
- [ ] Test Arduino data polling endpoint (`/api/arduino/{arduino_id}/data`)
- [ ] Test scheduler location processing
- [ ] Verify location data updates propagate to all arduinos
- [ ] Update MCP Supabase server tool descriptions
- [ ] Run production migration on Render database

---

## Rollback Plan

If migration fails, restore from backup and revert code changes:

```sql
-- Restore database from pre-migration backup
-- Revert git commits to pre-migration state
git revert <commit-hash>
```

---

## Testing Strategy

1. **Local Development:**
   - Run migration SQL on local Supabase instance
   - Update code files
   - Test scheduler: `python background_processor.py`
   - Test Arduino endpoint: `curl http://localhost:5000/api/arduino/4433/data`

2. **Staging (if available):**
   - Deploy to staging Render service
   - Monitor logs for errors
   - Verify Arduino polling works

3. **Production:**
   - Schedule maintenance window
   - Backup database
   - Run migration
   - Deploy code
   - Monitor first 3-4 polling cycles (13min × 4 = 52min)

---

## Post-Migration Verification Queries

```sql
-- Verify arduinos table populated correctly
SELECT COUNT(*) FROM arduinos;
SELECT * FROM arduinos;

-- Verify locations table has API endpoints
SELECT location, wave_api_url, wind_api_url FROM locations;

-- Verify conditions data migrated
SELECT location, wave_height_m, wind_speed_mps, last_updated FROM locations;

-- Check for orphaned data
SELECT * FROM error_reports WHERE arduino_id NOT IN (SELECT arduino_id FROM arduinos);
```
