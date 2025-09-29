# Web Application - Technical Documentation

## 1. Overview

**What it does**: Flask-based web server at surflampz.com providing user authentication, dashboard for real-time surf condition monitoring, lamp configuration management, and REST API endpoints for Arduino device polling.

**Why it exists**: Primary user interface for the Surf Lamp system - handles registration/login, displays live wave/wind data, allows threshold configuration, manages LED themes, and serves as the data bridge between Arduino devices and the background processor.

## 2. Technical Details

### What Would Break If This Disappeared?

- **Arduino Data Source**: Arduinos poll `/api/arduino/{id}/data` every 13 minutes - all devices go dark without this endpoint
- **User Management**: No registration, login, or preference updates - system becomes read-only
- **Dashboard Display**: Users lose visibility into current surf conditions
- **Threshold Configuration**: Cannot set wave/wind alert thresholds - Arduino LEDs show raw data only
- **Theme Selection**: Users stuck with default LED colors
- **Background Processor Integration**: Processor writes to database, but no user-facing view of that data
- **Password Recovery**: Email-based reset flow breaks entirely

### Critical Assumptions

**Database Assumptions**:
- PostgreSQL (Supabase) always available via `DATABASE_URL` env var
- SQLAlchemy ORM handles connection pooling and retries
- Tables exist: `users`, `lamps`, `current_conditions`, `password_reset_tokens`
- Foreign key constraints enforced: `lamps.user_id` → `users.user_id`, `current_conditions.lamp_id` → `lamps.lamp_id`

**Redis Assumptions**:
- Redis instance available at `REDIS_URL` for rate limiting and location change tracking
- Redis down = rate limiting fails open (allows all requests) via Flask-Limiter fallback
- Connection timeout: 30 seconds
- No persistence required (rate limit counters ephemeral)

**Session Management**:
- `SECRET_KEY` env var set and stable (changing invalidates all sessions)
- Flask sessions stored in client-side signed cookies (no server-side storage)
- Session expires on browser close (no "remember me" feature)

**Email Service**:
- SMTP server configured via Flask-Mail for password reset emails
- Email delivery not guaranteed (no retry logic)
- Token-based reset flow assumes emails arrive within token expiration window

**Timezone Assumptions**:
- `LOCATION_TIMEZONES` dict maps user locations to timezones for quiet hours calculation
- Unlisted locations default to no quiet hours (always show surf data)
- Server clock UTC-synchronized for pytz calculations

**Reverse Proxy**:
- Render deployment uses reverse proxy - `ProxyFix` middleware required to prevent redirect loops
- `X-Forwarded-For`, `X-Forwarded-Proto` headers trusted for rate limiting

**Arduino Polling Contract**:
- Arduinos expect exact JSON response format from `/api/arduino/{id}/data`
- Field renames break deployed devices until firmware reflashed
- Units must match Arduino expectations: cm, m/s, degrees, knots

### Where Complexity Hides

**Edge Cases**:
- **Concurrent Location Updates**: User changes location rapidly → Redis rate limit key race condition if multiple requests in-flight
- **Quiet Hours Timezone Missing**: Location not in `LOCATION_TIMEZONES` → `is_quiet_hours()` returns False silently, no error logged
- **Password Reset Token Collision**: `secrets.token_urlsafe(32)` generates token, SHA-256 hashed - theoretical collision but astronomically unlikely
- **Dashboard No Conditions**: Lamp exists but `current_conditions` row doesn't → template shows "No data yet" (graceful degradation)
- **Arduino ID Reuse**: Multiple lamps with same `arduino_id` → first match wins in database query (should be unique constraint)
- **Theme Name Mismatch**: User database has invalid theme string → Arduino defaults to "classic_surf" (no server-side validation)

**Race Conditions**:
- **Session vs Database State**: User updates threshold via dashboard → background processor reads old value before transaction commits → stale data sent to Arduino for up to 20 minutes
- **Location Change Rate Limit**: `location_changes` dict stored in-memory (not Redis) → multi-instance deployments have separate counters (limit bypassed)
- **Password Reset Token Expiry**: Token checked for expiry, then used → if expires between check and use (unlikely but possible), user sees cryptic error

**Rate Limiting Concerns**:
- **Login Attempts**: Flask-Limiter applies fixed-window strategy → attacker can brute force at limit boundary (e.g., 9 attempts at 59 seconds, 9 more at 61 seconds)
- **Location Changes**: Custom in-memory dict `location_changes` tracks per-user timestamps → memory leak if users never logout (dict grows unbounded)
- **Arduino Polling**: No rate limit on `/api/arduino/{id}/data` → compromised device could DDoS endpoint (trust-based security)

**Commented-Out Code & Workarounds**:
- Line 52: `ProxyFix` middleware added to fix Render redirect loops - indicates deployment-specific issues discovered in production
- Git history shows theme system underwent major refactor (`b804c39 → a421ed3 → 0f53817`) - user feedback drove simplification
- Form validation evolved (`19b4741 "Fix registration form validation issues"`) - suggests early XSS/injection attempts

### Stories the Code Tells

**Git History Insights**:
- **Quiet Hours Feature** (`30dd66c "Implement timezone-aware quiet hours"`): Added mid-development, not original design - suggests user complaint about nighttime blinking LEDs
- **Theme System Evolution** (`b804c39 → 0f53817`): 3 commits in sequence simplifying themes, reducing red colors - indicates user confusion with too many options + psychological aversion to red (alarm color)
- **Sport Selection** (`5fda07e "Add sport selection feature"`): Late addition - originally surfing-only, expanded to kitesurfing/windsurfing/SUP
- **Form Validation Fixes** (`19b4741`): Security hardening after initial deployment - bleach library added for HTML sanitization

**Design Philosophy**:
- **Pull-Based Arduino Architecture**: Arduinos poll server instead of server pushing - simpler deployment, no WebSockets, stateless HTTP
- **Defensive Form Validation**: Custom `SanitizedStringField` using bleach, regex patterns for names/emails, extensive edge case checks
- **Graceful Degradation**: Missing data returns defaults (0 values) instead of 500 errors - Arduino keeps functioning with stale data
- **Security-First**: CSRF protection via Flask-WTF, bcrypt password hashing, rate limiting on auth endpoints

## 3. Architecture & Implementation

### Data Flow

**User Registration Flow**:
```
[User Fills Form] → [WTForms Validation] → [Bleach Sanitization]
         ↓
[Check Email Unique] → [Bcrypt Hash Password] → [Insert User + Lamp to DB]
         ↓
[Redirect to Dashboard] → [Session Cookie Set]
```

**Dashboard Load Flow**:
```
[User Requests /dashboard] → [Check Session Cookie] → [Query DB for User + Lamps + CurrentConditions]
         ↓
[Calculate Quiet Hours via Timezone] → [Format Data for Template]
         ↓
[Render dashboard.html] → [Display Wave Height, Period, Wind Speed/Direction]
```

**Arduino Data Fetch Flow** (every 13 minutes):
```
[Arduino GET /api/arduino/{id}/data] → [Query Lamp + CurrentConditions + User by arduino_id]
         ↓
[Calculate Quiet Hours] → [Format JSON Response]
         ↓
{
  wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg,
  wave_threshold_cm, wind_speed_threshold_knots,
  led_theme, quiet_hours_active, last_updated, data_available
}
```

**Threshold Update Flow**:
```
[User Updates Threshold] → [Redis Rate Limit Check] → [Update users Table]
         ↓
[Background Processor Reads on Next Cycle (20 min)] → [Writes to current_conditions]
         ↓
[Arduino Polls /api/arduino/{id}/data (13 min)] → [Gets New Threshold]
```

**Password Reset Flow**:
```
[User Submits Email] → [Generate Token] → [Hash with SHA-256] → [Store in password_reset_tokens]
         ↓
[Send Email with Token URL] → [User Clicks Link] → [Verify Token Not Expired]
         ↓
[User Sets New Password] → [Bcrypt Hash] → [Update users Table] → [Delete Token]
```

### Key Functions & Classes

**Authentication & Sessions**:
- `login_required(f)`: Decorator checking `session['user_id']` exists, redirects to login if not
- `register()`: WTForms validation → bleach sanitization → bcrypt hashing → DB insert
- `login()`: Email lookup → bcrypt password verify → session cookie set
- `logout()`: Clear session, redirect to index

**Dashboard & Data Display**:
- `dashboard()`: Queries `get_user_lamp_data()` → calculates wind direction compass → renders template
- `dashboard_view(view_type)`: Alternate dashboard layouts (unused in production)
- `convert_wind_direction(degrees)`: Maps 0-360° to 16-point compass (N, NNE, NE, ...)

**User Preferences**:
- `update_location()`: Redis rate limit → validate against `SURF_LOCATIONS` list → update `users.location`
- `update_threshold()`: Update `users.wave_threshold_m` (meters → cm conversion for Arduino)
- `update_wind_threshold()`: Update `users.wind_threshold_knots`
- `update_theme()`: Update `users.theme` (classic_surf, vibrant_mix, tropical_paradise, ocean_sunset, electric_vibes)

**Arduino API Endpoints**:
- `get_arduino_surf_data(arduino_id)`: Main pull endpoint - joins Lamp + CurrentConditions + User, calculates quiet hours, returns JSON
- `handle_arduino_callback()`: Legacy push endpoint (rarely used)
- `arduino_status_overview()`: Admin endpoint showing all lamps and last callback times

**Password Recovery**:
- `forgot_password()`: Generate token → hash → email link
- `reset_password_form(token)`: Verify token → allow password change → delete token
- `send_reset_email(user_email, username, token)`: Flask-Mail SMTP delivery

**Quiet Hours Logic**:
- `is_quiet_hours(user_location, quiet_start_hour=22, quiet_end_hour=6)`: Timezone-aware check (10 PM - 6 AM local time)
- Uses `pytz` to convert server UTC to user's local timezone
- Handles overnight ranges (22:00 → 06:00 next day)

**Rate Limiting Helpers**:
- `check_location_change_limit(user_id)`: Custom in-memory rate limiter (5 changes per hour)
- Flask-Limiter on `/login` and `/register`: Fixed-window strategy

### Configuration

**Environment Variables (Required)**:
```bash
SECRET_KEY          # Flask session signing key (critical - rotation invalidates sessions)
DATABASE_URL        # PostgreSQL connection string (Supabase)
REDIS_URL           # Redis connection string (rate limiting)
MAIL_SERVER         # SMTP server for password reset emails
MAIL_PORT           # SMTP port (587 for TLS)
MAIL_USERNAME       # SMTP auth username
MAIL_PASSWORD       # SMTP auth password
MAIL_USE_TLS        # Enable TLS (True)
MAIL_DEFAULT_SENDER # From address for emails
```

**Hardcoded Configuration**:
```python
SURF_LOCATIONS = [
    "Hadera, Israel", "Tel Aviv, Israel", "Ashdod, Israel",
    "Haifa, Israel", "Netanya, Israel", "Ashkelon, Israel", "Nahariya, Israel"
]

LOCATION_TIMEZONES = {
    "Hadera, Israel": "Asia/Jerusalem",
    "Tel Aviv, Israel": "Asia/Jerusalem",
    # ... 7 locations mapped to timezones
}

# Rate Limiting
limiter = Limiter(strategy="fixed-window")  # Flask-Limiter defaults
location_changes = {}  # In-memory per-user timestamp tracking
```

**Theme Configuration** (sent to Arduino):
- classic_surf, vibrant_mix, tropical_paradise, ocean_sunset, electric_vibes
- Theme names must match Arduino firmware `getThemeColors()` function

## 4. Integration Points

### What Calls This Component

**User Interactions**:
- Web browser → `/register`, `/login`, `/dashboard` (HTML pages)
- Dashboard AJAX → `/update-location`, `/update-threshold`, `/update-theme` (JSON endpoints)

**Arduino Devices**:
- Arduino firmware → `GET /api/arduino/{arduino_id}/data` (every 13 minutes, pull mode)
- Arduino firmware → `POST /api/arduino/callback` (rarely used, legacy push mode)

**Background Processor**:
- No direct calls - processor writes to database, web app reads from database (decoupled via DB)

**Email Service**:
- Flask-Mail → SMTP server (outbound only, no incoming email handling)

### What This Component Calls

**Database (SQLAlchemy)**:
- `data_base.py` functions: `add_user_and_lamp()`, `get_user_lamp_data()`, `update_user_location()`
- Direct queries via `SessionLocal()` for Arduino API endpoints

**Redis**:
- Flask-Limiter storage backend (automatic via `storage_uri`)
- Custom `location_changes` dict (in-memory, not Redis - architectural inconsistency)

**External Services**:
- SMTP server via Flask-Mail (password reset emails)

**Templates (Jinja2)**:
- `dashboard.html`, `register.html`, `login.html`, `forgot_password.html`, `reset_password.html`, `themes.html`

### Data Contracts

**Arduino Pull API Response** (`/api/arduino/{id}/data`):
```json
{
  "wave_height_cm": 150,           // Integer - converted from meters * 100
  "wave_period_s": 8.0,            // Float - seconds
  "wind_speed_mps": 5,             // Integer - meters per second (Arduino converts to knots)
  "wind_direction_deg": 180,       // Integer - 0-360 degrees
  "wave_threshold_cm": 100,        // Integer - user's alert threshold
  "wind_speed_threshold_knots": 15, // Integer - user's wind alert threshold
  "led_theme": "classic_surf",     // String - must match Arduino theme names
  "quiet_hours_active": false,     // Boolean - server-calculated from timezone
  "last_updated": "2025-09-30T12:34:56Z", // ISO 8601 timestamp
  "data_available": true           // Boolean - false if no conditions yet
}
```

**Dashboard AJAX Endpoints** (POST):
- `/update-location`: `{location: "Tel Aviv, Israel"}` → `{success: true/false, message: "..."}`
- `/update-threshold`: `{threshold: 1.2}` → `{success: true/false, message: "..."}`
- `/update-wind-threshold`: `{wind_threshold: 20}` → `{success: true/false, message: "..."}`
- `/update-theme`: `{theme: "ocean_sunset"}` → `{success: true/false, message: "..."}`

**Session Cookie**:
- Key: `user_id` (integer)
- Signed with `SECRET_KEY` (Flask default session implementation)
- Expires on browser close

**Database Schema Dependencies**:
- `users` table: user_id (PK), email, password_hash, location, wave_threshold_m, wind_threshold_knots, theme, sport_type
- `lamps` table: lamp_id (PK), user_id (FK), arduino_id (unique), arduino_ip
- `current_conditions` table: lamp_id (PK/FK), wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, last_updated
- `password_reset_tokens` table: id (PK), user_id (FK), token_hash, expiration_time

## 5. Troubleshooting & Failure Modes

### Common Issues

**Problem: Users Can't Login (Bcrypt Errors)**
- **Symptoms**: 500 error on login page, logs show bcrypt exceptions
- **Detection**: Check logs for "bcrypt" errors or "password verification failed"
- **Causes**:
  - `SECRET_KEY` changed (invalidates sessions but shouldn't affect bcrypt)
  - Database password_hash column corrupted
  - Bcrypt library version mismatch (rare)
- **Recovery**:
  1. Verify `SECRET_KEY` environment variable set
  2. Check database connectivity: `psql $DATABASE_URL -c "SELECT count(*) FROM users;"`
  3. Test bcrypt: `python -c "from flask_bcrypt import Bcrypt; print(Bcrypt().generate_password_hash('test'))"`
  4. If all else fails: password reset flow or manual password update in database

**Problem: Arduino Gets 404 on Data Endpoint**
- **Symptoms**: Arduino serial logs show "HTTP error 404", LEDs frozen
- **Detection**: Check Render logs for 404s on `/api/arduino/{id}/data`
- **Causes**:
  - `arduino_id` not in database (lamp not registered)
  - Route typo in Arduino firmware (should be `/api/arduino/{id}/data` not `/api/arduino/data/{id}`)
  - Web service restarted, ServerDiscovery cached old URL
- **Recovery**:
  1. Verify arduino_id in database: Check Supabase `lamps` table
  2. Test endpoint manually: `curl https://surflampz.com/api/arduino/4433/data`
  3. Check Arduino serial logs for exact URL being requested
  4. Force ServerDiscovery refresh on Arduino: `GET http://{arduino_ip}/api/discovery-test`

**Problem: Quiet Hours Not Working**
- **Symptoms**: LEDs blinking at night despite quiet hours feature
- **Detection**: Check Arduino status endpoint `quiet_hours_active` field
- **Causes**:
  - User location not in `LOCATION_TIMEZONES` dict
  - Server timezone misconfigured (not UTC)
  - Arduino firmware ignoring `quiet_hours_active` flag
- **Recovery**:
  1. Test quiet hours API: `curl https://surflampz.com/api/arduino/4433/data | jq .quiet_hours_active`
  2. Check user's location matches timezone dict: `grep -i "tel aviv" web_and_database/app.py`
  3. Verify server time: `date -u` (should show UTC)
  4. Add missing location to `LOCATION_TIMEZONES` dict, redeploy

**Problem: Rate Limiting Not Working Across Instances**
- **Symptoms**: Users bypass location change limits on multi-instance Render deployments
- **Detection**: Check `location_changes` dict in logs (will be empty on other instances)
- **Causes**: `location_changes` dict stored in-memory (not Redis) - architectural flaw
- **Recovery**:
  1. Short-term: Scale Render to 1 instance only
  2. Long-term: Migrate `location_changes` dict to Redis (requires code change)

**Problem: Dashboard Shows Stale Data**
- **Symptoms**: Dashboard displays old surf conditions, Arduino shows fresh data
- **Detection**: Compare dashboard timestamp with `current_conditions.last_updated` in database
- **Causes**:
  - Browser caching (unlikely with Flask defaults)
  - Background processor stopped writing to database
  - User looking at wrong lamp (multiple lamps per user)
- **Recovery**:
  1. Hard refresh: Ctrl+Shift+R (clear browser cache)
  2. Check background processor logs on Render
  3. Verify `current_conditions` table updated recently: `SELECT last_updated FROM current_conditions WHERE lamp_id = X;`

**Problem: Password Reset Emails Not Arriving**
- **Symptoms**: User requests reset, no email received
- **Detection**: Check Render logs for Flask-Mail SMTP errors
- **Causes**:
  - SMTP credentials wrong (`MAIL_USERNAME`, `MAIL_PASSWORD`)
  - SMTP server blocking connection (firewall, rate limit)
  - Email landed in spam folder
  - Token generated but email send failed silently
- **Recovery**:
  1. Verify SMTP config: `echo $MAIL_SERVER $MAIL_PORT $MAIL_USERNAME`
  2. Test SMTP manually: `python -c "from flask_mail import Mail, Message; ..."`
  3. Check spam folder
  4. Manually generate reset token and send via alternative channel (support ticket)

### Diagnostic Log Patterns

**Healthy Operation**:
```
INFO - 📥 Arduino 4433 requesting surf data (PULL mode)
INFO - ✅ Returning surf data for Arduino 4433: wave=150cm
INFO - User johndoe logged in successfully
INFO - Location updated for user 42: Tel Aviv, Israel
```

**Redis Connection Issues**:
```
ERROR - Redis connection failed: ConnectionError
WARNING - Rate limiter falling back to in-memory storage
```

**Database Connection Issues**:
```
ERROR - SQLAlchemy error: (psycopg2.OperationalError) FATAL: too many connections
ERROR - ❌ Error getting surf data for Arduino 4433: connection timeout
```

**Form Validation Failures**:
```
WARNING - Registration failed: Email already exists
WARNING - Login failed: Invalid credentials for user@example.com
WARNING - Suspicious email pattern detected: test@example..com
```

**Quiet Hours Calculation**:
```
INFO - 🌙 Quiet hours active for Tel Aviv, Israel - threshold alerts disabled
INFO - Quiet hours check for San Diego, USA: False (daytime)
```

### Scaling Concerns

**Session Storage**:
- **Current**: Client-side signed cookies (stateless)
- **At Scale**: 10k concurrent users = no server-side storage needed (good)
- **Concern**: Session data in cookie (max 4KB) - currently only stores `user_id` (negligible)

**Database Connection Pool**:
- **Current**: SQLAlchemy default pool (5 connections)
- **At Scale**: 1000 requests/min ÷ 5 connections = 200 req/connection/min (fine if queries fast)
- **Mitigation**: Increase pool size via `SQLALCHEMY_POOL_SIZE` env var, optimize slow queries

**Redis Rate Limiting**:
- **Current**: Fixed-window strategy
- **At Scale**: 10k users × 5 location changes/hour = 50k Redis operations/hour (negligible load)
- **Concern**: `location_changes` dict in-memory grows unbounded (memory leak)
- **Mitigation**: Migrate to Redis-backed storage, add TTL expiry

**Arduino Polling Load**:
- **Current**: 1 Arduino = 110 requests/day (13-min interval)
- **At Scale**: 10k Arduinos = 1.1M requests/day = ~13 requests/second
- **Mitigation**: CDN caching with 1-min TTL (reduces DB queries), read replicas for Arduino endpoints

**Background Processor Lag**:
- **Current**: 20-min cycle writes to database, web app reads immediately
- **At Scale**: If processor takes >20 min to process all locations, data freshness degrades
- **Concern**: Dashboard shows stale data while processor catches up
- **Mitigation**: Horizontal scaling of processor (multiple instances processing different location subsets)

**Email Delivery**:
- **Current**: Synchronous Flask-Mail send (blocks request until email sent)
- **At Scale**: Password reset requests during SMTP slowness cause 30-second page loads
- **Mitigation**: Async task queue (Celery + Redis) for email sending

**Static Asset Serving**:
- **Current**: Flask serves CSS/JS directly (no CDN)
- **At Scale**: Bandwidth costs increase, slow page loads globally
- **Mitigation**: Serve static assets from CloudFlare CDN or Render's built-in CDN

---

*Last Updated: 2025-09-30*
*Deployment: Render Web Service (gunicorn + Flask)*
*URL: https://surflampz.com*