# V3 Binary Protocol Endpoint

## Overview

The v3 endpoint provides a **94% smaller** binary protocol alternative to JSON for Arduino communication.

- **v2 (JSON)**: ~450 bytes per response
- **v3 (Binary)**: 26 bytes per response (9 surf + 17 settings)

## Backward Compatibility

**Existing Arduinos**: Continue using `/api/arduino/v2/<id>/data` (JSON)
**New Arduinos**: Use `/api/arduino/v3/<id>/data` (Binary)

No breaking changes - both endpoints coexist.

## Endpoint

```
GET /api/arduino/v3/<arduino_id>/data
```

**Response:**
- Content-Type: `application/octet-stream`
- Size: 26 bytes (9 + 17)

## Packet Structure

### SurfData Packet (9 bytes)
```
Bytes 0-7: Data (64 bits)
  Bits 0-5:   wave_period_s (6 bits)
  Bits 6-15:  wave_height_cm (10 bits)
  Bits 16-25: wave_threshold_cm (10 bits)
  Bits 26-35: wind_speed_mps (10 bits)
  Bits 36-42: wind_threshold_knots (7 bits)
  Bits 43-52: wind_direction_deg (10 bits)
  Bit 53:     stale_data flag
  Bit 54:     data_available flag
  Bit 55:     quiet_hours flag
  Bit 56:     off_hours flag

Byte 8: CRC-8 checksum
```

### SettingsData Packet (17 bytes)
```
Bytes 0-7: Data1 (64 bits)
  Bits 0-2:   led_theme (3 bits)
  Bits 3-9:   brightness (7 bits, 0-100%)
  Bits 10-29: fetch_interval_ms (20 bits)
  Bits 30-50: latitude fixed-point (21 bits, ±0.0001°)

Bytes 8-15: Data2 (64 bits)
  Bits 0-21:  longitude fixed-point (22 bits, ±0.0001°)
  Bits 22-38: tz_offset (17 bits, seconds)

Byte 16: CRC-8 checksum
```

## Arduino Integration

### 1. Include C++ Header
Copy `my_lib/esp_Server_encoding.hpp` to your Arduino project.

### 2. Update Endpoint
```cpp
// Old (v2 JSON)
const char* endpoint = "/api/arduino/v2/123/data";

// New (v3 Binary)
const char* endpoint = "/api/arduino/v3/123/data";
```

### 3. Parse Binary Response
```cpp
#include "esp_Server_encoding.hpp"

// Receive 26 bytes from server
uint8_t response[26];
http.readBytes(response, 26);

// Parse surf data (first 9 bytes)
uint64_t surf_packed = 0;
for (int i = 0; i < 8; i++) {
    surf_packed = (surf_packed << 8) | response[i];
}
SurfData surf(surf_packed);

// Validate CRC
uint8_t surf_crc = response[8];
if (!surf.ValidateCRC(surf_crc)) {
    Serial.println("ERROR: Surf data CRC failed!");
    return;
}

// Parse settings data (bytes 9-25)
uint64_t settings_data1 = 0, settings_data2 = 0;
for (int i = 0; i < 8; i++) {
    settings_data1 = (settings_data1 << 8) | response[9 + i];
    settings_data2 = (settings_data2 << 8) | response[17 + i];
}
SettingsData settings(settings_data1, settings_data2);

// Validate CRC
uint8_t settings_crc = response[25];
if (!settings.ValidateCRC(settings_crc)) {
    Serial.println("ERROR: Settings data CRC failed!");
    return;
}

// Use the data
int wave_height = surf.GetWaveHeight();
int wave_threshold = surf.GetWaveThreshold();
bool quiet_hours = surf.GetQuietHours();
float latitude = settings.GetLatitude();
// ... etc
```

## Testing

```bash
# Test v2 (JSON) - still works
curl http://localhost:5000/api/arduino/v2/1/data

# Test v3 (Binary) - new endpoint
curl http://localhost:5000/api/arduino/v3/1/data --output response.bin
xxd response.bin  # View binary hex dump
```

## Python Testing

```bash
cd web_and_database
python test_v3_endpoint.py
```

Expected output:
```
✓ ALL TESTS PASSED - Ready for production!
Total packet size: 26 bytes
JSON equivalent: ~450 bytes
Compression: 94.2%
```

## Migration Path

1. **Phase 1** (Now): Both v2 and v3 coexist
2. **Phase 2** (After all Arduinos updated): Monitor v2 usage
3. **Phase 3** (Future): Deprecate v2 when no longer used

## Benefits

- **94% bandwidth reduction**: 26 bytes vs 450 bytes
- **Faster parsing**: Binary decoding vs JSON parsing
- **Error detection**: CRC-8 catches corrupted packets
- **Future-proof**: 38 unused bits for expansion
- **No RAM allocation**: Fixed-size structs on stack

## Error Handling

If CRC validation fails:
1. Arduino discards packet
2. Requests retransmission (optional)
3. Logs error for debugging

Typical causes:
- Network corruption
- WiFi interference
- Hardware malfunction
