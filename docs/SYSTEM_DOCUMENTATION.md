# Surf Lamp System Documentation

## Overview
The Surf Lamp system displays real-time surf conditions using LED visualizations on Arduino-based devices. The system consists of a web dashboard, background data processor, and Arduino firmware that work together to fetch, process, and display surf data.

## Architecture

⚠️ **CRITICAL ARCHITECTURAL PRINCIPLES** ⚠️
===============================================

**DO NOT MODIFY these core design decisions without understanding the production issues they solve:**

1. **🔄 PULL-BASED COMMUNICATION**
   - Arduino devices fetch data from web server every 13 minutes (FETCH_INTERVAL = 780000ms)
   - Background processor ONLY updates database, never pushes to Arduino
   - No Arduino IP tracking needed - Arduino initiates all communication via server discovery
   - Eliminates network complexity, firewall issues, and Arduino reliability problems

2. **📍 LOCATION-BASED PROCESSING**
   - API calls grouped by location to eliminate duplicate requests
   - Prevents 429 rate limiting errors (solved 25-minute processing issue)
   - Reduces API calls by ~70% while maintaining data completeness

3. **🎯 MULTI-SOURCE PRIORITY SYSTEM**
   - Each location uses multiple API sources with priority ordering
   - Data merging ensures complete surf conditions (wave + wind data)
   - Automatic failover prevents data loss when primary APIs fail

### Core Components

1. **Web Application** (`web_and_database/app.py`)
   - Flask-based dashboard and API server
   - User authentication and session management
   - Arduino data endpoint for pull-based architecture
   - Location-aware configuration system

2. **Background Processor** (`surf-lamp-processor/background_processor.py`)
   - **Location-based processing**: Groups API calls by location to eliminate duplicates
   - Fetches data from external surf APIs every 20 minutes with multi-source priority
   - **Prevents rate limiting**: 10-second delays + exponential backoff (60s → 120s → 240s)
   - **Data merging**: Combines wave data (Isramar) with wind data (Open-Meteo) per location
   - **Pull-based architecture**: Only updates database, Arduino devices fetch data independently

3. **Arduino Firmware**
   - **3-Strip Version** (`arduino_code/surf_lamp_3_strips/arduinomain_lamp.ino`) - Original with 3 separate LED strips
   - **Single-Strip Version** (`arduino_code/surf_lamp_single_strip/surf_lamp_single_strip.ino`) - 47-LED continuous strip
   - ESP32-based device that pulls data from server every 13 minutes
   - Controls LED strips for visual surf condition display
   - Implements threshold-based blinking alerts

4. **Database Schema** (defined in `web_and_database/data_base.py`)
   - PostgreSQL database with user accounts, lamps, and surf conditions
   - Dynamic location-to-API endpoint mapping

## Data Flow

```
External APIs → Background Processor → Database → Web API → Arduino → LED Display
     ↓                ↓                    ↓         ↓         ↓
   20min           Every 20min         Real-time   31min   Immediate
```

### Wind Speed Unit Handling

The system ensures consistent wind speed units throughout the data pipeline:

**API Configuration:**
- All Open-Meteo API URLs include `&wind_speed_unit=ms` parameter
- APIs return wind speed data directly in meters per second (m/s)
- No unit conversion needed in background processor

**Data Processing:**
1. **External APIs**: Return wind speed in m/s (via URL parameter)
2. **Background Processor**: Extracts `wind_speed_10m` as `wind_speed_mps`
3. **Database**: Stores wind speed values in m/s
4. **Arduino API**: Sends wind speed as `"wind_speed_mps": <integer>`
5. **Arduino**: Receives m/s, converts to knots only for threshold comparison

**Arduino Internal Conversion:**
```cpp
float windSpeedInKnots = windSpeed_mps * 1.94384;  // For threshold comparison
int windSpeedLEDs = constrain(static_cast<int>(windSpeed * 10.0 / 22.0), 1, NUM_LEDS_CENTER - 2);  // Uses m/s directly
```

### Detailed Flow
1. **Background Processor** runs every 20 minutes with location-based processing
2. **Groups lamps by location** to eliminate duplicate API calls (reduces calls by ~70%)
3. **Multi-source data fetching** per location:
   - Priority 1: Wave data (Isramar for Israel locations)
   - Priority 2+: Wind data (Open-Meteo forecast, GFS backup)
4. **Data merging**: Combines fields from all sources for complete surf conditions
5. **Database updates**: Stores merged data in `current_conditions` table
6. **Arduino** independently pulls data every 31 minutes (`FETCH_INTERVAL = 1860000ms`)
7. **Arduino** updates LED display immediately upon receiving data

## Location System (Database-Driven)

**Database Tables:** `users`, `lamps`, `usage_lamps`, `daily_usage`

The system uses a **database-driven location mapping** where API endpoints are configured per lamp and grouped by user location for efficient processing:

### Database Schema for Location-Based Processing

```sql
-- Users define locations
users (user_id, location, preferred_output, wave_threshold_m, wind_threshold_knots)

-- Lamps belong to users and inherit location
lamps (lamp_id, user_id, arduino_id, last_updated)  -- arduino_ip removed in commit 1e96bc8

-- API endpoints are configured per lamp with priorities
usage_lamps (lamp_id, usage_id, api_key, http_endpoint, endpoint_priority)

-- Daily usage tracks API source information
daily_usage (usage_id, website_url, ...)
```

### Location-Based Processing Query

The background processor uses this query to group API calls by location:

```sql
SELECT DISTINCT
    u.location,
    ul.usage_id,
    du.website_url,
    ul.api_key,
    ul.http_endpoint,
    ul.endpoint_priority
FROM usage_lamps ul
JOIN daily_usage du ON ul.usage_id = du.usage_id
JOIN lamps l ON ul.lamp_id = l.lamp_id
JOIN users u ON l.user_id = u.user_id
WHERE ul.http_endpoint IS NOT NULL
ORDER BY u.location, ul.endpoint_priority
```

### Location-Based Multi-Source Processing

The system implements **location-based processing** with multi-source data merging:

**Architecture Benefits:**
- **Eliminates Duplicate API Calls:** Groups lamps by location (reduces API calls by ~70%)
- **Rate Limiting Prevention:** 10-second delays + exponential backoff for 429 errors
- **Data Completeness:** Merges wave and wind data from multiple sources per location
- **Geographic Optimization:** Uses location-specific APIs (Isramar for Israeli locations)

**Processing Flow per Location:**
1. **Query Database:** Get all unique API endpoints for the location (ordered by priority)
2. **Fetch Multi-Source Data:** Call each API in priority order with proper delays
3. **Data Merging:** Combine fields from all sources into complete surf conditions
4. **Update All Lamps:** Apply merged data to all lamps in that location

**Example: Hadera, Israel Processing**
- **Location Query:** Groups 6 lamps in Hadera, Israel
- **API Sources:** 4 unique endpoints (deduplicates 14 database entries)
  - Priority 1: Isramar (wave_height_m, wave_period_s)
  - Priority 2: Open-Meteo forecast (wind_speed_mps, wind_direction_deg)
  - Priority 3: Open-Meteo GFS (backup wind data)
- **Result:** Combined data with both wave and wind fields for all 6 lamps

**Rate Limiting Protection:**
- 10-second delays between ALL API calls
- Exponential backoff for 429 errors: 60s → 120s → 240s
- Multi-source redundancy ensures data availability
- Processing time reduced from 25 minutes to <2 minutes

### Location Change Process - Complete Program Execution Flow

**Function:** `update_user_location()` in `data_base.py:467-540`

#### **Step 1: Configuration in Code**
```python
MULTI_SOURCE_LOCATIONS = {
    "Tel Aviv, Israel": [
        {"url": "https://marine-api.open-meteo.com/...", "priority": 1, "type": "wave"},
        {"url": "https://api.open-meteo.com/v1/forecast?...", "priority": 2, "type": "wind"}
    ]
}
```

#### **Step 2: User Dashboard Action**
- User selects new location → JavaScript calls `/update-location` endpoint

#### **Step 3: Database Mapping Process**
1. **Lookup:** System finds `new_location` in `MULTI_SOURCE_LOCATIONS`
2. **Delete:** Removes existing `usage_lamps` records for lamp
3. **Create:** For each API source in location config:
   ```python
   UsageLamps(
       lamp_id=lamp.lamp_id,
       http_endpoint=source['url'],           # Full API URL with coordinates
       endpoint_priority=source['priority']   # 1, 2, 3...
   )
   ```

#### **Step 4: Background Processor Discovery**
Every 20 minutes, queries database:
```sql
SELECT ul.http_endpoint, ul.endpoint_priority, u.location
FROM usage_lamps ul
JOIN lamps l ON ul.lamp_id = l.lamp_id
ORDER BY ul.lamp_id, ul.endpoint_priority  -- Priority order!
```

#### **Step 5: Priority-Based API Processing**
- **Priority 1:** Try primary endpoint (e.g., Isramar wave data)
- **Priority 2:** Try secondary endpoint (e.g., Open-Meteo wind)
- **Priority 3:** Try backup endpoint (e.g., GFS wind backup)
- **Failover:** If endpoint fails, automatically tries next priority

#### **Step 6: Data Flow Chain**
```
Code Config → User Selection → Database Update → Background Processor →
Priority API Calls → Data Storage → Arduino Pull → LED Display
```

**Timeline:**
- Database update: Immediate
- Background processor pickup: Up to 20 minutes
- Arduino data refresh: Up to 31 minutes

**Important:** API URL changes in code require location change to update database endpoints

## Arduino LED System

### LED Theme System

**User Flow:**
1. User selects "Light" or "Dark" theme in dashboard
2. JavaScript sends POST to `/update-theme` endpoint
3. Server updates `users.theme` field in database ("day" or "night")
4. Arduino pulls theme via `/api/arduino/{id}/data` endpoint (every 31 minutes)
5. Arduino applies theme colors immediately upon receiving update

**Theme Colors:**
- **Day Theme:** Green (120°), Cyan (180°), Orange (30°) - Bright, vibrant colors
- **Night Theme:** Blue (240°), Purple (270°), Red (0°) - Darker, warmer colors

**Color Mapping:**
```cpp
// Wind Speed: Green (day) / Blue (night)
// Wave Height: Cyan (day) / Purple (night)
// Wave Period: Orange (day) / Red (night)
```

### Arduino Hardware Variants

The system supports two hardware configurations with different LED arrangements:

#### **3-Strip Lamp** (Original - Arduino ID 4433)
**Firmware:** `arduino_code/surf_lamp_3_strips/arduinomain_lamp.ino`

**Hardware:**
- 3 separate WS2812B LED strips on different GPIO pins
- Total: 50 LEDs (20 center + 15 right + 15 left)

**LED Configuration:**
```cpp
#define LED_PIN_CENTER 4        // Wind speed + direction
#define LED_PIN_SIDE 2          // Wave height (right strip)
#define LED_PIN_SIDE_LEFT 5     // Wave period (left strip)

#define NUM_LEDS_CENTER 20      // Wind speed + direction LEDs
#define NUM_LEDS_RIGHT 15       // Wave height LEDs
#define NUM_LEDS_LEFT 15        // Wave period LEDs
```

**Wind Scaling:** Maps 0-13 m/s to 0-18 LEDs (formula: `18.0/13.0`)

#### **Single-Strip Wrapped Lamp** (New - Arduino ID 1)
**Firmware:** `arduino_code/surf_lamp_single_strip/surf_lamp_single_strip.ino`
**Documentation:** `arduino_code/surf_lamp_single_strip/LED_VALUES_REFERENCE.md`

**Hardware:**
- Single continuous 47-LED WS2812B strip wrapped to appear as 3 strips
- Uses array index mapping to simulate 3 separate strips

**LED Configuration:**
```cpp
#define LED_PIN 2               // Single GPIO pin
#define TOTAL_LEDS 47           // One continuous strip

// LED Section Mapping (array indices)
#define WAVE_HEIGHT_START 1      // LEDs 1-14 (bottom-up)
#define WAVE_PERIOD_START 33     // LEDs 33-46 (bottom-up)
#define WIND_SPEED_START 30      // LEDs 30-17 (REVERSE direction)

#define STATUS_LED_INDEX 30      // Status indicator
#define WIND_DIRECTION_INDEX 17  // Wind direction indicator
```

**Wind Scaling:** Maps 0-13 m/s to 0-12 LEDs (formula: `12.0/13.0` - fewer available LEDs)

**Key Difference:** Single-strip version uses reverse direction for wind speed LEDs (30→17) due to physical wrapping layout.

**Both variants:**
- Use identical pull-based communication
- Support all theme modes and threshold alerts
- Fetch data every 13 minutes from `/api/arduino/<id>/data`
- Share the same data processing logic

### Wind Direction Colors
**Function:** `setWindDirection()` in `arduinomain_lamp.ino:316-328`
```cpp
// Wind direction color coding (based on LED 18 - the top LED)
// int northLED = NUM_LEDS_CENTER - 1;  // LED #18 (0-indexed)
if (windDirection < 45 || windDirection >= 315) {
    leds_center[northLED] = CRGB::Green;   // North - Green
} else if (windDirection >= 45 && windDirection < 135) {
    leds_center[northLED] = CRGB::Yellow;  // East - Yellow
} else if (windDirection >= 135 && windDirection < 225) {
    leds_center[northLED] = CRGB::Red;     // South - Red
} else if (windDirection >= 225 && windDirection < 315) {
    leds_center[northLED] = CRGB::Blue;    // West - Blue
}
```

### Threshold Alerts
**Functions:** `applyWindSpeedThreshold()` and `applyWaveHeightThreshold()` in `arduinomain_lamp.ino:212-233`

- **Wave Height Alert:** When `wave_height_cm >= wave_threshold_cm` → Blue LEDs blink
- **Wind Speed Alert:** When `wind_speed_knots >= wind_speed_threshold_knots` → White LEDs blink
- **Blinking:** Smooth sine wave pulsing (not harsh on/off)

### Data Processing
**Function:** `updateSurfDisplay()` in `arduinomain_lamp.ino:633-654`

LED calculations:
```cpp
int windSpeedLEDs = constrain(static_cast<int>(windSpeed * 10.0 / 22.0), 1, NUM_LEDS_CENTER - 2);
int waveHeightLEDs = constrain(static_cast<int>(waveHeight_cm / 25) + 1, 0, NUM_LEDS_RIGHT);
int wavePeriodLEDs = constrain(static_cast<int>(wavePeriod), 0, NUM_LEDS_LEFT);
```

With the updated LED counts:
- **Wind Speed**: Scales 0-22 m/s to 1-17 LEDs (reserves top 2 LEDs for direction indicator)
- **Wave Height**: Every 25cm = 1 LED, up to 15 LEDs maximum
- **Wave Period**: Direct mapping up to 15 LEDs maximum

## API Endpoints

### Arduino Data Endpoint
**Route:** `GET /api/arduino/<arduino_id>/data`
**File:** `web_and_database/app.py:762-817`

Returns surf data formatted for Arduino consumption:
```json
{
    "wave_height_cm": 40,
    "wave_period_s": 5.2,
    "wind_speed_mps": 3,
    "wind_direction_deg": 340,
    "wave_threshold_cm": 100,
    "wind_speed_threshold_knots": 22,
    "last_updated": "2025-09-13T16:48:53.253866",
    "data_available": true
}
```

### Key Features:
- Pulls user's personal thresholds from database
- Converts wave height from meters to centimeters
- Rounds wind speed to integers
- Returns safe defaults if no data available
- **Timezone Handling (Commit 4f38fb6):** All timestamps use `datetime.now(timezone.utc)` for consistent UTC timestamps across deployments

## Database Schema

### Core Tables - Implementation Reference
**USE CASE:** SQLAlchemy implementation details and field specifications
**AUDIENCE:** Backend developers, API integration, code maintenance
**FILE:** `web_and_database/data_base.py:74-223`

```sql
-- Users table
users (
    user_id PRIMARY KEY,
    username UNIQUE,
    email UNIQUE,
    location,                    -- Dynamic location (e.g., "Tel Aviv, Israel")
    wave_threshold_m FLOAT,      -- User's wave height alert threshold
    wind_threshold_knots FLOAT   -- User's wind speed alert threshold
)

-- Lamps table
lamps (
    lamp_id PRIMARY KEY,
    user_id FOREIGN KEY,
    arduino_id UNIQUE,           -- Physical Arduino device ID (also called "Device ID" in UI)
    last_updated TIMESTAMP       -- Last successful data sync
    -- arduino_ip removed in commit 1e96bc8: pull-based architecture doesn't need IP tracking
)

-- Current surf conditions
current_conditions (
    lamp_id PRIMARY KEY,
    wave_height_m FLOAT,
    wave_period_s FLOAT,
    wind_speed_mps FLOAT,
    wind_direction_deg INTEGER,
    last_updated TIMESTAMP
)

-- API endpoint configurations (enables dynamic location system)
usage_lamps (
    usage_id,
    lamp_id,
    http_endpoint TEXT,          -- Full API URL with coordinates
    endpoint_priority INTEGER   -- 1=highest priority (wave data), 2=wind data
)

-- Password reset tokens (added in commit 181ee7d)
password_reset_tokens (
    id UUID PRIMARY KEY,
    user_id FOREIGN KEY,
    token_hash VARCHAR(128) UNIQUE,  -- Hashed token for security
    expiration_time TIMESTAMP,       -- Token valid for 20 minutes
    created_at TIMESTAMP,
    used_at TIMESTAMP,               -- Prevents token reuse
    is_invalidated BOOLEAN           -- Manual revocation flag
)
```

**Database Maintenance:**
- `cleanup_expired_password_reset_tokens()` function deletes tokens older than 24 hours
- Script: `/cleanup_tokens.py` - recommended cron: daily at 3 AM

## Timing and Synchronization

### Update Intervals
- **Background Processor:** Every 20 minutes (defined in `background_processor.py:810`)
- **Arduino Fetch:** Every 31 minutes (`FETCH_INTERVAL = 1860000ms` in Arduino code)
- **Dashboard Updates:** Real-time (when user refreshes)

### Threshold Change Propagation
1. User changes threshold in dashboard → Database update (immediate)
2. Next Arduino fetch cycle → Sees new threshold (up to 31 minutes)
3. Arduino applies new threshold logic → LED behavior changes

### Theme Change Propagation
1. User changes LED theme in dashboard → Database update (immediate)
2. Next Arduino fetch cycle → Sees new theme (up to 31 minutes)
3. Arduino updates LED colors → All surf data displays in new theme colors

### Quiet Hours (Sleep Protection)
**Purpose**: Prevents threshold blinking during sleep hours to avoid waking users

**Implementation**: Timezone-aware system that disables threshold alerts during 10 PM - 6 AM local time

**Data Flow**:
1. Arduino requests data → Flask API checks user location and current time
2. If within quiet hours → `quiet_hours_active: true` flag sent to Arduino
3. Arduino displays normal surf conditions but **disables all threshold blinking**
4. At 6 AM local time → Automatic return to normal threshold alerts

**Code Locations**:
- **Flask Logic**: `web_and_database/app.py:92-121` (`is_quiet_hours()` function)
- **Arduino Logic**: `arduino/arduinomain_lamp.ino:270,282,297` (threshold functions)
- **Timezone Mapping**: `LOCATION_TIMEZONES` in both `app.py` and `background_processor.py`

**Features**:
- **Global Support**: Works for any timezone using pytz library
- **Preserves Thresholds**: Real user settings unchanged, only blinking disabled
- **Automatic**: No user configuration needed, based on location
- **Debuggable**: `quiet_hours_active` visible in Arduino status endpoint

**Benefits**: Users sleep undisturbed while maintaining surf data visualization

## System Infrastructure Components

### Redis Service - User Rate Limiting
**Purpose**: Rate limiting system to prevent API abuse and protect external weather service quotas

**Rate Limited User Actions**:
- **Location Changes**: Prevents users from rapidly switching between surf spots
- **Threshold Modifications**: Limits frequency of wave height and wind speed threshold updates
- **User Preference Updates**: Controls rate of other dashboard setting changes

**Architecture**: Backend checks Redis counters before processing user actions that would trigger API calls or database updates

**Integration Points**:
- Web application checks rate limits before updating user location in database
- Dashboard UI can display rate limit status to users
- Background processor benefits from reduced API call churn

**Benefits**:
- Protects weather API quotas from user-driven request spikes
- Maintains system stability during high usage periods
- Prevents accidental API quota exhaustion from rapid user interactions

### Nighttime LED Behavior Requirements
**Night Mode Operation**: Special LED behavior during nighttime hours that overrides normal surf condition display

**Functional Requirements**:
- **Time Detection**: System detects nighttime hours (typically 10 PM - 6 AM) based on user location timezone
- **Threshold Bypass**: Wave height and wind speed thresholds do not trigger blinking alerts during night hours
- **LED Pattern**: Only the top LED of each LED strip should illuminate during night mode
- **Theme Independence**: Night LED behavior works regardless of user's selected day/night theme colors

**User Experience Goals**:
- **Sleep Protection**: Provides subtle ambient lighting without disturbing sleep
- **Consistency**: Reliable gentle lighting during sleep hours regardless of surf conditions
- **Automatic Operation**: No user configuration required - based on location and time

**Implementation Considerations**:
- Requires timezone-aware logic in both Arduino firmware and web application
- Should preserve normal surf data collection and processing
- May need location-based sunset/sunrise calculations for more accurate night detection
- Arduino needs to receive night mode flag from server API

**Current Status**: Requirements documented - implementation needed in both Arduino firmware and web application

## Manufacturing and Production System

**Location:** `manufacturing_id/` directory
**Documentation:** `manufacturing_id/README.md`

### Overview
The manufacturing system is a complete production tooling suite that bridges hardware manufacturing and customer onboarding. It enables efficient Arduino ID assignment, QR code generation, and seamless device registration.

### Components

#### 1. **ID Manager** (`id_manager.py`)
- Queries production database for next available Arduino ID
- Tracks used IDs and detects gaps in ID sequences
- Provides statistics for manufacturing team

#### 2. **QR Code Generator** (`qr_generator.py`)
- Generates QR codes linking to pre-filled registration URLs
- Format: `https://final-surf-lamp-web.onrender.com/register?id=4433`
- Creates single codes, batch sets, and print-ready sheets
- Adds human-readable labels with Arduino ID and URL

#### 3. **Manufacturing Dashboard** (`manufacturing_app.py`)
- Flask web application (port 5001) for production team
- Real-time statistics: next available ID, total used, highest ID
- Three core functions: single generation, batch processing, print sheets
- Duplicate detection prevents re-generating existing IDs

#### 4. **Database Integration**
- Connects directly to production Supabase database
- Real-time ID availability checking
- Automatic silent skipping of duplicate IDs in batch mode

### Production Workflow

**Phase 1: Device Preparation**
1. Manufacturing team opens dashboard at `http://localhost:5001`
2. Flash Arduino firmware with next available ID (e.g., ID 15)
3. Generate QR code for that ID
4. Print QR code on card (credit card size)
5. Package device with QR code card

**Phase 2: Customer Onboarding**
1. Customer receives device with QR code card
2. Scans QR code with phone camera
3. Registration page opens with **Device ID pre-filled** (Arduino ID auto-populated)
4. Customer enters name, email, password, location
5. Account created and lamp registered in database
6. Arduino fetches data and displays surf conditions

### QR Code Auto-Fill System

**Backend Implementation** (`web_and_database/app.py:407-425`):
- Extracts `?id=` parameter from registration URL
- Validates Arduino ID range (1-999,999)
- Pre-fills registration form Device ID field
- Provides visual green checkmark when valid

**User Terminology:**
- User-facing: "Device ID" (non-technical)
- Backend code: `arduino_id` (technical field name)
- Rationale: Non-technical users don't need to know Arduino platform

### Real-Time Registration Validation (Commit 9416a35)

The registration form provides instant visual feedback:

**Validated Fields:**
- **Name:** 2-50 characters, letters/spaces/hyphens/apostrophes (regex: `/^[a-zA-Z\s\-']{2,50}$/`)
- **Email:** Standard email format, max 255 characters
- **Device ID:** Integer 1-999,999 (green border when valid)
- **Password:** 8-128 characters

**Visual Feedback:**
- Green border + shadow: Field valid
- Red border + shadow: Field invalid
- No styling: Field empty

### Error Handling (Commit 2f834d3)

**Duplicate Field Detection:**
Database constraint parsing provides specific error messages:

| Duplicate Field | Error Message |
|----------------|---------------|
| Email | "This email address is already registered. Please use a different email or login." |
| Username | "This username is already taken. Please choose a different username." |
| Device ID | "This Device ID is already registered to another user. Please check your Device ID." |

**Implementation:** PostgreSQL constraint name parsing from `IntegrityError.orig`

### Benefits

1. **Production Efficiency:** Generate 100 QR codes in one click
2. **Zero-Error ID Assignment:** Database-driven prevents duplicates
3. **Customer Experience:** Scan QR → form auto-filled → done! (90% friction reduction)
4. **Inventory Tracking:** Real-time statistics on ID usage
5. **Scalability:** Ready for mass production runs

### Files

```
manufacturing_id/
├── id_manager.py              # Database queries for ID management
├── qr_generator.py            # QR code generation with PIL
├── manufacturing_app.py       # Flask dashboard (port 5001)
├── requirements.txt           # Flask, qrcode, Pillow, SQLAlchemy
├── README.md                  # Complete documentation
├── templates/
│   └── dashboard.html         # Manufacturing UI
└── static/qr_codes/           # Generated QR code files
```

**Security Note:** Manufacturing dashboard is intended for internal use only (no authentication).

## Configuration Files

### API Field Mappings
**File:** `surf-lamp-processor/endpoint_configs.py`

Defines how to extract data from different API responses:
```python
FIELD_MAPPINGS = {
    "marine-api.open-meteo.com": {
        "wave_height_m": ["hourly", "wave_height", 0],
        "wave_period_s": ["hourly", "wave_period", 0],
        "wave_direction_deg": ["hourly", "wave_direction", 0]
    },
    "api.open-meteo.com": {
        "wind_speed_mps": ["hourly", "wind_speed_10m", 0],
        "wind_direction_deg": ["hourly", "wind_direction_10m", 0]
    }
}
```

### Server Discovery
**File:** `arduino/ServerDiscovery.h`

Arduino uses discovery system to find API server:
1. Tries GitHub Pages config: `https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
2. Falls back to hardcoded servers
3. Caches discovered server for 24 hours

## Error Handling and Resilience

### Arduino Resilience
- **WiFi Connection:** Auto-reconnect every 30 seconds if disconnected
- **AP Mode:** Creates setup hotspot if WiFi fails (60-second timeout)
- **Data Fetch:** Continues with cached data if server unreachable

### Background Processor
- **Database Reconnection:** Tests connection before each cycle
- **API Failures:** Continues with other endpoints if one fails
- **Partial Data:** Stores whatever data was successfully fetched
- **Rate Limit Prevention:** 10-second delay between API calls to prevent burst rate limiting (background_processor.py:516)
- **API Cache:** Caches API responses within each 20-minute cycle to avoid duplicate requests; cache resets at start of each cycle
- **Priority Processing:** Processes API endpoints in priority order, attempting backups only when primary sources fail
- **Smart Aggregation:** Combines data from multiple sources to create complete surf reports

### Web Application
- **Rate Limiting:** Prevents authentication abuse
- **Session Management:** Secure user sessions with timeout
- **Database Transactions:** Atomic operations for data consistency

## Deployment Architecture (Render)

### Production Deployment
The Surf Lamp system runs on Render cloud platform with the following architecture:

1. **Flask Web Application** (`web_and_database/app.py`)
   - Deployed as a Render Web Service
   - Handles user dashboard, authentication, and Arduino API endpoints
   - Configured with ProxyFix for Render's reverse proxy setup

2. **Background Processor** (`surf-lamp-processor/background_processor.py`)
   - Deployed as a Render Background Worker
   - Continuously fetches surf data from external APIs every 30 minutes
   - Updates database with latest surf conditions for all registered lamps

### Render Configuration
- **Web Service:** Hosts the Flask application for user interface and Arduino API
- **Background Worker:** Runs the background processor for continuous data fetching
- **Database:** Uses Render's managed PostgreSQL database
- **Environment Variables:** Database connection strings and configuration managed via Render dashboard

Both services share the same database and work together to provide real-time surf data to Arduino devices and users.

## Development and Debugging

### Unit Testing
The project includes a unit test to verify the core API failover and priority logic in a controlled environment.

- **File:** `surf-lamp-processor/test_api_priority.py`
- **Purpose:** This test simulates a scenario where a high-priority API fails and asserts that the background processor correctly fails over to the next-highest priority API. It uses mocking to avoid making real network calls or database changes.
- **To Run:** `python3 surf-lamp-processor/test_api_priority.py`

This test is crucial for ensuring the resilience of the data-fetching mechanism and can be run to prevent regressions.

### Log Locations
- **Background Processor:** `surf-lamp-processor/lamp_processor.log`
- **Web Application:** Console/stdout (configured in app.py:25-27)
- **Arduino:** Serial Monitor (115200 baud)

### Debug Endpoints
- **Manual Fetch:** `GET http://<arduino_ip>/api/fetch` - Forces immediate data fetch
- **LED Test:** `GET http://<arduino_ip>/api/led-test` - Tests all LED strips
- **Status:** `GET http://<arduino_ip>/api/status` - Arduino health check

### Key Debug Information
Arduino Serial Output includes:
```
🐛 DEBUG: Wind direction = 340°
🎨 LEDs Updated - Wind: 3, Wave: 2, Period: 5, Direction: 340°
```

## Security Considerations

### Authentication
- **Password Hashing:** bcrypt with salt (implemented in app.py:56)
- **Session Security:** Flask sessions with SECRET_KEY
- **Rate Limiting:** Login attempts limited (app.py:64-71)

### Network Security
- **HTTPS:** Arduino uses TLS for API calls (`client.setInsecure()` - production should use proper certs)
- **API Keys:** Stored securely in database, not hardcoded
- **Input Validation:** Form validation on all user inputs

## Location-to-Endpoint Mapping

### Complete Endpoint Coverage Map

| Location | Coordinates | Wave API | Wind API | Backup Wind API |
|----------|-------------|----------|----------|-----------------|
| **Tel Aviv** | 32.0853, 34.7818 | Marine-API (Open-Meteo) | Open-Meteo Forecast | - |
| **Hadera** | 32.4365, 34.9196 | **Isramar** (Local) | Open-Meteo Forecast | Open-Meteo GFS |
| **Ashdod** | 31.7939, 34.6328 | Marine-API (Open-Meteo) | Open-Meteo Forecast | - |
| **Haifa** | 32.7940, 34.9896 | Marine-API (Open-Meteo) | Open-Meteo Forecast | - |
| **Netanya** | 32.3215, 34.8532 | Marine-API (Open-Meteo) | Open-Meteo Forecast | - |
| **Nahariya** | 33.006, 35.094 | Marine-API (Open-Meteo) | Open-Meteo Forecast | - |
| **Ashkelon** | 31.6699, 34.5738 | Marine-API (Open-Meteo) | Open-Meteo Forecast | - |

### API Endpoint Details

**Wave Data Sources:**
- **Marine-API (Open-Meteo):** `marine-api.open-meteo.com/v1/marine`
- **Isramar (Local Israeli):** `isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json`

**Wind Data Sources:**
- **Open-Meteo Forecast:** `api.open-meteo.com/v1/forecast` (Primary)
- **Open-Meteo GFS:** `api.open-meteo.com/v1/gfs` (Backup for Hadera only)

### Special Configuration Notes

- **Hadera:** Only location with 3 API sources (includes GFS backup for wind)
- **Isramar:** Local Israeli marine data - higher accuracy for wave conditions
- **All wind APIs:** Include `&wind_speed_unit=ms` for correct m/s values
- **Coordinates:** Embedded in API URLs for location-specific data

### Adding New Locations

To add a new location (e.g., California, USA), follow these steps:

#### Step 1: Add Timezone Support
**File:** `web_and_database/app.py:79-90`
```python
LOCATION_TIMEZONES = {
    # ... existing locations ...
    "Los Angeles, USA": "America/Los_Angeles",     # NEW: Add timezone mapping
    "San Francisco, USA": "America/Los_Angeles",   # NEW: Pacific Time zone
}
```

**File:** `surf-lamp-processor/background_processor.py:74-83`
```python
LOCATION_TIMEZONES = {
    # ... existing locations ...
    "Los Angeles, USA": "America/Los_Angeles",     # NEW: Same mapping for processor
}
```

#### Step 2: Add to Location List
**File:** `web_and_database/app.py:125+`
```python
SURF_LOCATIONS = [
    # ... existing locations ...
    "Los Angeles, USA",        # NEW: Appears in dashboard dropdown
    "San Francisco, USA",      # NEW: Available for user selection
]
```

#### Step 3: Add API Endpoints
**File:** `web_and_database/data_base.py` (find `MULTI_SOURCE_LOCATIONS`)
```python
MULTI_SOURCE_LOCATIONS = {
    # ... existing locations ...
    "Los Angeles, USA": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=34.0522&longitude=-118.2437&hourly=wave_height,wave_direction,wave_period&wind_speed_unit=ms",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": "https://api.open-meteo.com/v1/forecast?latitude=34.0522&longitude=-118.2437&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms",
            "priority": 2,
            "type": "wind"
        }
    ]
}
```

#### Common California Coordinates:
- **Los Angeles**: `34.0522, -118.2437`
- **San Francisco**: `37.7749, -122.4194`
- **San Diego**: `32.7767, -117.1611` (already exists)
- **Monterey**: `36.6002, -121.8947`
- **Santa Barbara**: `34.4208, -119.6982`

#### Step 4: Automatic Features
After adding the location, the system automatically provides:
1. **Quiet Hours**: Sleep protection 10 PM - 6 AM in local timezone (Pacific Time for California)
2. **Dashboard Access**: Location appears in user dropdown menu
3. **API Processing**: Location-based surf data fetching with correct coordinates
4. **Threshold Alerts**: Timezone-aware blinking suppression during sleep hours

**Note**: All existing threshold logic, timezone calculations, and quiet hours functionality work immediately for new locations.

## Common Issues and Solutions

### Arduino Not Updating
1. **Check Arduino Network:** Ensure Arduino can reach the API server (check serial monitor at 115200 baud)
2. **Check Server Discovery:** Arduino logs show server discovery status and fetch attempts
3. **Check Database:** Verify lamp_id has current surf data in `current_conditions` table
4. **Check Background Processor:** Verify lamp_id is being processed in background_processor logs
5. **Manual Fetch:** Use `http://<arduino_local_ip>/api/fetch` endpoint on Arduino to force immediate update

### Wrong Location Data
1. **Check API Endpoints:** Verify `usage_lamps` table has correct coordinates
2. **Location Change:** Use dashboard to change location (triggers endpoint update)
3. **Database Consistency:** Ensure `usage_lamps` matches user's location setting

### LED Colors Wrong
1. **Check Wind Direction:** Verify value received in Arduino serial debug
2. **Check Calculations:** Wind direction ranges in `setWindDirection()` function
3. **LED Indexing:** Ensure `NUM_LEDS_CENTER - 1` points to correct LED

This documentation reflects the actual implementation as found in the codebase and should prevent future architectural misunderstandings.