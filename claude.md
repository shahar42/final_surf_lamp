# 🌊 Surf Lamp Background Processor

## Overview
Background service that fetches surf data from external APIs and sends it to Arduino devices via HTTP POST every 30 minutes.

## Architecture
```
PostgreSQL Database → Background Processor → Arduino Devices
     ↑                        ↑                    ↑
 Lamp configs             API calls           HTTP POST
 API endpoints           Surf data           LED updates
```

## Files

### `background_processor.py`
**Main service that runs continuously.**

**Core Functions:**
- `get_unique_api_configs()` - Gets API endpoints from `usage_lamps` table
- `fetch_surf_data()` - Calls external surf APIs, auto-parses JSON responses
- `send_to_arduino()` - HTTP POST surf data to Arduino IP addresses
- `process_all_lamps()` - Main loop that orchestrates everything

**Key Features:**
- Auto-detects surf data fields (`wave_height`, `wind_speed`, etc.)
- Handles both authenticated and public APIs
- Graceful error handling per device
- Comprehensive logging

### `test_background_processor.py`
**Test runner for local development.**

**What it tests:**
- Database connectivity
- API configuration retrieval
- Complete processing loop
- Error handling

**Usage:** `python test_background_processor.py`

### `requirements.txt`
**Python dependencies:**
- `sqlalchemy` - Database connectivity
- `psycopg2-binary` - PostgreSQL driver
- `requests` - HTTP calls to APIs and Arduinos
- `schedule` - 30-minute intervals

## Database Schema Required

```sql
-- Core tables (must exist):
lamps (lamp_id, arduino_ip, last_updated)
usage_lamps (usage_id, lamp_id, api_key, http_endpoint)  
daily_usage (usage_id, website_url)
users (user_id, location, preferred_output)
```

## Data Flow

### Every 30 Minutes:
1. **Query database** for unique API endpoints
2. **Fetch surf data** from each API once
3. **Parse JSON** using auto-detection
4. **Send HTTP POST** to all Arduino IPs that need this data
5. **Update timestamps** in database

### Optimizations:
- **Deduplication**: One API call serves multiple Arduinos
- **Fault tolerance**: Individual failures don't stop processing
- **Auto-parsing**: Works with any API JSON structure

## Environment Variables
```bash
DATABASE_URL="postgresql://user:pass@host:port/db"
TEST_MODE="true"  # Optional: run once and exit
```

## Arduino Endpoint Expected
```http
POST /api/update
Content-Type: application/json

{
  "wave_height_m": 1.8,
  "wave_period_s": 9.2,
  "wind_speed_mps": 8.5,
  "wind_direction_deg": 225,
  "location": "San Diego",
  "timestamp": 1704067200
}

Response: {"status": "ok"}
```

## Deployment
- **Platform**: Render Background Worker
- **Build**: `pip install -r requirements.txt`
- **Start**: `python background_processor.py`
- **Scaling**: Single instance (database prevents conflicts)

## Error Handling
- **API failures**: Logged, other APIs continue
- **Arduino unreachable**: Logged, other devices continue  
- **Database errors**: Logged, retried next cycle
- **Partial success**: System reports success/failure counts

## Logging Output
```
🚀 ======= STARTING LAMP PROCESSING CYCLE =======
📡 Getting unique API configurations...
✅ Found 2 unique API configurations
🌊 Fetching surf data from: https://api.weather.gov/...
✅ Surf data received: {"wave_height_m": 2.1, ...}
📡 Sending data to Arduino at 192.168.1.100...
✅ Successfully sent data to Arduino
⏰ Updating timestamp for lamp 12345
🎉 ======= CYCLE COMPLETED ======= (4.2 seconds)
```
## query sql
SELECT 
    lw.location,
    du.website_url as endpoint,
    ul.api_key,
    ul.lamp_id,
    l.arduino_ip
FROM location_websites lw
JOIN daily_usage du ON lw.usage_id = du.usage_id  
JOIN usage_lamps ul ON du.usage_id = ul.usage_id
JOIN lamps l ON ul.lamp_id = l.lamp_id
JOIN users u ON l.user_id = u.user_id
WHERE lw.location = 'Bondi Beach, Australia';
this query should get all the information needed inorder to send surf data to the arduino
## API Configuration Examples
```sql
-- Public API (no auth)
INSERT INTO usage_lamps VALUES (1, 12345, NULL, 'https://api.weather.gov/stations/12345/observations/latest');

-- Authenticated API  
INSERT INTO usage_lamps VALUES (2, 12345, 'api-key', 'https://api.weatherapi.com/v1/marine.json?key=api-key&q=sandiego');
```
