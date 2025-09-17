# Surf Lamp Agent 🌊💡

A complete IoT surf monitoring system that transforms real-time surf conditions into beautiful LED visualizations. The system fetches marine weather data, processes it through a web application, and displays wave height, period, wind speed, and direction on an ESP32-powered LED device.

## 🏗️ Project Architecture

### Core Directories

#### 📱 **web_and_database/**
*The heart of the system - Flask web application with PostgreSQL database*

Contains the main web application (`app.py`) that serves a user dashboard for surf lamp management. Features secure user authentication with bcrypt password hashing, user registration with lamp configuration, real-time surf data visualization, and preference management. The database schema (`data_base.py`) includes 7 tables managing users, lamps, surf conditions, API sources, and security tokens. Supports 7 Israeli surf locations with multi-source API integration and priority-based fallback systems. Includes comprehensive HTML templates for login, registration, dashboard, and password reset functionality. Built with Flask 2.3.3, SQLAlchemy 2.0.21, and Redis-backed rate limiting for security.

#### ⚙️ **surf-lamp-processor/**
*Background data processing and Arduino integration layer*

Houses the background processor (`background_processor.py`) that continuously fetches surf data from marine weather APIs and updates the database. Includes Arduino integration code (`fixed_surf_lamp.ino`) for ESP32 devices with WiFi configuration, server discovery, LED control, and HTTP endpoints. The Arduino payload documentation (`arduino_payload_documentation.md`) details the JSON data format sent to devices. Contains transport layer (`arduino_transport.py`) for communicating with physical devices, endpoint configuration management (`endpoint_configs.py`), and comprehensive testing utilities. Features automatic server discovery using GitHub-hosted configuration files and supports both push and pull data synchronization models.

#### 🔍 **api_TESTING/**
*Marine weather API research and testing utilities*

Contains scripts for discovering and testing surf condition APIs across California coastal locations. The main discovery script (`find_cali_points.py`) systematically tests marine weather endpoints and maintains a database of successful API sources. Includes data visualization tools (`display_surf_conditions.py`) for validating API responses and condition display logic. Maintains logs of API discovery attempts and successful endpoint configurations. Contains JSON databases of verified working APIs and their geographical coverage areas. Used for expanding the system to new surf locations and validating data source reliability.

#### 🔧 **arduino/**
*Arduino-specific code and hardware documentation*

Stores the server discovery header file (`ServerDiscovery.h`) that enables ESP32 devices to automatically find the best API server using GitHub-hosted configuration. Contains important hardware setup instructions (`IMPORTANT.txt`) and Arduino-specific documentation (`README.md`). The ServerDiscovery class implements fallback mechanisms, discovery URL management, JSON parsing for server configuration, and automatic failover handling. Designed to work with GitHub Pages for reliable, free server discovery infrastructure without requiring dedicated discovery servers.

#### ⚙️ **discovery-config/**
*Server discovery configuration files*

Contains the central configuration file (`config.json`) that defines which API servers Arduino devices should use. This JSON file is published to GitHub Pages and consumed by Arduino devices through the ServerDiscovery system. Includes API server URLs, backup server configurations, version information, and endpoint definitions. The configuration supports automatic failover, load balancing hints, and update interval specifications. Changes to this file automatically propagate to all deployed Arduino devices within their discovery interval.

#### 🗂️ **archive_debug_files/**
*Historical debugging files and legacy configurations*

Stores debugging scripts and configuration files used during development and troubleshooting. Contains OpenSSL legacy configuration files (`openssl_legacy.cnf`) for handling older SSL/TLS connections, test utilities for debugging tool functionality, and historical log files from development sessions. These files provide insight into solved issues and can be referenced for future debugging scenarios. Includes test scripts for validating tool integrations and API connectivity issues.

## 🗄️ Database Schema

The system uses PostgreSQL with a carefully designed schema supporting multi-user, multi-device surf monitoring. See `docs/database_schema.txt` for a complete ASCII diagram of table relationships, data flow patterns, and security architecture.

**Key Tables:**
- `users` - User authentication and preferences
- `lamps` - Physical device registration and configuration  
- `current_conditions` - Latest surf data for each device
- `daily_usage` - API endpoint deduplication and management
- `usage_lamps` - Many-to-many API source configuration
- `location_websites` - Location-to-API mapping
- `password_reset_tokens` - Secure password recovery

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Redis server (for rate limiting)
- ESP32 development board (ESP32-WROOM-32 recommended)
- Arduino IDE or PlatformIO
- WS2812B LED strips (3 strips required)

### Environment Verification
Before setup, verify your environment:
```bash
# Check Python version
python --version  # Should be 3.8+

# Check PostgreSQL availability
psql --version

# Check Redis availability
redis-server --version
```

### Setup Web Application
```bash
cd web_and_database/
pip install -r requirements.txt

# Configure database connection in security_config.py
# Set DATABASE_URL environment variable or update config file
export DATABASE_URL="postgresql://user:password@localhost:5432/surf_lamp_db"

# Initialize database (if needed)
python -c "from data_base import init_db; init_db()"

# Start the web application
python app.py
```
Access dashboard at: `http://localhost:5000`

### Setup Background Processor
```bash
cd surf-lamp-processor/
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/surf_lamp_db"
export ARDUINO_TRANSPORT="http"  # Use "mock" for testing

# Start background processor (runs every 20 minutes)
python background_processor.py

# For single test run:
TEST_MODE=true python background_processor.py
```

### Setup Arduino Device
1. **Hardware Setup:**
   - Connect 3 WS2812B LED strips to GPIO pins 2, 4, and 5
   - Ensure adequate 5V power supply for LED strips
   - Use appropriate current capacity (calculate: LED count × 60mA)

2. **Firmware Flash:**
   ```bash
   # Update ServerDiscovery.h with your GitHub username
   # Flash surf-lamp-processor/fixed_surf_lamp.ino to ESP32
   ```

3. **WiFi Configuration:**
   - Connect to "SurfLamp-Setup" WiFi hotspot (password: surf123456)
   - Navigate to 192.168.4.1 in browser
   - Configure home WiFi through web interface
   - Device will auto-discover servers and fetch data every 31 minutes

### Configuration Files
- **Database:** `web_and_database/security_config.py`
- **API Endpoints:** `surf-lamp-processor/endpoint_configs.py`
- **Server Discovery:** `discovery-config/config.json`
- **Arduino Discovery:** Update GitHub username in `arduino/ServerDiscovery.h`

## 🌐 API Integration

### Multi-Source API Architecture
The system integrates with multiple marine weather APIs for comprehensive surf data:

**Primary APIs:**
- **Open-Meteo Marine API** - Wave height, period, direction
- **Open-Meteo Weather API** - Wind speed and direction
- **Isramar (Israel)** - Regional wave data for Israeli locations
- **NOAA APIs** - Marine weather data (configurable)

**Priority-Based Fallback System:**
Each location supports multiple API sources with automatic failover:
```
Location: Hadera, Israel
├── Priority 1: Isramar (wave data) - Primary source
├── Priority 2: Open-Meteo forecast (wind) - Primary wind
└── Priority 3: Open-Meteo GFS (wind) - Backup wind source
```

**Rate Limiting & Resilience:**
- 1-second delays between API calls prevent burst rate limiting
- Automatic retry with exponential backoff
- Failed endpoints temporarily suspended
- Data validation and error handling
- Graceful degradation when APIs are unavailable

**Adding New APIs:**
1. Add endpoint configuration to `endpoint_configs.py`
2. Define field mappings for JSON response parsing
3. Update `MULTI_SOURCE_LOCATIONS` in `data_base.py`
4. Test with single processing cycle

## 🔒 Security Features

- bcrypt password hashing with salt
- CSRF protection with Flask-WTF
- Redis-backed rate limiting
- Secure password reset with time-limited tokens
- Input sanitization and validation
- Foreign key constraints with cascade deletes
- HTTPS enforcement for Arduino communication

## 📊 Monitoring & Testing

### System Health Monitoring

**Background Processor Monitoring:**
```bash
# Check processor logs
tail -f surf-lamp-processor/lamp_processor.log

# Test single processing cycle
cd surf-lamp-processor/
TEST_MODE=true python background_processor.py

# Verify API endpoints
python test_pull_endpoints.py
```

**Discovery System Testing:**
```bash
# Test server discovery mechanism
python test_discovery_system.py

# Verify GitHub configuration
curl https://[username].github.io/[repo]/discovery-config/config.json
```

**Arduino Device Monitoring:**

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /api/status` | Device health check | Full system status JSON |
| `GET /api/fetch` | Manual data trigger | Forces immediate data fetch |
| `GET /api/led-test` | Hardware validation | LED strip test sequence |
| `GET /api/info` | Device information | Hardware specs and config |

**Example Status Check:**
```bash
# Get device status
curl http://192.168.1.100/api/status

# Expected response:
{
  "arduino_id": 4433,
  "status": "online",
  "wifi_connected": true,
  "ip_address": "192.168.1.100",
  "uptime_ms": 3600000,
  "last_surf_data": {
    "wave_height_m": 1.5,
    "last_update_ms": 1800000
  }
}
```

### Performance Monitoring
**Key Metrics to Monitor:**
- Background processor cycle time (should be < 5 minutes)
- API response times and success rates
- Arduino device connectivity and data freshness
- Database query performance
- Memory usage on ESP32 devices (should maintain >200KB free heap)

## 🌍 Supported Locations

Currently supports 7 surf locations in Israel:
- Hadera, Israel (primary coverage area)
- Tel Aviv, Israel  
- Ashdod, Israel
- Haifa, Israel
- Netanya, Israel
- Ashkelon, Israel
- Nahariya, Israel

## 📱 Hardware Requirements

- ESP32 development board (recommended: ESP32-WROOM-32)
- WS2812B LED strips (3 strips: center, left, right)
- Power supply (5V, appropriate amperage for LED count)
- Breadboard and connecting wires
- Optional: Custom PCB for production deployment

## 🔧 Development

### Architecture Overview
The project uses a modular architecture with clear separation of concerns:

**Layer Separation:**
- **Presentation Layer:** Web dashboard (Flask templates), Arduino API, LED visualization
- **Business Logic:** Flask application, background processor, server discovery
- **Data Access:** SQLAlchemy ORM, API integration, security controls
- **Persistence:** PostgreSQL database, Redis cache, file system

**Development Environment Setup:**
```bash
# Clone and setup
git clone [repository-url]
cd Git_Surf_Lamp_Agent

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r web_and_database/requirements.txt
pip install -r surf-lamp-processor/requirements.txt
```

**Testing Strategy:**
- **Unit Tests:** Individual component testing
- **Integration Tests:** API endpoint validation
- **Hardware Tests:** Arduino LED strip validation
- **End-to-End Tests:** Complete data flow verification

**Development Workflow:**
1. **Database First:** Design schema changes in `docs/database_schema.txt`
2. **API Development:** Update endpoints and test with Postman/curl
3. **Frontend Changes:** Modify Flask templates and test in browser
4. **Arduino Development:** Use mock transport for testing without hardware
5. **Integration Testing:** Test complete data flow from API to LED

**Environment-Specific Configurations:**
```bash
# Development
export ARDUINO_TRANSPORT="mock"
export TEST_MODE="true"
export DEBUG="true"

# Production
export ARDUINO_TRANSPORT="http"
export TEST_MODE="false"
export DEBUG="false"
```

**Code Style & Standards:**
- Follow PEP 8 for Python code
- Use meaningful variable names reflecting domain concepts
- Comment complex business logic and Arduino calculations
- Maintain consistent error handling patterns

### Advanced Troubleshooting

**Common Issues & Solutions:**

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Arduino not updating | LEDs show old data | Check `arduino_ip` in database, verify network connectivity |
| Background processor stuck | No new data in logs | Check API rate limits, verify database connection |
| Web dashboard errors | Login failures, timeouts | Check Redis connection, verify PostgreSQL status |
| LED strips not working | No light output | Test power supply, check GPIO pin connections |

**Performance Optimization:**
- Monitor database query execution times
- Optimize API call frequency (current: 20-minute intervals)
- Implement connection pooling for high-traffic scenarios
- Use Redis caching for frequently accessed data

**Known Limitations:**
- Maximum 100 concurrent Arduino devices per server instance
- API rate limits may affect real-time updates during peak usage
- ESP32 memory constraints limit complex LED animations
- IPv4 only (IPv6 support planned for future release)

## 🤝 Contributing

### Contribution Workflow
1. **Fork the repository** and create a feature branch
2. **Follow development standards:**
   - Test with both mock and real Arduino devices
   - Verify database migrations don't break existing data
   - Check API endpoint backward compatibility
   - Validate LED visualization changes with hardware

3. **Testing Requirements:**
   - Run background processor in test mode
   - Verify Arduino device registration and data flow
   - Test web dashboard functionality
   - Validate new API integrations with real endpoints

4. **Documentation Updates:**
   - Update relevant README sections
   - Document new configuration options
   - Add troubleshooting entries for new features
   - Update database schema diagrams if applicable

5. **Pull Request Guidelines:**
   - Include comprehensive testing results
   - Provide before/after screenshots for UI changes
   - Document any breaking changes
   - Ensure compatibility with existing Arduino deployments

### Development Guidelines
**Before Contributing:**
- Review existing issues and feature requests
- Discuss major changes in GitHub issues first
- Ensure your development environment matches prerequisites

**Code Quality Standards:**
- Follow existing code style and patterns
- Add logging for new background processes
- Include error handling for new API integrations
- Maintain security best practices (no hardcoded credentials)

## 📚 Technical Documentation

### Core Documentation Files
- **[SYSTEM_DOCUMENTATION.md](docs/SYSTEM_DOCUMENTATION.md)** - Technical deep-dive and implementation details
- **[database_schema.txt](docs/database_schema.txt)** - Complete database schema and relationships
- **[database_schema_v2.txt](docs/database_schema_v2.txt)** - Enhanced schema with security architecture
- **[arduino_architecture_schema.txt](docs/arduino_architecture_schema.txt)** - Hardware and firmware architecture
- **[surf-lamp-processor README](docs/surf-lamp-processor-README.md)** - Background processor setup and configuration

### API Documentation
- **Arduino Endpoints:** See `docs/arduino_payload_documentation.md`
- **Web API:** Authentication, lamp management, and data endpoints
- **Background Processing:** API integration and data flow patterns

### Troubleshooting Resources
- **Common Issues:** Database connection, Arduino connectivity, LED hardware
- **Performance Optimization:** API rate limiting, database queries, memory management
- **Security Configuration:** Authentication, rate limiting, input validation

## 📄 License

This project is licensed under the MIT License - see individual files for specific license terms.