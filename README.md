# Surfboard Lamp Flask Backend

A Flask-based backend system that fetches surf condition data from external APIs and pushes it to Arduino-based IoT lamp devices via HTTP POST requests.

## Overview

The Surfboard Lamp project creates ambient IoT devices that display real-time surf conditions through LED visualizations. This backend coordinates data retrieval from surf APIs and pushes formatted data directly to Arduino devices on the local network.

## Architecture

**Communication Flow:**
1. Background processor fetches surf data from external APIs (Surfline, WeatherAPI)
2. Backend **pushes** formatted data to Arduino devices via HTTP POST
3. Arduino devices display surf conditions via LED patterns
4. Users can register lamps and check status via web interface

**Technology Stack:**
- **Framework:** Flask (synchronous)
- **Database:** PostgreSQL with SQLAlchemy
- **Background Processing:** Scheduled Python jobs
- **Arduino Communication:** HTTP POST to local IP addresses
- **External APIs:** Surfline, WeatherAPI for surf conditions

## Database Schema

### Core Tables

**users** - User account management
- `user_id` (PK, AUTO_INCREMENT)
- `username` (VARCHAR(255), UNIQUE)
- `password_hash` (TEXT)
- `email` (VARCHAR(255), UNIQUE)
- `location` (VARCHAR(255))
- `theme` (VARCHAR(50))
- `preferred_output` (VARCHAR(50))

**lamps** - IoT device registry
- `lamp_id` (PK)
- `user_id` (FK → users)
- `arduino_id` (INTEGER, UNIQUE)
- `arduino_ip` (VARCHAR(15)) - Local IP for HTTP POST
- `last_updated` (TIMESTAMP)

**daily_usage** - External API endpoints
- `usage_id` (PK, AUTO_INCREMENT)
- `website_url` (VARCHAR(255), UNIQUE)
- `last_updated` (TIMESTAMP)

**location_websites** - Location to API mapping
- `location` (VARCHAR(255), PK)
- `usage_id` (FK → daily_usage, UNIQUE)

**usage_lamps** - Lamp to API configuration
- `usage_id` (FK → daily_usage)
- `lamp_id` (FK → lamps)
- `api_key` (TEXT)
- `http_endpoint` (TEXT)
- Composite PK: (usage_id, lamp_id)

## API Endpoints

### Arduino Configuration
**GET /api/lamp/config?id={lamp_id}**
- Returns lamp registration status and configuration
- Response: `{registered: bool, lamp_id: int, update_interval: int, status: str, error: str}`

### User Management
**POST /api/register**
- Register new user and lamp
- Body: `{username, email, password, location, lamp_id, arduino_id, arduino_ip}`

### Health Check
**GET /health**
- System health status
- Response: `{status: "ok"}`

## Agent Tools Workflow

The system uses 5 agent tools that work together in a processing loop:

1. **get_all_lamp_ids()** → `List[int]`
   - Query all active lamp IDs from database

2. **get_lamp_details(lamp_id)** → `dict`
   - Get Arduino IP and associated websites for a lamp
   - Returns: `{arduino_id: int, arduino_ip: str, websites: [...]}`

3. **fetch_website_data(api_key, endpoint)** → `dict` 
   - Fetch current surf conditions from external API
   - Returns: `{wave_height_m: float, wave_period_s: float, wind_speed_mps: float, wind_deg: int, location: str, timestamp: int}`

4. **send_to_arduino(arduino_id, data, output_format)** → `bool`
   - HTTP POST surf data to Arduino's local IP
   - POST to: `http://{arduino_ip}/api/update`
   - Payload: Formatted surf condition JSON

5. **update_lamp_timestamp(lamp_id)** → `bool`
   - Update last_updated timestamp for processed lamp

## Background Processing

The background processor runs on a scheduled interval (configurable, default 30 minutes):

```python
# Processing loop
lamp_ids = get_all_lamp_ids()
for lamp_id in lamp_ids:
    details = get_lamp_details(lamp_id)
    for website in details['websites']:
        surf_data = fetch_website_data(website['api_key'], website['endpoint'])
        send_to_arduino(details['arduino_id'], surf_data, user_format)
    update_lamp_timestamp(lamp_id)
```

## Arduino Communication Protocol

**Push-Based Architecture:** Backend pushes data to Arduino devices (not polling)

**HTTP POST Endpoint:** `http://{arduino_ip}/api/update`

**Payload Format:**
```json
{
  "wave_height_m": 1.5,
  "wave_period_s": 8.0,
  "wind_speed_mps": 12.0,
  "wind_deg": 180,
  "location": "San Diego",
  "timestamp": 1704067200
}
```

**Arduino Response:** `{status: "ok"}` or `{error: "message"}`

## Setup Instructions

### 1. Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Create PostgreSQL database
createdb surfboard_lamp

# Setup tables and seed data
python setup_database.py
```

### 3. Environment Configuration
```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your database credentials and API keys
```

### 4. Run Application
```bash
# Start Flask app
python app.py

# Run background processor (separate terminal)
python background/scheduler.py
```

## Environment Variables

```bash
DATABASE_URL=postgresql://user:password@localhost/surfboard_lamp
SURFLINE_API_KEY=your_surfline_key_here
WEATHER_API_KEY=your_weather_key_here
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development
LOG_LEVEL=INFO
LOG_FILE=surfboard_lamp.log
```

## Development Workflow

### Adding New Locations
1. Add location to `location_websites` table
2. Map to appropriate API endpoint in `daily_usage`
3. Configure lamp in `usage_lamps` with API keys

### Adding New API Providers
1. Add endpoint to `daily_usage` table
2. Update `fetch_website_data()` function for new response format
3. Map locations to new provider in `usage_lamps`

### Testing Arduino Communication
```bash
# Test POST to Arduino
curl -X POST http://192.168.1.100/api/update \
  -H "Content-Type: application/json" \
  -d '{"wave_height_m": 1.5, "wind_speed_mps": 10.0}'
```

## Logging

The system uses structured logging:
- **Console:** Development debugging
- **File:** Production logging to `surfboard_lamp.log`
- **Levels:** INFO (default), DEBUG, WARNING, ERROR

## Architecture Benefits

✅ **Simple & Reliable:** Flask synchronous patterns, no complex async coordination  
✅ **Database-First:** Schema drives tool design, ensuring consistency  
✅ **Push-Based:** Arduino doesn't need to poll, reduces network overhead  
✅ **Modular:** Agent tools can be tested and modified independently  
✅ **Extensible:** Easy to add new API providers and locations  

## Future Enhancements

- Web dashboard for lamp management
- Real-time status monitoring  
- Multiple surf forecast providers
- Arduino OTA firmware updates
- Mobile app integration
