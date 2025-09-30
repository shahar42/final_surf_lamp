# Background Processor - Technical Documentation

## 1. Overview

**What it does**: Location-centric background service running every 20 minutes on Render that fetches surf data from external APIs (Isramar, Open-Meteo, OpenWeatherMap), standardizes responses using field mappings, and updates the PostgreSQL database with current wave height, period, wind speed, and direction for all lamps grouped by location.

**Why it exists**: Eliminates duplicate API calls by processing lamps grouped by location instead of individually. Reduces API call volume by ~70% (from 21 to 6 calls for 7 lamps across 2 locations), prevents rate limiting (429 errors), maintains data completeness through multi-source fallback, and keeps processing time under 5 minutes instead of 25+ minutes with lamp-centric approach.

## 2. Technical Details

### What Would Break If This Disappeared?

- **Lamp Data Freshness**: All lamps stop receiving fresh surf data - database `current_conditions` table goes stale
- **Arduino Displays**: Arduino devices continue functioning but display outdated conditions from last successful update
- **User Dashboard**: Web dashboard shows stale `last_updated` timestamps, users see old wave/wind data
- **External API Integration**: Complete loss of weather data ingestion - system becomes read-only historical data viewer
- **Background Processor Service**: The only component that writes to `current_conditions` table - no other service can substitute

### Critical Assumptions

**Database Assumptions**:
- PostgreSQL (Supabase) accessible via `DATABASE_URL` environment variable (line 86)
- SSL connection required for supabase.com domains (line 94-95: `connect_args["sslmode"] = "require"`)
- Tables exist: `users` (with `location` column), `lamps` (with `arduino_id`, `lamp_id`, `user_id`), `current_conditions` (with `lamp_id` primary key)
- Database exits on startup if `DATABASE_URL` not set (line 87-89)
- Connection failures exit with code 1 (line 100-101)

**API Reliability Assumptions**:
- Isramar API available at `https://isramar.ocean.org.il/isramar2009/station/data/{location}_Hs_Per.json`
- Open-Meteo Marine API at `https://marine-api.open-meteo.com/v1/marine?...`
- OpenWeatherMap at `https://api.openweathermap.org/data/2.5/weather?...`
- Multi-source priority system (line 746-767): Higher priority sources tried first, data merged from multiple sources
- APIs return JSON responses parsable by `response.json()` (line 590)

**Timing Assumptions**:
- 20-minute cycle in production mode (line 846: `schedule.every(20).minutes.do(process_all_lamps)`)
- 30-second delay between API calls (line 584: `time.sleep(30)`) - increased from 10s due to rate limiting
- HTTP timeouts: 30 seconds for OpenWeatherMap (line 551), 15 seconds for others
- Retry logic: max 3 attempts with exponential backoff for 429 errors (line 547-580)
- Test mode runs once and exits (line 830-835: `TEST_MODE` env var check)

**Wind Speed Units CRITICAL**:
- Open-Meteo wind APIs MUST include `&wind_speed_unit=ms` parameter (line 527-532 validation)
- Without this parameter, APIs return km/h instead of m/s causing incorrect calculations throughout system
- Validation added after critical production incident (endpoint_configs.py line 6-18 maintainer note)
- Validation error logged as CRITICAL and returns None (line 529-532)

**Location Configuration Assumptions**:
- `MULTI_SOURCE_LOCATIONS` imported from `web_and_database/data_base.py` as source of truth (line 372)
- Dynamic path resolution using relative paths (line 367-370) to avoid hardcoded local paths breaking in production
- Each location maps to multiple API sources with priority ordering (line 388-395 conversion to expected format)
- Active locations determined by querying distinct `location` from `users` table (line 375-378)

### Where Complexity Hides

**Edge Cases**:

1. **Current Hour Index Calculation** (line 130-157):
   - Open-Meteo APIs return hourly arrays with timestamps like `["2025-09-13T00:00", "2025-09-13T01:00", ...]`
   - Function finds index matching current UTC hour via string matching (line 147-149)
   - Falls back to index 0 if not found (line 152, 156) - logs warning but doesn't fail
   - Potential issue: Timezone mismatches if API returns local time instead of UTC

2. **Wind Speed Unit Parameter Missing** (line 527-532):
   - CRITICAL validation checks if Open-Meteo wind endpoints contain `&wind_speed_unit=ms`
   - Missing parameter causes km/h to be returned instead of m/s (3.6x conversion error)
   - Logs three ERROR messages and returns None to prevent bad data propagation
   - Validation added after production incident where Arduino displayed incorrect wind speeds

3. **Empty API Response Merging** (line 759-762):
   - Multi-source priority system merges data: `if field not in combined_surf_data or value is not None`
   - Empty responses don't overwrite existing fields from higher priority sources
   - Allows partial data from multiple sources to combine into complete dataset
   - Risk: If all sources return empty, `combined_surf_data` empty and location skipped (line 769-771)

4. **Arduino Failure Tracking** (line 159-188):
   - Tracks consecutive failures per Arduino in `arduino_failure_counts` dict (line 68)
   - After 3 failures, skips Arduino for 30 minutes (line 70-71: `ARDUINO_FAILURE_THRESHOLD`, `ARDUINO_RETRY_DELAY`)
   - Legacy system - `send_to_arduino()` exists but rarely used (line 190-244)
   - Architectural note line 15-17: Arduinos PULL data, processor doesn't PUSH

**Race Conditions**:

1. **Multiple Instance Concurrency**:
   - Render could theoretically auto-scale to multiple instances (not intended design)
   - No locking mechanism for location processing - multiple instances could process same location
   - Database writes would overwrite each other (line 696-703: `INSERT ... ON CONFLICT UPDATE`)
   - Scheduler state not shared between instances (line 846: `schedule` is in-memory)

2. **Database Writes Non-Atomic Across Lamps**:
   - Processing loop updates lamps one-by-one (line 777-789)
   - If cycle interrupted mid-loop, some lamps updated with fresh data, others remain stale
   - No transaction wrapping entire location's lamp updates
   - Each `update_lamp_timestamp()` and `update_current_conditions()` commits independently (line 663, 703)

**Rate Limiting Concerns**:

1. **30-Second Delay Between Calls** (line 584):
   - `time.sleep(30)` after every successful API call
   - Increased from 10 seconds after production 429 errors (comment line 583)
   - Applied uniformly regardless of API provider's actual rate limits
   - Sequential processing means total cycle time = (num_locations × num_apis × 30s + processing overhead)

2. **Exponential Backoff for 429s** (line 572-578):
   - Base delay 60 seconds (line 548: `base_delay = 60`)
   - Exponential: 60s, 120s, 240s for attempts 1, 2, 3 (line 572: `delay = base_delay * (2 ** attempt)`)
   - After 3 failed attempts, gives up and logs error (line 577-578)
   - Per-API retry, not per-cycle global limit

3. **Timeout Handling** (line 551-568):
   - OpenWeatherMap: 30 seconds (line 551: `timeout_seconds = 30 if "openweathermap.org"`)
   - Other APIs: 15 seconds default
   - Timeout retries use 30-second delay (line 562), not exponential
   - Max 3 timeout retry attempts before giving up (line 567-568)

**Stories the Code Tells**:

**Git History Insights**:
- Commit `cd0f5d1`: "Restore API-based processing from 100 commits ago" - location-centric architecture was rediscovered after failed lamp-centric approach
- Wind speed unit bug (`c315af3`, `8818a51`) - critical production incident led to validation code (line 527)
- Rate limiting evolution - increased delays from 10s to 30s after 429 errors in production
- Multi-source fallback added after Open-Meteo rate limiting issues (priority system in lines 746-767)

**Design Philosophy**:
- **Location-centric over lamp-centric**: Lines 1-37 architectural documentation emphasizes this is NON-NEGOTIABLE
- **Multi-source reliability**: Priority system (Isramar → Open-Meteo → OpenWeatherMap) ensures data completeness
- **Defensive programming**: Extensive logging, retry logic, safe defaults
- **Separation of concerns**: `endpoint_configs.py` for API field mappings, `arduino_transport.py` for push mechanism

## 3. Architecture & Implementation

### Data Flow

```
[20-min Schedule Trigger] → [test_database_connection()]
         ↓
[get_location_based_configs()] → Query distinct user locations → Lookup MULTI_SOURCE_LOCATIONS
         ↓
[For each location]:
  ├─> [get_lamps_for_location()] → Query all lamps in location
  ├─> [For each API endpoint (priority order)]:
  │     ├─> [fetch_surf_data()] → HTTP GET with retry/backoff → 30s delay
  │     ├─> [standardize_surf_data()] → Apply FIELD_MAPPINGS
  │     └─> [Merge into combined_surf_data]
  └─> [For each lamp]:
        ├─> [update_lamp_timestamp()]
        └─> [update_current_conditions()] → UPSERT to database
```

### Key Functions

- `process_all_lamps()` (line 712): Main orchestrator, location-centric loop, returns success/failure
- `get_location_based_configs()` (line 357): Reads MULTI_SOURCE_LOCATIONS from data_base.py, queries active user locations
- `fetch_surf_data()` (line 510): HTTP client with retry logic, timeout handling, wind unit validation
- `standardize_surf_data()` (line 273): Applies FIELD_MAPPINGS from endpoint_configs.py, handles nested JSON extraction
- `get_current_hour_index()` (line 130): Finds current hour in Open-Meteo time arrays for hourly data
- `update_current_conditions()` (line 673): UPSERT query to current_conditions table
- `send_to_arduino()` (line 190): Legacy push mechanism (unused - Arduinos pull from web server)

### Configuration

**Environment Variables**:
- `DATABASE_URL` (required) - PostgreSQL connection string
- `TEST_MODE` (optional, default: false) - "true" for single run, "false" for continuous 20-min scheduling
- `ARDUINO_TRANSPORT` (optional, default: http) - "mock" for testing without real Arduino connections

**Hardcoded Configuration**:
- `ARDUINO_FAILURE_THRESHOLD = 3` (line 70)
- `ARDUINO_RETRY_DELAY = 1800` (30 minutes, line 71)
- `LOCATION_TIMEZONES` (line 74-83) - for local time formatting
- 30-second delay between API calls (line 584)
- Retry timeouts: 30s for OpenWeatherMap, 15s for others (line 551)

**External Configuration**:
- `MULTI_SOURCE_LOCATIONS` from `/web_and_database/data_base.py` - maps locations to API endpoints with priorities
- `FIELD_MAPPINGS` from `endpoint_configs.py` - maps API response fields to standardized format

## 4. Integration Points

### What Calls This Component

- Render cron/scheduler (every 20 minutes in production)
- Manual execution via `python background_processor.py` (test mode)
- No other services call this directly (runs autonomously)

### What This Component Calls

**External APIs**:
- Isramar: `https://isramar.ocean.org.il/isramar2009/station/data/{location}_Hs_Per.json`
- Open-Meteo Marine API: `https://marine-api.open-meteo.com/v1/marine?lat={lat}&lon={lon}&hourly=wave_height,wave_period`
- OpenWeatherMap: `https://api.openweathermap.org/data/2.5/weather?q={location}&appid={key}`

**Database (PostgreSQL)**:
- `SELECT DISTINCT location FROM users` - get active locations
- `SELECT ... FROM lamps JOIN users` - get lamps per location
- `UPDATE lamps SET last_updated = ...` - update lamp timestamp
- `INSERT ... ON CONFLICT UPDATE` - upsert to current_conditions

### Data Contracts

**Database Write** (`current_conditions` table):
```sql
INSERT INTO current_conditions (
  lamp_id, wave_height_m, wave_period_s,
  wind_speed_mps, wind_direction_deg, last_updated
) VALUES (...) ON CONFLICT (lamp_id) DO UPDATE ...
```

**API Response Standardization**:
- All APIs normalized to: `wave_height_m`, `wave_period_s`, `wind_speed_mps`, `wind_direction_deg`
- Isramar uses custom extraction (line 66-88 in endpoint_configs.py)
- Open-Meteo uses hourly array indexing with current hour calculation
- OpenWeatherMap uses nested dict extraction

## 5. Troubleshooting & Failure Modes

### Common Issues

**Problem: 429 Rate Limiting Errors**

**Symptoms**: Logs show repeated rate limit warnings, processing cycle fails

**Detection**: `mcp__render__search_render_logs` with "429"

**Causes**:
- Too many API calls in short period (30s delay insufficient)
- Shared IP quota exhaustion on Render
- API subdomain rate limit pools

**Recovery**:
1. Identify failing API from logs
2. Verify 30-second delay present (line 584)
3. Consider switching API subdomain
4. Increase exponential backoff base delay (line 548)

**Problem: Wind Speed Units Bug**

**Symptoms**: Arduino displays wind speeds 3.6x incorrect (km/h vs m/s)

**Detection**: Compare database `wind_speed_mps` with external weather sources

**Causes**: Open-Meteo API URL missing `&wind_speed_unit=ms` parameter

**Recovery**:
1. Check `MULTI_SOURCE_LOCATIONS` in `data_base.py`
2. Verify all Open-Meteo URLs contain `&wind_speed_unit=ms`
3. Add missing parameter and redeploy

**Problem: Processing Cycle Takes >20 Minutes**

**Symptoms**: Duration >1200 seconds in logs, overlapping cycles

**Detection**: Check final summary "Duration: X seconds"

**Causes**:
- Too many locations (30s × APIs × locations)
- API timeouts with retries
- Database connection slow

**Recovery**:
1. Calculate expected duration: (locations × APIs × 30s)
2. Reduce timeout from 30s to 15s
3. Implement parallel location processing
4. Scale with location sharding

**Problem: Lamp Data Not Updating**

**Symptoms**: Stale `last_updated` timestamps in database

**Detection**: Query `current_conditions` table, check processor logs

**Causes**:
- Processor service down on Render
- All API sources failed for location
- Database write failure

**Recovery**:
1. `mcp__render__render_service_status`
2. `mcp__render__render_logs` service_type="background"
3. Test APIs manually with curl
4. `mcp__render__render_restart_service`

### Scaling Concerns

**API Call Volume**:
- Current: 2-6 locations × 2-3 APIs × 30s = 120-360s (acceptable)
- At Scale: 100 locations × 3 APIs × 30s = 9000s (exceeds 20-min window)
- Mitigation: Parallel processing, reduce delays with smart rate limiting

**Database Connections**:
- Current: New connection per query (inefficient)
- At Scale: Connection exhaustion
- Mitigation: SQLAlchemy pooling with `pool_size` and `max_overflow`

**API Quotas**:
- Current: Free tier <10 locations
- At Scale: OpenWeatherMap 1000 calls/day exceeded
- Mitigation: Paid tier or location-based caching with 10-min TTL

---

*Last Updated: 2025-09-30*
*Service: Render Background Worker*
*Schedule: Every 20 minutes*