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

The system uses PostgreSQL with a carefully designed schema supporting multi-user, multi-device surf monitoring. See `database_schema.txt` for a complete ASCII diagram of table relationships, data flow patterns, and security architecture.

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
- Redis server
- ESP32 development board
- Arduino IDE or PlatformIO

### Setup Web Application
```bash
cd web_and_database/
pip install -r requirements.txt
# Configure database connection in security_config.py
python app.py
```

### Setup Background Processor
```bash
cd surf-lamp-processor/
pip install -r requirements.txt
python background_processor.py
```

### Setup Arduino Device
1. Flash `surf-lamp-processor/fixed_surf_lamp.ino` to ESP32
2. Connect to "SurfLamp-Setup" WiFi hotspot (password: surf123456)
3. Configure your home WiFi through web interface
4. Device will auto-discover servers and fetch data every 31 minutes

### Configuration
- Update GitHub username in `ServerDiscovery.h` discovery URLs
- Configure database credentials in `security_config.py`
- Set up supported surf locations in `endpoint_configs.py`
- Customize LED patterns and thresholds in Arduino code

## 🌐 API Integration

The system integrates with multiple marine weather APIs including NOAA, Marine Weather, and regional surf forecasting services. Each location can use multiple API sources with priority-based fallback. The background processor handles rate limiting, data validation, and automatic failover between API sources.

## 🔒 Security Features

- bcrypt password hashing with salt
- CSRF protection with Flask-WTF
- Redis-backed rate limiting
- Secure password reset with time-limited tokens
- Input sanitization and validation
- Foreign key constraints with cascade deletes
- HTTPS enforcement for Arduino communication

## 📊 Monitoring & Testing

Run the discovery system test:
```bash
python test_discovery_system.py
```

Test API endpoints:
```bash
python test_pull_endpoints.py
```

Monitor Arduino device:
- Visit `http://[arduino-ip]/api/status` for device status
- Use `http://[arduino-ip]/api/fetch` to manually trigger data fetch
- Check `http://[arduino-ip]/api/led-test` for hardware validation

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

The project uses a modular architecture with clear separation between web application, data processing, and hardware control layers. Each component can be developed and tested independently. The system supports both development and production configurations with environment-specific settings.

For detailed technical documentation, see individual README files in each directory and the complete database schema diagram in `database_schema.txt`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test with both simulated and hardware devices
4. Submit pull request with comprehensive testing results
5. Ensure compatibility with existing Arduino deployments

## 📄 License

This project is licensed under the MIT License - see individual files for specific license terms.