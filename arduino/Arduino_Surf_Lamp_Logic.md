# Arduino Surf Lamp Logic Documentation

## Overview
The Surf Lamp is an ESP32-based device that visualizes surf conditions using three LED strips. It connects to WiFi, fetches surf data from a remote server, and displays wave height, wind speed, wind direction, and wave period through colored LEDs.

## Device Configuration
- **Arduino ID**: 4433 (unique identifier for each device)
- **LED Configuration**:
  - Center Strip: 12 LEDs (Wind Speed + Direction)
  - Right Strip: 9 LEDs (Wave Height)
  - Left Strip: 9 LEDs (Wave Period)

## WiFi Connection Process

### 1. Initial Connection Attempt
- Device attempts to connect using stored WiFi credentials
- Default credentials: SSID="Sunrise", Password="4085429360"
- Connection timeout: 30 seconds

### 2. Configuration Mode (if WiFi fails)
- Creates WiFi Access Point: "SurfLamp-Setup"
- AP Password: "surf123456"
- Web interface available at AP IP address
- User can enter new WiFi credentials via web form
- AP times out after 60 seconds, then retries original connection

### 3. Reconnection Logic
- Continuously monitors WiFi status
- Auto-reconnects every 30 seconds if connection lost
- Stores new credentials permanently in NVRAM

## LED Color Coding

### Center Strip (Wind Speed + Direction)
**Wind Speed Visualization:**
- **Normal**: White LEDs (number of LEDs = wind speed in m/s × 0.97)
- **Alert Mode**: Blinking bright white (when wind ≥ threshold in knots)

**Wind Direction (Last LED):**
- **North (315°-44°)**: Green
- **East (45°-134°)**: Yellow
- **South (135°-224°)**: Red
- **West (225°-314°)**: Blue

### Right Strip (Wave Height)
- **Normal**: Solid Blue
- **Alert Mode**: Blinking Bright Blue (when wave height ≥ threshold)
- Number of LEDs = wave height in cm ÷ 25

### Left Strip (Wave Period)
- **Always**: Solid Green
- Number of LEDs = wave period in seconds

## Data Acquisition Process

### 1. Server Discovery
- Uses ServerDiscovery class to locate API server
- Maintains current server endpoint

### 2. Automatic Data Fetching
- **Interval**: Every 31 minutes (1,860,000 ms)
- **URL Format**: `https://{server}/api/arduino/{ARDUINO_ID}/data`
- **Method**: HTTPS GET request with 15-second timeout
- **Security**: Uses insecure SSL (self-signed certificates accepted)

### 3. Manual Data Fetching
- Available via `/api/fetch` HTTP endpoint
- Can be triggered remotely for immediate updates

### 4. Data Processing
**Expected JSON Format:**
```json
{
  "wave_height_cm": 150,
  "wave_period_s": 8.5,
  "wind_speed_mps": 12,
  "wind_direction_deg": 180,
  "wave_threshold_cm": 100,
  "wind_speed_threshold_knots": 15
}
```

## User Interaction

### Status Indicators (Status LED)
- **Blinking Blue**: Connecting to WiFi
- **Blinking Green**: Connected with fresh data (< 30 min old)
- **Blinking Blue (slow)**: Connected but no recent data
- **Blinking Red**: WiFi connection failed
- **Blinking Yellow**: Configuration mode active

### Physical Controls
- **Boot Button (Pin 0)**: Available for future use
- **Reset Button**: Restarts device (standard ESP32 functionality)

### HTTP API Endpoints
Users can interact with the device via HTTP requests:
- `GET /api/status` - View device status and last surf data
- `GET /api/test` - Test device connectivity
- `GET /api/led-test` - Trigger LED test sequence
- `GET /api/info` - Get device hardware information
- `GET /api/fetch` - Manually fetch new surf data
- `POST /api/update` - Send surf data directly to device

## Alert System

### Wave Height Alert
- **Trigger**: When wave height ≥ wave_threshold_cm
- **Visual**: Right strip LEDs blink bright blue
- **Default Threshold**: 100 cm

### Wind Speed Alert  
- **Trigger**: When wind speed ≥ wind_speed_threshold_knots
- **Visual**: Center strip LEDs blink bright white
- **Default Threshold**: 15 knots
- **Conversion**: Wind speed converted from m/s to knots for threshold comparison

## Data Flow Summary

1. **Startup**: Device performs LED test, connects to WiFi
2. **Initial Fetch**: Attempts to get surf data immediately after connection
3. **Continuous Operation**:
   - Serves HTTP requests
   - Monitors WiFi connection
   - Fetches new data every 31 minutes
   - Updates LED display based on current data
   - Indicates system status via status LED
4. **Error Handling**: Automatically retries failed operations, maintains connection stability

## Technical Details
- **Platform**: ESP32 with WiFiClientSecure for HTTPS
- **LED Library**: FastLED with WS2812B strips
- **JSON Processing**: ArduinoJson library
- **Storage**: Preferences library for NVRAM credential storage
- **Update Rate**: LED animations update every 50ms for smooth blinking
- **Memory Management**: Dynamic JSON documents with appropriate sizing