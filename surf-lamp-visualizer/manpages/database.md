# Database (Supabase PostgreSQL) - Technical Documentation

## 1. Overview

**What it does**: an Abstraction to the sql database allows cleaner less error prone code.

## 2. Technical Details

### Critical Assumptions

**Connection String**:
- `DATABASE_URL` env var set with Supabase connection string (format: `postgresql://user:pass@host:port/dbname`)
- Fallback to individual env vars (`DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, `DB_NAME`) if `DATABASE_URL` not set
- Localhost fallback (`postgresql://user:password@localhost/surfboard_lamp`) warns in logs - production will fail

**PostgreSQL Version**:
- Supabase uses PostgreSQL 15+ - SQLAlchemy ORM assumes standard features (foreign keys, triggers, sequences)
- Auto-increment primary keys require `SERIAL` or `BIGSERIAL` type support
- `TIMESTAMP` type for datetime fields (stored in UTC, no timezone offset)

**Foreign Key Enforcement**:
- Database enforces referential integrity - cannot delete user without cascade deleting lamp
- Orphaned records prevented by ON DELETE CASCADE on `lamps.user_id` → `users.user_id`
- `current_conditions.lamp_id` → `lamps.lamp_id` requires lamp exists before conditions inserted

**Session Management**:
- SQLAlchemy `SessionLocal()` creates new database connection per request
- `autocommit=False` requires explicit `db.commit()` or changes rollback on error
- Connection pooling via SQLAlchemy defaults (5 connections, 30-second timeout)

**Unique Constraints**:
- `users.email` and `users.username` must be unique - duplicate registration fails with `IntegrityError`
- `lamps.arduino_id` unique - same Arduino cannot be registered to multiple users
- `lamps.arduino_ip` unique - IP address collision detection (same physical network assumption)
- `daily_usage.website_url` unique - API URLs deduplicated across all users

**Timezone Handling**:
- All `TIMESTAMP` fields stored in UTC using timezone-aware datetime objects (`datetime.now(timezone.utc)`). Database uses PostgreSQL TIMESTAMPTZ type for automatic UTC handling.
- Application layer (web app) converts to user's local timezone for display
- No timezone column in database - pytz handles conversion at query time

**NULL Constraints**:
- `lamps.arduino_id` and `lamps.arduino_ip` allow NULL initially - set during discovery phase
- `current_conditions` wave/wind fields allow NULL - no data yet fetched
- `usage_lamps.api_key` allows NULL - most APIs don't require keys

### Where Complexity Hides

**Edge Cases**:
- **Multiple Lamps Per User**: Schema supports one-to-one `User`→`Lamp` via `uselist=False` - multi-lamp users break relationship
- **Duplicate Arduino ID**: Two users register same arduino_id → second registration fails with unique constraint error (no retry logic)
- **Orphaned CurrentConditions**: Background processor writes conditions but lamp deleted → foreign key cascade deletes row silently
- **UsageLamps Priority Collision**: Two endpoints with same priority → undefined which runs first (stable sort not guaranteed)

**Race Conditions**:
- **Concurrent Registration**: Two users register simultaneously with same email → one transaction rolls back with `IntegrityError`
- **Location Update Mid-Fetch**: User changes location while background processor fetching old location → stale data written to new location's conditions
- **Password Reset Token Expiry**: Token checked valid, then expires before password update → user sees "invalid token" error (no retry window)

**Data Integrity Risks**:
- **Manual Database Edits**: Changing `location_websites.location` breaks join with `MULTI_SOURCE_LOCATIONS` dict - processor cannot find endpoints
- **Deleted DailyUsage**: Removing row from `daily_usage` breaks `usage_lamps` foreign key - lamp configuration broken


**Schema Evolution Gotchas**:
- **Adding Columns**: SQLAlchemy `Base.metadata.create_all()` does NOT alter existing tables - new columns require manual migration
- **Renaming Tables**: Would break all ORM queries - requires search/replace across codebase
- **Primary Key Auto-Increment**: `lamp_id` auto-generated via sequence - SQLAlchemy model defines manually but database overrides

### Stories the Code Tells


**Design Philosophy**:
- **Location-Centric Processing**: `LocationWebsites` table maps one location to one DailyUsage - deduplicates API calls for multiple users in same city
- **Priority-Based Fallback**: `usage_lamps.endpoint_priority` enables failover (wave API down → use backup source)
- **Relationship Cascade**: `cascade="all, delete-orphan"` on ORM relationships - deleting user automatically cleans up lamp, conditions, tokens
- **String-Based Location Keys**: Using human-readable "Tel Aviv, Israel" instead of numeric location IDs - easier debugging, harder to typo

## 3. Architecture & Implementation

### Schema Diagram

```
users (1) ←→ (1) lamps (1) ←→ (1) current_conditions
  ↓                ↓
  |                ├→ (N) usage_lamps (N) ←→ daily_usage (1)
  |                                             ↓
  ↓                                             ├→ (N) location_websites
password_reset_tokens
```

### Table Definitions

#### `users` - User Accounts
**File**: `web_and_database/data_base.py:74-100`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `user_id` | `INTEGER` | PK, AUTO_INCREMENT | Unique user identifier |
| `username` | `VARCHAR(255)` | UNIQUE, NOT NULL | Display name (not used for login) |
| `password_hash` | `TEXT` | NOT NULL | Bcrypt-hashed password |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL | Login credential + password reset destination |
| `location` | `VARCHAR(255)` | NOT NULL | Selected surf spot (e.g., "Tel Aviv, Israel") |
| `theme` | `VARCHAR(50)` | NOT NULL | LED theme name (classic_surf, ocean_sunset, etc.) |
| `preferred_output` | `VARCHAR(50)` | NOT NULL | Unit system (metric/imperial) - unused in current code |
| `sport_type` | `VARCHAR(20)` | NOT NULL, DEFAULT 'surfing' | Water sport type (surfing, kitesurfing, windsurfing, SUP) |
| `wave_threshold_m` | `DOUBLE PRECISION` | NULL, DEFAULT 1.0 | Minimum wave height for alert (meters) |
| `wind_threshold_knots` | `DOUBLE PRECISION` | NULL, DEFAULT 22.0 | Maximum wind speed for alert (knots) |

**Relationships**:
- `lamp` (1:1): One user owns one lamp via `user_id` foreign key
- `reset_tokens` (1:N): User can have multiple password reset tokens (only one valid at a time)

**Indexes**: Implicit on `email` (unique), `username` (unique)

---

#### `lamps` - Physical Arduino Devices
**File**: `web_and_database/data_base.py:122-142`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `lamp_id` | `INTEGER` | PK, AUTO_INCREMENT | Unique lamp identifier (auto-generated sequence) |
| `user_id` | `INTEGER` | FK → users.user_id, NOT NULL | Lamp owner |
| `arduino_id` | `INTEGER` | UNIQUE, NULL | Arduino microcontroller ID (set during discovery) |
| `arduino_ip` | `VARCHAR` | UNIQUE, NULL | Local network IP address (IPv4 format) |
| `last_updated` | `TIMESTAMP` | DEFAULT NOW() | Last successful data sync timestamp |

**Relationships**:
- `user` (N:1): Each lamp belongs to one user
- `usage_configs` (1:N): Lamp linked to multiple API endpoints via `usage_lamps`
- `current_conditions` (1:1): One set of surf conditions per lamp

**Indexes**: Implicit on `arduino_id` (unique), `arduino_ip` (unique)

**Cascade Behavior**: Deleting user deletes lamp (ON DELETE CASCADE)

---

#### `current_conditions` - Latest Surf Data
**File**: `web_and_database/data_base.py:144-166`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `lamp_id` | `INTEGER` | PK, FK → lamps.lamp_id | Links to specific lamp (one row per lamp) |
| `wave_height_m` | `DOUBLE PRECISION` | NULL | Wave height in meters |
| `wave_period_s` | `DOUBLE PRECISION` | NULL | Wave period in seconds |
| `wind_speed_mps` | `DOUBLE PRECISION` | NULL | Wind speed in meters per second |
| `wind_direction_deg` | `INTEGER` | NULL | Wind direction in degrees (0-360, 0=North) |
| `last_updated` | `TIMESTAMP` | DEFAULT NOW() | When background processor last wrote data |

**Relationships**:
- `lamp` (1:1): One conditions row per lamp

**Update Pattern**: Background processor UPSERTs - inserts if not exists, updates if exists

**Cascade Behavior**: Deleting lamp deletes conditions row (ON DELETE CASCADE)

---

#### `daily_usage` - API Endpoint Registry
**File**: `web_and_database/data_base.py:168-186`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `usage_id` | `INTEGER` | PK, AUTO_INCREMENT | Unique API endpoint identifier |
| `website_url` | `VARCHAR(255)` | UNIQUE, NOT NULL | Full API URL (e.g., Open-Meteo marine endpoint) |
| `last_updated` | `TIMESTAMP` | DEFAULT NOW(), ON UPDATE NOW() | Last API fetch timestamp (deduplication) |

**Relationships**:
- `locations` (1:N): One API URL can serve multiple locations
- `lamp_configs` (1:N): One API URL used by multiple lamps

**Deduplication Logic**: If 5 users in Tel Aviv, only 1 row for Tel Aviv's wave API

---

#### `location_websites` - Location → API Mapping
**File**: `web_and_database/data_base.py:188-200`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `location` | `VARCHAR(255)` | PK | Surf spot name (e.g., "Hadera, Israel") |
| `usage_id` | `INTEGER` | FK → daily_usage.usage_id, UNIQUE, NOT NULL | Primary API source for this location |

**Relationships**:
- `website` (N:1): Each location maps to one primary API source

**Usage**: Background processor queries this table to find API URL for location

---

#### `usage_lamps` - Lamp API Configuration
**File**: `web_and_database/data_base.py:202-224`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `usage_id` | `INTEGER` | PK, FK → daily_usage.usage_id | Which API endpoint |
| `lamp_id` | `INTEGER` | PK, FK → lamps.lamp_id | Which lamp uses this endpoint |
| `api_key` | `TEXT` | NULL | API authentication key (if required) |
| `http_endpoint` | `TEXT` | NOT NULL | Full API URL (denormalized from daily_usage) |
| `endpoint_priority` | `INTEGER` | NOT NULL, DEFAULT 1 | Failover order (1=primary, 2=backup) |

**Composite Primary Key**: (`usage_id`, `lamp_id`) - allows one lamp to have multiple endpoints

**Relationships**:
- `lamp` (N:1): Multiple endpoints per lamp
- `website` (N:1): Multiple lamps per API source

**Priority System**:
- Priority 1: Wave data (marine-api.open-meteo.com or isramar.ocean.org.il)
- Priority 2: Wind data (OpenWeatherMap)

**Denormalization**: `http_endpoint` duplicates `daily_usage.website_url` - performance optimization for background processor

---

#### `password_reset_tokens` - Password Recovery
**File**: `web_and_database/data_base.py:102-120`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | Unique token record ID (PostgreSQL UUID type) |
| `user_id` | `INTEGER` | FK → users.user_id, NOT NULL | User requesting reset |
| `token_hash` | `VARCHAR` | UNIQUE, NOT NULL | SHA-256 hash of reset token |
| `expiration_time` | `TIMESTAMP` | NOT NULL | Token expires (20 minutes from creation) |
| `created_at` | `TIMESTAMP` | DEFAULT NOW() | When token generated |
| `used_at` | `TIMESTAMP` | NULL | When password successfully reset (NULL if unused) |
| `is_invalidated` | `BOOLEAN` | DEFAULT FALSE | Manually invalidated (new request cancels old tokens) |

**Relationships**:
- `user` (N:1): Multiple tokens per user (only one valid)

**Security Model**:
- **Token Generation**: `secrets.token_urlsafe(48)` generates 64-character random token
- **Storage**: Only SHA-256 hash stored - plaintext token never in database
- **Validation**: Token hashed client-side, compared to `token_hash`
- **Single-Use**: `used_at` timestamp set after password change
- **Expiration**: 20-minute validity window
- **Invalidation**: New reset request sets `is_invalidated=TRUE` on all previous tokens for that user

**Cleanup**: No automatic deletion - old tokens accumulate (manual cleanup via SQL needed) a local clean up script exists cleanup_tokens.py

---

### API Source Configuration

**File**: `web_and_database/data_base.py:231-316`

**Supported Locations**:
1. Tel Aviv, Israel (Open-Meteo marine + OpenWeatherMap)
2. Hadera, Israel (isramar.ocean.org.il + OpenWeatherMap)
3. Ashdod, Israel (Open-Meteo marine + OpenWeatherMap)
4. Haifa, Israel (Open-Meteo marine + OpenWeatherMap)
5. Netanya, Israel (Open-Meteo marine + OpenWeatherMap)
6. Nahariya, Israel (Open-Meteo marine + OpenWeatherMap)
7. Ashkelon, Israel (Open-Meteo marine + OpenWeatherMap)

**Why Hybrid APIs**:
- **Rate Limiting**: `api.open-meteo.com` exhausted shared IP quota - switched to `marine-api.open-meteo.com` for waves
- **Data Completeness**: Open-Meteo provides wave data but unreliable wind - OpenWeatherMap fills gap
- **Isramar Preference**: Hadera uses Israeli government API (isramar.ocean.org.il) - local buoy data more accurate

**Architecture Decision**: Code-driven configuration (not database-driven) - immune to accidental database edits corrupting API URLs

---

### Key Functions & Classes

#### `add_user_and_lamp(name, email, password_hash, lamp_id, arduino_id, location, theme, units, sport_type)`
**File**: `web_and_database/data_base.py:323-427`

**Purpose**: Atomic user registration - creates user, lamp, API links, and location mapping in single transaction

**Transaction Flow**:
1. Validate location exists in `MULTI_SOURCE_LOCATIONS` (fail fast if unsupported)
2. Create `User` record with profile data
3. Create `Lamp` record linked to user (`arduino_id=None` initially)
4. For each API source in location:
   - Get or create `DailyUsage` record for API URL
   - Create `UsageLamps` link with priority
5. Create `LocationWebsites` mapping (first API source)
6. Commit transaction (rollback on any error)

**Error Handling**:
- `IntegrityError`: Duplicate email/username/lamp_id/arduino_id → return `(False, "Account exists")`
- `Exception`: Any other error → rollback, return `(False, "Database error: {details}")`

**Returns**: `(success: bool, message: str)`

---

#### `get_user_lamp_data(email)`
**File**: `web_and_database/data_base.py:430-470`

**Purpose**: Dashboard data retrieval - joins user, lamp, and conditions tables

**Query**:
```python
db.query(User, Lamp, CurrentConditions)
  .join(Lamp, User.user_id == Lamp.user_id)
  .outerjoin(CurrentConditions, Lamp.lamp_id == CurrentConditions.lamp_id)
  .filter(User.email == email)
  .first()
```

**Returns**: `(User, Lamp, CurrentConditions)` or `(None, None, None)` if user not found

**LEFT JOIN Strategy**: Uses `outerjoin` on `CurrentConditions` - returns user/lamp even if no surf data yet

---

#### `update_user_location(user_id, new_location)`
**File**: `web_and_database/data_base.py:472-545`

**Purpose**: Change user's surf location and reconfigure lamp's API endpoints

**Transaction Flow**:
1. Validate new location in `MULTI_SOURCE_LOCATIONS`
2. Update `users.location` field
3. Delete all `UsageLamps` records for user's lamp
4. Create new `UsageLamps` records for new location's APIs
5. Update `LocationWebsites` mapping
6. Commit transaction

**Why Delete/Recreate**: Ensures clean state - no orphaned endpoints from old location

**Returns**: `(success: bool, message: str)`

---

### Configuration

**Environment Variables**:
```bash
DATABASE_URL="postgresql://user:pass@host:port/dbname"
# OR individual components:
DB_USER="postgres_user"
DB_PASS="password"
DB_HOST="db.supabase.co"
DB_PORT="5432"
DB_NAME="postgres"
```

**SQLAlchemy Connection**:
- Engine: `create_engine(DATABASE_URL)`
- Session: `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- Base: `declarative_base()` for ORM models

**Connection Pooling** (SQLAlchemy defaults):
- Pool size: 5 connections
- Max overflow: 10 connections
- Timeout: 30 seconds
- Recycle: 3600 seconds (1 hour)

## 4. Integration Points

### What Calls This Component

**Web Application** (`web_and_database/app.py`):
- `add_user_and_lamp()`: User registration form
- `get_user_lamp_data()`: Dashboard rendering
- `update_user_location()`: Location change AJAX endpoint
- Direct queries: Login, threshold updates, password reset

**Background Processor** (`surf-lamp-processor/background_processor.py`):
- Direct queries: Fetch locations, write to `current_conditions`, read `usage_lamps` for API URLs
- No function calls - uses `SessionLocal()` directly

**MCP Supabase Server** (`mcp-supabase-server/`):
- Direct SQL queries via Supabase client
- Read-only access for monitoring and debugging

### Data Contracts

**User Registration Input**:
```python
add_user_and_lamp(
    name="johndoe",
    email="john@example.com",
    password_hash="$2b$12$...",  # Bcrypt hash
    lamp_id=1234,  # User-provided serial number
    arduino_id=5678,  # Arduino MAC address
    location="Tel Aviv, Israel",
    theme="classic_surf",
    units="metric",
    sport_type="surfing"
)
```

**Dashboard Query Output**:
```python
(
    User(user_id=42, email="john@example.com", location="Tel Aviv, Israel", ...),
    Lamp(lamp_id=1234, arduino_id=5678, arduino_ip="192.168.1.100", ...),
    CurrentConditions(lamp_id=1234, wave_height_m=1.5, wave_period_s=8.0, ...)
)
```

**Location Update Input**:
```python
update_user_location(user_id=42, new_location="Haifa, Israel")
```

## 5. Troubleshooting & Failure Modes

### Common Issues

**Problem: "An account with this email already exists"**
- **Symptoms**: Registration fails with `IntegrityError`
- **Detection**: Logs show `IntegrityError: duplicate key value violates unique constraint "users_email_key"`
- **Causes**: User trying to register email already in database
- **Recovery**: Use password reset flow or manual database query to check existing user

**Problem: "Location not supported"**
- **Symptoms**: Registration or location update fails with validation error
- **Detection**: Logs show `No API mapping found for location: ...`
- **Causes**: User entered location not in `MULTI_SOURCE_LOCATIONS` dict
- **Recovery**: Add location to `MULTI_SOURCE_LOCATIONS` in `data_base.py`, redeploy

**Problem: Orphaned CurrentConditions Rows**
- **Symptoms**: `current_conditions` table grows larger than `lamps` table
- **Detection**: `SELECT COUNT(*) FROM current_conditions; SELECT COUNT(*) FROM lamps;`
- **Causes**: Cascade delete failed or foreign key constraint missing
- **Recovery**: Manual cleanup: `DELETE FROM current_conditions WHERE lamp_id NOT IN (SELECT lamp_id FROM lamps);`

**Problem: Multiple UsageLamps with Same Priority**
- **Symptoms**: Background processor fetches from wrong API source
- **Detection**: Logs show unexpected API URL for location
- **Causes**: Manual database edit or bug in `add_user_and_lamp()`
- **Recovery**: Fix priority values: `UPDATE usage_lamps SET endpoint_priority = 1 WHERE lamp_id = X AND usage_id = Y;`

**Problem: DATABASE_URL Not Set**
- **Symptoms**: App fails to start with connection error
- **Detection**: Logs show `Using localhost fallback DATABASE_URL - this will fail in production!`
- **Causes**: Environment variable missing in deployment
- **Recovery**: Set `DATABASE_URL` in Render dashboard (Settings → Environment)


### Scaling Concerns

**Connection Pool Exhaustion**:
- **Current**: 5 connections (SQLAlchemy default)
- **At Scale**: 100 concurrent users × 1 request/sec = connection starvation
- **Mitigation**: Increase pool size via `create_engine(pool_size=20, max_overflow=30)`

**Table Growth**:
- **`password_reset_tokens`**: Accumulates forever - no cleanup
  - **At Scale**: 1000 users × 10 resets/year = 10k rows/year
  - **Mitigation**: Cron job to delete tokens older than 7 days
- **`daily_usage`**: One row per unique API URL (finite)
  - **At Scale**: ~50 locations × 2 APIs = 100 rows max
- **`usage_lamps`**: Grows with user count
  - **At Scale**: 10k users × 2 endpoints = 20k rows (negligible)

**Query Performance**:
- **Dashboard Load**: 3-table join (User → Lamp → CurrentConditions)
  - **At Scale**: Index on `users.email` required (already unique)
  - **Optimization**: Add composite index on `(lamps.user_id, lamps.lamp_id)`
- **Arduino API**: 3-table join by `arduino_id`
  - **At Scale**: Index on `lamps.arduino_id` required (already unique)

**Write Contention**:
- **Background Processor**: Updates all `current_conditions` rows every 20 minutes
  - **At Scale**: 10k lamps = 10k UPDATE queries = lock contention
  - **Mitigation**: Batch updates, stagger processing by location

---

*Last Updated: 2025-10-01*
*Database: Supabase PostgreSQL 15*
*ORM: SQLAlchemy 2.x*
