# Surf Lamp System Design

## System Overview

The Surf Lamp is an IoT system that provides real-time surf condition visualization through ESP32-based LED lamps. The system integrates a web application, background data processor, PostgreSQL database, Redis rate limiting, and Arduino firmware to deliver continuous surf monitoring.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL DATA SOURCES                          │
├─────────────────────────────────────────────────────────────────────────┤
│  • OpenWeatherMap API (Wind data)                                       │
│  • Open-Meteo Marine API (Wave data)                                    │
│  • Isramar API (Wave data - priority source)                            │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            │ API Calls (per location, not per lamp)
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND PROCESSOR SERVICE                         │
│                 ~/surf-lamp-processor/                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  • background_processor.py - Main orchestrator (20-min cycle)           │
│  • endpoint_configs.py - API configuration & data standardization       │
│  • data_base.py - Database operations (SQLAlchemy)                      │
│  • arduino_transport.py - Optional push to Arduino (rarely used)        │
│                                                                          │
│  Key Features:                                                           │
│  - Location-centric processing (1 API call per location)                │
│  - Multi-source fallback (Isramar → Open-Meteo → OpenWeatherMap)        │
│  - Data standardization & unit conversion                               │
│  - Failure tracking for Arduino communication                           │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            │ Writes processed data
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        POSTGRESQL DATABASE                              │
│                          (Supabase)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  Tables:                                                                 │
│  • users - User accounts (location, thresholds, preferences)            │
│  • lamps - Lamp hardware (arduino_id, arduino_ip, user_id)              │
│  • current_conditions - Latest surf data (wave_height, wind_speed)      │
│  • daily_usage - API endpoint configurations                            │
│  • usage_lamps - Lamp-to-endpoint mappings                              │
│  • location_websites - Location-to-endpoint mappings                    │
│  • password_reset_tokens - Security tokens                              │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│    WEB APPLICATION      │   │    ESP32 SURF LAMPS     │
│  ~/web_and_database/    │   │   arduinomain_lamp.ino  │
├─────────────────────────┤   ├─────────────────────────┤
│  • app.py (Flask)       │   │  • WiFi manager         │
│  • forms.py             │   │  • HTTP client          │
│  • security_config.py   │   │  • LED controller       │
│  • data_base.py         │   │  • ServerDiscovery.h    │
│  • templates/           │   │                         │
│  • static/              │   │  Features:              │
│                         │   │  - 3 LED strips         │
│  User Features:         │   │  - Threshold alerts     │
│  - Registration/Login   │   │  - Quiet hours mode     │
│  - Dashboard            │   │  - Color themes         │
│  - Location setup       │   │  - Wind direction       │
│  - Threshold config     │   │  - 13-min polling       │
└─────────────────────────┘   └─────────────────────────┘
         │                              │
         │                              │ Pulls data via HTTP GET
         │                              └────────────────────────┐
         │                                                       │
         ▼                                                       ▼
┌─────────────────────────┐                    ┌──────────────────────────┐
│    REDIS SERVICE        │                    │   SERVER DISCOVERY       │
├─────────────────────────┤                    │   ServerDiscovery.h      │
│  User Rate Limiting:    │                    ├──────────────────────────┤
│  • Location changes     │                    │  Primary:                │
│  • Threshold updates    │                    │  • GitHub Pages          │
│  • Preference edits     │                    │  • raw.githubusercontent  │
│                         │                    │                          │
│  Protects:              │                    │  Fallback:               │
│  • API quotas           │                    │  • 3 hardcoded servers   │
│  • System stability     │                    │                          │
│                         │                    │  Cache: 24 hours         │
└─────────────────────────┘                    └──────────────────────────┘
```

---

## Data Flow

### 1. User Onboarding Flow

```
User Purchase → Web Registration → forms.py Validation → Database User Creation
                                                         ↓
                                                    Dashboard Access
                                                    (Location, Thresholds)
```

### 2. Background Data Processing Flow (Every 20 Minutes)

```
1. Fetch lamp configurations grouped by location
   └─> Query database for all lamps and their locations

2. For each unique location:
   ├─> Attempt Isramar API (priority wave source)
   ├─> Attempt Open-Meteo Marine API (wave fallback)
   ├─> Attempt OpenWeatherMap API (wind data)
   └─> Standardize data via endpoint_configs.py

3. Write to current_conditions table (per lamp_id)

4. (Optional) Push to Arduino via arduino_transport.py
```

**Key Optimization**: If 7 lamps exist across 2 locations, only **2 API calls** are made (not 7), dramatically reducing rate limiting risks.

### 3. Arduino Data Fetch Flow (Every 13 Minutes)

```
1. ServerDiscovery checks for api_server address
   ├─> Try fetch config.json from GitHub Pages
   ├─> Cache result for 24 hours
   └─> Fallback to hardcoded server list if needed

2. HTTP GET to /api/lamp-data?lamp_id=XXX

3. Parse JSON response:
   {
     "wave_height_m": 1.5,
     "wave_period_s": 8,
     "wind_speed_mps": 5.2,
     "wind_direction_deg": 180,
     "wave_threshold": 1.2,
     "wind_threshold": 10,
     "color_theme": "ocean_breeze"
   }

4. Update LED strips:
   ├─> Right strip: Wave height visualization
   ├─> Left strip: Wave period visualization
   ├─> Center strip: Wind speed + direction (top LED color-coded)
   └─> Apply threshold alerts (blinking if exceeded)
```

---

## Component Details

### Background Processor (`~/surf-lamp-processor/`)

**Files**:
- `background_processor.py` - Main orchestrator, runs every 20 minutes
- `endpoint_configs.py` - API source of truth, defines data parsers
- `data_base.py` - SQLAlchemy models and queries
- `arduino_transport.py` - Optional push mechanism (mock-able for dev)

**Design Principles**:
- **Location-centric processing**: Groups lamps by location to minimize API calls
- **Multi-source fallback**: Isramar → Open-Meteo → OpenWeatherMap
- **Data standardization**: Converts all API responses to unified format
- **Failure tracking**: Stops contacting unresponsive Arduinos after N failures

**Configuration Source**: `endpoint_configs.MULTI_SOURCE_LOCATIONS` in code (not database)

**Why Code-Driven Config?**:
- Immune to database corruption
- Version-controlled alongside logic
- Easier to review and debug

### Web Application (`~/web_and_database/`)

**Backend** (Python/Flask):
- `app.py` - Main Flask application, routing, session management
- `forms.py` - WTForms validation for user inputs
- `data_base.py` - Database operations (shared with background processor)
- `security_config.py` - Authentication, CSRF protection

**Frontend**:
- `templates/` - Jinja2 HTML templates
- `static/` - CSS, JS, images, PWA manifest

**User Features**:
- Registration with location and threshold setup
- Dashboard showing real-time surf conditions
- Configuration updates (rate-limited by Redis)
- Mobile-friendly responsive design

### Arduino Firmware (`arduinomain_lamp.ino`)

**Hardware**: ESP32 microcontroller with 3 addressable LED strips

**Capabilities**:
- WiFi manager with captive portal for setup
- HTTP server for status monitoring and testing
- Periodic data polling (13-minute intervals)
- LED strip control with multiple visualization modes

**LED Strip Assignments**:
- **Right strip**: Wave height (bar graph)
- **Left strip**: Wave period (bar graph)
- **Center strip**: Wind speed (bar graph) + direction (top LED color)

**Special Modes**:
- **Threshold alerts**: Blinking LEDs when conditions exceed user limits
- **Quiet hours**: Dim single LED per strip during nighttime
- **Color themes**: Multiple palettes selectable via API

**Wind Direction Color Coding**:
```
North (0°): Green
Northeast (45°): Yellow-Green
East (90°): Yellow
Southeast (135°): Orange
South (180°): Red
Southwest (225°): Purple
West (270°): Blue
Northwest (315°): Cyan
```

### Server Discovery (`ServerDiscovery.h`)

**Purpose**: Dynamic API server resolution without firmware updates

**Discovery Mechanism**:
1. Fetch `config.json` from GitHub Pages or raw.githubusercontent.com
2. Parse JSON to extract current `api_server` address
3. Cache result for 24 hours

**Fallback Strategy**:
- If discovery fails → use hardcoded server list
- Retries with exponential backoff
- Ensures lamp continues functioning during network issues

**Why This Approach?**:
- Server infrastructure can change without reflashing devices
- High availability through multiple static hosting sources
- Minimal network overhead (24-hour cache)

---

## Database Schema

### Core Tables

**users**
```sql
user_id INT PRIMARY KEY
username VARCHAR
email VARCHAR UNIQUE
location VARCHAR  -- e.g., "Herzliya, Israel"
theme VARCHAR
sport_type VARCHAR
wave_threshold_m FLOAT
wind_threshold_knots FLOAT
```

**lamps**
```sql
lamp_id INT PRIMARY KEY
user_id INT REFERENCES users
arduino_id VARCHAR UNIQUE
arduino_ip VARCHAR
```

**current_conditions**
```sql
lamp_id INT PRIMARY KEY REFERENCES lamps
wave_height_m FLOAT
wave_period_s FLOAT
wind_speed_mps FLOAT
wind_direction_deg INT
updated_at TIMESTAMP
```

**location_websites** (Location-to-Endpoint Mapping)
```sql
location VARCHAR
usage_id INT REFERENCES daily_usage
```

**daily_usage** (API Endpoint Configurations)
```sql
usage_id INT PRIMARY KEY
website_url VARCHAR  -- e.g., "https://api.openweathermap.org/..."
```

**usage_lamps** (Lamp-to-Endpoint Mapping)
```sql
usage_id INT REFERENCES daily_usage
lamp_id INT REFERENCES lamps
api_key VARCHAR
http_endpoint VARCHAR
```

---

## Key Design Decisions

### 1. Location-Centric Processing

**Problem**: Processing each lamp individually caused rate limiting (21 API calls for 7 lamps).

**Solution**: Group lamps by location, fetch data once per location.

**Impact**: Reduced API calls from 21 to 6 for 7 lamps across 2 locations (71% reduction).

**Implementation**: `get_location_based_configs()` in `background_processor.py`

### 2. Pull-Based Arduino Architecture

**Decision**: Arduinos poll the server instead of server pushing to Arduinos.

**Rationale**:
- No need to track Arduino IP addresses (can be dynamic)
- Resilient to network interruptions
- Arduinos control their own update frequency
- Simplifies backend (stateless HTTP server)

**Trade-off**: Slight delay in data propagation (up to 13 minutes).

### 3. Multi-Source API Fallback

**Problem**: Single API sources suffer from rate limiting and downtime.

**Solution**: Priority-based cascade:
1. **Isramar** (primary wave data)
2. **Open-Meteo Marine API** (wave fallback)
3. **OpenWeatherMap** (wind data)

**Configuration**: `endpoint_configs.MULTI_SOURCE_LOCATIONS`

**Why Not Database?**: Code-driven config prevents database corruption from breaking critical logic.

### 4. Redis Rate Limiting

**Purpose**: Prevent users from making rapid changes that trigger excessive API calls.

**Rate Limited Actions**:
- Location changes
- Threshold updates
- Preference modifications

**Why Needed**: Without rate limiting, a user could switch locations repeatedly, exhausting API quotas.

### 5. Nighttime LED Behavior

**Requirement**: During quiet hours, override normal threshold logic.

**Behavior**:
- Only top LED of each strip illuminates
- Wave/wind thresholds do not apply
- Provides ambient lighting without full surf indication

**Implementation**: Time-based logic in Arduino firmware.

---

## API Endpoints

### Backend API (Flask)

**Public Endpoints**:
- `GET /api/lamp-data?lamp_id=<id>` - Fetch current conditions for a lamp
- `POST /api/register` - User registration
- `POST /api/login` - User authentication
- `POST /api/update-location` - Change user location (rate-limited)
- `POST /api/update-thresholds` - Modify wave/wind thresholds (rate-limited)

**Arduino Endpoints** (Optional Push):
- `POST /api/arduino/update` - Receive pushed data from backend

### Arduino Endpoints (ESP32 Web Server)

**Diagnostic**:
- `GET /api/status` - Lamp health check (uptime, WiFi, last update)
- `GET /api/test` - Manual data fetch trigger
- `GET /api/led-test` - LED strip functionality test

**Data Reception**:
- `POST /api/update` - Receive pushed data from backend (rarely used)

---

## Visualization & Documentation

### Interactive System Visualizer
**Location**: `~/Git_Surf_Lamp_Agent/surf-lamp-visualizer/`
**URL**: https://surf-lamp-visualizer.onrender.com

A Progressive Web App (PWA) providing interactive D3.js visualization of the entire system architecture.

**Features**:
- **Interactive force-directed graph** - Nodes represent system components, edges show data flow
- **Click-to-explore** - Click any module for detailed description
- **Full manual pages** - Technical documentation for each component (markdown-based)
- **PWA installable** - Add to phone home screen for native app experience
- **Real-time stats** - Display system metrics and performance characteristics
- **Color-coded modules** - Backend (green), Storage (blue), Hardware (orange), APIs (purple), Tools (red)

**Technology Stack**:
- Flask web server with CORS support
- D3.js v7 for force simulation and graph rendering
- markdown2 for rendering technical documentation
- Service Worker for offline PWA capabilities
- Responsive design for mobile and desktop

**Manual Pages** (`/manpages/*.md`):
Each system component has dedicated technical documentation covering:
- Architecture details and implementation
- API endpoints and database schemas
- Configuration options and environment variables
- Troubleshooting guides and performance characteristics
- Code examples and integration patterns

**User Flow**:
1. Browse interactive graph visualization
2. Click module → View summary description
3. Click "View Full Manual" → Deep dive into technical details
4. Navigate back via breadcrumb or install as PWA for quick access

---

## Deployment Architecture

### Production Environment (Render)

**Services**:
1. **Web Application** - Flask app serving user dashboard
2. **Background Processor** - Scheduled service (20-min intervals)
3. **System Visualizer** - Interactive D3.js architecture documentation (PWA)
3. **PostgreSQL Database** - Supabase hosted
4. **Redis Service** - Rate limiting backend

**Monitoring Tools**:
- Render MCP Server (FastMCP-based)
- Log filtering and error detection
- Deployment history tracking
- Performance metrics (CPU, memory, HTTP)

### Development Environment

**Local Setup**:
- Virtual environment with `requirements.txt`
- Mock Arduino transport for testing
- SQLite database for local development
- Environment variables in `.env` file

**Testing**:
- `test_endpoints.sh` - Backend endpoint validation
- `test_background_processor.py` - Pytest unit tests

---

## Security Considerations

### Authentication
- Password hashing (bcrypt/Werkzeug)
- Session management via Flask-Login
- CSRF protection on all forms

### API Security
- Rate limiting via Redis (prevents abuse)
- API keys stored securely (environment variables)
- Input validation via `forms.py` (WTForms)

### Arduino Security
- HTTPS for API communication
- WiFi credentials stored in NVS (non-volatile storage)
- Captive portal for secure initial setup

---

## Failure Modes & Recovery

### API Rate Limiting
**Detection**: HTTP 429 responses
**Recovery**:
- Switch to fallback API sources
- Exponential backoff with circuit breaker
- Prioritize location-based processing

### Database Connection Loss
**Detection**: SQLAlchemy connection errors
**Recovery**:
- Retry with exponential backoff
- Log errors to Render logs
- Arduino continues using cached data

### Arduino Offline
**Detection**: HTTP timeouts or failed requests
**Recovery**:
- Failure tracking in background processor
- Stop contacting after N consecutive failures
- Resume attempts after cooldown period

### Server Discovery Failure
**Detection**: GitHub config fetch fails
**Recovery**:
- Use hardcoded fallback server list
- Retry with exponential backoff
- Log discovery failures for debugging

---

## Performance Characteristics

### Background Processor
- **Cycle Time**: 20 minutes
- **API Calls per Cycle**: ~2-6 (depending on unique locations)
- **Processing Time**: <5 seconds per location
- **Database Writes**: 1 per lamp per cycle

### Arduino Polling
- **Polling Interval**: 13 minutes
- **HTTP Request Time**: <1 second
- **LED Update Latency**: <500ms
- **WiFi Reconnect**: Automatic with exponential backoff

### Web Application
- **Response Time**: <200ms (database-backed)
- **Concurrent Users**: 100+ (typical load)
- **Static Asset Caching**: Browser-cached with cache busting

---

## Future Enhancements

### Potential Improvements
1. **Real-time WebSocket updates** - Push data to dashboard without polling
2. **Mobile app** - Native iOS/Android apps
3. **Historical data tracking** - Store surf condition trends
4. **Predictive alerts** - Notify users when ideal conditions approach
5. **Multi-location support** - Users can monitor multiple spots simultaneously
6. **Advanced LED animations** - More sophisticated visualization modes
7. **Solar/battery power** - Offline lamp operation

### Scalability Considerations
- **Database sharding** - Partition users/lamps by region
- **API caching layer** - Redis cache for frequently accessed data
- **CDN for static assets** - Reduce web server load
- **Horizontal scaling** - Multiple background processor instances

---

## Lessons Learned (From CLAUDE.md)

### Core Principles
1. **90% analysis, 10% implementation** - Understand before acting
2. **Fix at the earliest point in data flow** - Address root causes
3. **Core fixes, not shallow patches** - Architectural solutions > quick fixes
4. **Location-centric > Lamp-centric** - Reduce API calls through grouping
5. **Code-driven config > Database-driven** - Immunity to corruption

### Investigation Methodologies
- Git history as debugging tool (traced back 120 commits)
- Facts-based analysis documentation (`FACTS_*.md`)
- Production log pattern analysis
- Database verification with Supabase tools

### User Feedback Integration
- Listen to corrections without defensiveness
- Strong emotional reactions signal proximity to core issues
- Respect domain expertise over imposed solutions

---

## Maintenance Guidelines

### Regular Tasks
- Monitor Render logs for rate limiting patterns
- Review API quota usage monthly
- Update Arduino firmware for security patches
- Backup database weekly (automated via Supabase)

### Debugging Checklist
1. Check Render logs for errors (`mcp__render__render_recent_errors`)
2. Verify API source availability (Isramar, Open-Meteo, OpenWeatherMap)
3. Review database `current_conditions` table for stale data
4. Test Arduino connectivity via `/api/status` endpoint
5. Validate Redis rate limiting configuration

### Code Review Priorities
- Import path management (avoid hardcoded local paths)
- API error handling and retry logic
- Database transaction atomicity
- Arduino timeout and reconnection behavior

---

## Contact & Support

**Repository**: `~/Git_Surf_Lamp_Agent/`
**Documentation**: `CLAUDE.md`, `system_design.md`, `RENDER_DEPLOYMENT.md`
**Issue Tracking**: Git commit history and `FACTS_*.md` files

---

*Last Updated: 2025-09-29*
*Architecture Version: 2.0 (Location-Centric Processing)*