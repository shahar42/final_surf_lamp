# Surfboard Lamp Backend - Technical Architecture

## System Overview

The Surfboard Lamp backend is a Flask-based system designed around a **Database-First, Push-Based Architecture** that coordinates surf data delivery to IoT devices.

```
External APIs → Background Processor → Database → Arduino Devices
     ↑                ↑                   ↑           ↑
  Surfline         Agent Tools        PostgreSQL   HTTP POST
  WeatherAPI       Scheduler          SQLAlchemy   LED Display
```

## Core Architecture Principles

### 1. Database-First Design
- **Schema Drives Logic:** Database relationships define how tools and APIs interact
- **Contract-Based:** Tools implement interfaces derived from database structure
- **Normalized Design:** 5 tables with clear foreign key relationships

### 2. Push-Based Communication  
- **No Arduino Polling:** Backend pushes data to Arduino devices via HTTP POST
- **Event-Driven:** Updates triggered by background processor, not client requests
- **Reduced Network Load:** Arduino devices are passive receivers

### 3. Agent Tools Pattern
- **Functional Decomposition:** 5 specific tools handle distinct operations
- **Dependency Flow:** Tools work together in a defined sequence
- **Testable Units:** Each tool can be tested and mocked independently

## Database Architecture

### Entity Relationships

```
users (1) ←→ (N) lamps ←→ (N) usage_lamps ←→ (N) daily_usage
                                    ↓
                              location_websites (1) ←→ (1) daily_usage
```

### Table Purposes

**users**: User account management and authentication
- Stores user credentials, preferences, location information
- Links to lamps via foreign key relationship

**lamps**: IoT device registry and network configuration  
- Maps physical Arduino devices to users
- Stores Arduino IP addresses for HTTP POST communication
- Tracks last update timestamps for monitoring

**daily_usage**: External API endpoint registry
- Centralized catalog of available surf data APIs
- Tracks API performance and update frequencies
- Enables dynamic API provider management

**location_websites**: Geographic location to API mapping
- Links user locations to appropriate surf data sources
- Enables location-based API selection
- Supports regional API optimization

**usage_lamps**: Lamp-specific API configuration
- Many-to-many relationship between lamps and APIs
- Stores lamp-specific API keys and endpoints
- Enables per-device API customization

### Index Strategy

**Performance Indexes:**
- `users.email` (UNIQUE) - Authentication lookups
- `lamps.arduino_id` (UNIQUE) - Device identification
- `lamps.user_id` - User lamp queries
- `usage_lamps.lamp_id` - Lamp configuration queries
- `daily_usage.website_url` (UNIQUE) - API endpoint lookups

## Agent Tools Architecture

### Tool Dependencies and Flow

```
get_all_lamp_ids() 
    ↓
get_lamp_details(lamp_id)
    ↓
fetch_website_data(api_key, endpoint) ← (parallel calls)
    ↓
send_to_arduino(arduino_id, data, format)
    ↓
update_lamp_timestamp(lamp_id)
```

### Tool Specifications

**1. get_all_lamp_ids() → List[int]**
```sql
SELECT lamp_id FROM lamps WHERE arduino_ip IS NOT NULL
```
- Returns active lamps with network configuration
- Filters out unregistered or misconfigured devices

**2. get_lamp_details(lamp_id: int) → dict**
```sql
SELECT l.arduino_id, l.arduino_ip, du.website_url, ul.api_key, ul.http_endpoint
FROM lamps l 
JOIN usage_lamps ul ON l.lamp_id = ul.lamp_id
JOIN daily_usage du ON ul.usage_id = du.usage_id
WHERE l.lamp_id = ?
```
- Complex join query across 3 tables
- Returns all API configurations for a specific lamp
- Includes network information for HTTP POST

**3. fetch_website_data(api_key: str, endpoint: str) → dict**
```python
response = requests.get(endpoint, headers={'Authorization': f'Bearer {api_key}'})
return standardize_surf_data(response.json())
```
- HTTP client for external surf APIs
- Standardizes response format across different providers
- Handles API rate limiting and error responses

**4. send_to_arduino(arduino_id: int, data: dict, output_format: str) → bool**
```python
arduino_ip = get_arduino_ip(arduino_id)
formatted_data = format_for_arduino(data, output_format)
response = requests.post(f'http://{arduino_ip}/api/update', json=formatted_data)
return response.status_code == 200
```
- HTTP POST to Arduino device's local IP
- Data formatting based on user preferences
- Error handling for network failures

**5. update_lamp_timestamp(lamp_id: int) → bool**
```sql
UPDATE lamps SET last_updated = CURRENT_TIMESTAMP WHERE lamp_id = ?
```
- Tracks successful processing completion
- Enables monitoring and debugging
- Supports status dashboard features

## Flask Application Architecture

### Route Organization

**Core Routes:**
- `/api/lamp/config` - Arduino registration and configuration
- `/api/register` - User and lamp registration
- `/health` - System health monitoring

**Route Responsibilities:**
- **Input Validation:** Pydantic models for request validation
- **Business Logic Delegation:** Calls to agent tools
- **Response Formatting:** Standard JSON response patterns
- **Error Handling:** Consistent error response format

### Request/Response Patterns

**Arduino Configuration Request:**
```http
GET /api/lamp/config?id=12345
```

**Response:**
```json
{
  "registered": true,
  "lamp_id": 12345,
  "update_interval": 30,
  "status": "active",
  "error": null
}
```

**User Registration Request:**
```http
POST /api/register
Content-Type: application/json

{
  "username": "surfer123",
  "email": "user@example.com", 
  "password": "securepass",
  "location": "San Diego",
  "lamp_id": 12345,
  "arduino_id": 67890,
  "arduino_ip": "192.168.1.100"
}
```

## Background Processing Architecture

### Scheduler Design

**Processing Loop:**
```python
def process_all_lamps():
    lamp_ids = get_all_lamp_ids()
    for lamp_id in lamp_ids:
        try:
            process_single_lamp(lamp_id)
        except Exception as e:
            log_lamp_error(lamp_id, e)
            continue
```

**Error Isolation:** Individual lamp failures don't stop global processing

**Monitoring:** Each step logged with structured data for debugging

### Concurrency Strategy

**Sequential Processing:** Simple, reliable, debuggable
- Process lamps one at a time
- Avoid API rate limiting issues  
- Easy error tracking and recovery

**Future Enhancement:** Parallel processing with worker pools
- Async processing for improved performance
- Configurable concurrency limits
- Advanced error handling patterns

## Arduino Communication Protocol

### HTTP POST Specification

**Endpoint:** `POST http://{arduino_ip}/api/update`

**Headers:**
```http
Content-Type: application/json
User-Agent: SurfboardLamp-Backend/1.0
```

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

**Arduino Response:**
```json
{
  "status": "ok",
  "received_at": 1704067205,
  "arduino_id": 67890
}
```

### Error Handling

**Network Errors:**
- Connection timeouts (30 second limit)
- DNS resolution failures
- HTTP 5xx responses

**Arduino Errors:**
- HTTP 4xx responses (malformed data)
- JSON parsing errors
- Device offline/unreachable

**Recovery Strategy:**
- Log error with lamp_id and timestamp
- Continue processing other lamps
- Retry on next scheduled run

## External API Integration

### Supported Providers

**Surfline API:**
- Professional surf forecasting data
- Real-time conditions and forecasts
- Rate limit: 1000 requests/day
- Authentication: API key in headers

**WeatherAPI:**
- Marine weather conditions
- Wave height and wind data
- Rate limit: 100,000 requests/month
- Authentication: API key parameter

### Data Standardization

**Raw API Response → Standardized Format:**
```python
def standardize_surf_data(raw_response, provider):
    return {
        "wave_height_m": extract_wave_height(raw_response, provider),
        "wave_period_s": extract_wave_period(raw_response, provider), 
        "wind_speed_mps": extract_wind_speed(raw_response, provider),
        "wind_deg": extract_wind_direction(raw_response, provider),
        "location": extract_location(raw_response, provider),
        "timestamp": int(time.time())
    }
```

## Configuration Management

### Environment-Based Configuration

**Development:**
```python
FLASK_ENV=development
DATABASE_URL=postgresql://localhost/surfboard_lamp_dev
LOG_LEVEL=DEBUG
```

**Production:**
```python
FLASK_ENV=production  
DATABASE_URL=postgresql://prod-server/surfboard_lamp
LOG_LEVEL=INFO
```

### Security Configuration

**Password Hashing:** bcrypt with configurable rounds
**API Key Storage:** Environment variables, never in code
**Database Security:** Connection pooling, prepared statements

## Monitoring and Observability

### Logging Strategy

**Structured Logging:**
```python
logger.info("Lamp processing completed", 
           lamp_id=12345, 
           arduino_ip="192.168.1.100",
           api_calls=3,
           duration_ms=1250,
           status="success")
```

**Log Levels:**
- **DEBUG:** Detailed execution flow
- **INFO:** Normal operations and status
- **WARNING:** Recoverable errors and retries
- **ERROR:** Failed operations requiring attention

### Health Monitoring

**System Health Metrics:**
- Database connection status
- API response times
- Arduino communication success rates
- Background processor status

**Performance Metrics:**
- Lamp processing duration
- API call latency
- Database query performance
- Memory and CPU usage

## Security Architecture

### Authentication & Authorization

**User Authentication:** bcrypt password hashing
**API Access:** No public API keys, all internal
**Arduino Communication:** Local network only (no internet exposure)

### Data Protection

**Database Security:**
- Prepared statements (SQLAlchemy ORM)
- Connection pooling with limits
- No sensitive data in logs

**Network Security:**
- Arduino communication on local network
- HTTPS for external API calls
- Input validation on all endpoints

## Deployment Architecture

### Single-Server Deployment

**Components:**
- Flask application (wsgi server)
- PostgreSQL database
- Background processor (cron job)
- Nginx reverse proxy (optional)

**File Structure:**
```
/opt/surfboard-lamp/
├── app.py                 # Flask application
├── background/            # Background processing
├── tools/                 # Agent tools
├── database/              # Database models
├── config.py              # Configuration
└── logs/                  # Application logs
```

### Scaling Considerations

**Database:** PostgreSQL with connection pooling
**Background Processing:** Multiple worker processes
**Arduino Communication:** Parallel HTTP requests
**Monitoring:** Structured logs for external aggregation

## Development Guidelines

### Code Organization

**Flask App:** Route definitions, request/response handling
**Agent Tools:** Database operations, external API calls
**Background Processing:** Scheduled tasks, batch operations
**Configuration:** Environment variables, logging setup

### Testing Strategy

**Unit Tests:** Individual agent tools and Flask routes
**Integration Tests:** Database operations and API calls
**End-to-End Tests:** Complete lamp processing workflow
**Mock Testing:** External API responses and Arduino communication

### Error Handling Standards

**Database Errors:** Log and return 500 status
**API Errors:** Log, retry logic, graceful degradation
**Arduino Errors:** Log and continue processing other lamps
**Validation Errors:** Return 400 status with details
