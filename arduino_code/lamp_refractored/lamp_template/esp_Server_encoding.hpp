/*
Bit Layout (56 bits total, fits in uint64_t):
Bits 0-5:   wave_period_s (6 bits, range 0-63)
Bits 6-15:  wave_height_cm (10 bits, range 0-1023)
Bits 16-25: wave_threshold_cm (10 bits, range 0-1023)
Bits 26-35: wind_speed_mps (10 bits, range 0-1023)
Bits 36-42: wind_threshold_knots (7 bits, range 0-127)
Bits 43-52: wind_direction_deg (10 bits, range 0-1023)
Bit 53:     stale_data flag (1 bit)
Bit 54:     data_available flag (1 bit)
Bit 55:     quiet_hours flag (1 bit)
Bit 56:     off_hours flag (1 bit)
Bits 57-63: UNUSED (reserved for future)
*/

#ifndef ESP_SERVER_ENCODING_HPP
#define ESP_SERVER_ENCODING_HPP

#include <cstdint>
#include <cstddef>

/*
CRC-8 Checksum Calculation
Uses polynomial 0x07 (x^8 + x^2 + x + 1) - common in embedded systems
*/
class CRC8
{
public:
    static constexpr uint8_t POLYNOMIAL = 0x07;

    // Calculate CRC-8 for a byte array
    static uint8_t Calculate(const uint8_t* data, size_t length)
    {
        uint8_t crc = 0x00;
        for (size_t i = 0; i < length; ++i)
        {
            crc ^= data[i];
            for (uint8_t bit = 0; bit < 8; ++bit)
            {
                if (crc & 0x80)
                {
                    crc = (crc << 1) ^ POLYNOMIAL;
                }
                else
                {
                    crc <<= 1;
                }
            }
        }
        return crc;
    }

    // Calculate CRC-8 for a 64-bit value (stored as big-endian bytes)
    static uint8_t Calculate(uint64_t value)
    {
        uint8_t bytes[8];
        // Convert to big-endian byte array
        for (int i = 7; i >= 0; --i)
        {
            bytes[7 - i] = (value >> (i * 8)) & 0xFF;
        }
        return Calculate(bytes, 8);
    }
};

enum class SurfDataBitsOffset: uint32_t
{
    PERIOD_OFF = 0,
    HEIGHT_OFF = 6,
    WAVE_THRESHOLD_OFF = 16,
    SPEED_OFF = 26,
    WIND_THRESHOLD_OFF = 36,
    DIRECTION_OFF = 43,
    STALE_DATA = 53,
    DATA_AVAILABLE = 54,
    QUIET_HOURS = 55,
    OFF_HOURS = 56
};
  
 
                                                                                                                                                                                         
class SurfDataPacket
{
public:
    SurfDataPacket(uint64_t raw_values) : m_decimal(raw_values) {}

    // Get raw data for CRC calculation
    uint64_t GetRawData() const { return m_decimal; }

    // Calculate CRC-8 checksum for this packet
    uint8_t CalculateCRC() const
    {
        return CRC8::Calculate(m_decimal);
    }

    // Validate packet with provided CRC
    bool ValidateCRC(uint8_t expected_crc) const
    {
        return CalculateCRC() == expected_crc;
    }

    // Current readings
    uint8_t GetWavePeriod() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::PERIOD_OFF)) & 0x3F;
    }

    uint16_t GetWaveHeight() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::HEIGHT_OFF)) & 0x3FF;
    }

    uint16_t GetWindSpeed() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::SPEED_OFF)) & 0x3FF;
    }

    uint16_t GetWindDirection() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::DIRECTION_OFF)) & 0x3FF;
    }

    // Thresholds (for Arduino blink logic)
    uint16_t GetWaveThreshold() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::WAVE_THRESHOLD_OFF)) & 0x3FF;
    }

    uint8_t GetWindThreshold() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::WIND_THRESHOLD_OFF)) & 0x7F;
    }

    // Flags
    bool GetStaleData() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::STALE_DATA)) & 0x1;
    }

    bool GetDataAvailable() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::DATA_AVAILABLE)) & 0x1;
    }

    bool GetQuietHours() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::QUIET_HOURS)) & 0x1;
    }

    bool GetOffHours() const
    {
        return (m_decimal >> static_cast<uint32_t>(SurfDataBitsOffset::OFF_HOURS)) & 0x1;
    }

    static uint64_t PackData(uint8_t period, uint16_t height, uint16_t wave_threshold,
                             uint16_t speed, uint8_t wind_threshold, uint16_t direction,
                             bool stale, bool available, bool quiet_hours, bool off_hours)
    {
        return ((uint64_t)(period & 0x3F) << static_cast<uint32_t>(SurfDataBitsOffset::PERIOD_OFF)) |
               ((uint64_t)(height & 0x3FF) << static_cast<uint32_t>(SurfDataBitsOffset::HEIGHT_OFF)) |
               ((uint64_t)(wave_threshold & 0x3FF) << static_cast<uint32_t>(SurfDataBitsOffset::WAVE_THRESHOLD_OFF)) |
               ((uint64_t)(speed & 0x3FF) << static_cast<uint32_t>(SurfDataBitsOffset::SPEED_OFF)) |
               ((uint64_t)(wind_threshold & 0x7F) << static_cast<uint32_t>(SurfDataBitsOffset::WIND_THRESHOLD_OFF)) |
               ((uint64_t)(direction & 0x3FF) << static_cast<uint32_t>(SurfDataBitsOffset::DIRECTION_OFF)) |
               ((uint64_t)(stale ? 1 : 0) << static_cast<uint32_t>(SurfDataBitsOffset::STALE_DATA)) |
               ((uint64_t)(available ? 1 : 0) << static_cast<uint32_t>(SurfDataBitsOffset::DATA_AVAILABLE)) |
               ((uint64_t)(quiet_hours ? 1 : 0) << static_cast<uint32_t>(SurfDataBitsOffset::QUIET_HOURS)) |
               ((uint64_t)(off_hours ? 1 : 0) << static_cast<uint32_t>(SurfDataBitsOffset::OFF_HOURS));
    }                                                                                                                                                                                  
                                                                                                                                                                                         
private:
    uint64_t m_decimal;
};

/*
Settings Data - Static configuration (rarely changes)
Uses 16 bytes (2 x uint64_t) for user preferences and location data

First uint64_t (m_data1):
Bits 0-2:   led_theme (3 bits, 0-7 themes)
Bits 3-9:   brightness (7 bits, 0-100%)
Bits 10-29: fetch_interval_ms (20 bits, max ~1M ms)
Bits 30-50: latitude fixed-point (21 bits, -90 to +90, precision 0.0001°)
Bits 51-63: unused (13 bits)

Second uint64_t (m_data2):
Bits 0-21:  longitude fixed-point (22 bits, -180 to +180, precision 0.0001°)
Bits 22-38: tz_offset (17 bits, -43200 to +43200 seconds)
Bits 39-63: unused (25 bits)
*/

enum class SettingsDataBitsOffset: uint32_t
{
    // First uint64_t offsets
    LED_THEME = 0,
    BRIGHTNESS = 3,
    FETCH_INTERVAL = 10,
    LATITUDE = 30,

    // Second uint64_t offsets (relative to m_data2)
    LONGITUDE = 0,
    TZ_OFFSET = 22
};

enum class LEDTheme: uint8_t
{
    CLASSIC_SURF = 0,
    VIBRANT_MIX = 1,
    TROPICAL_PARADISE = 2,
    OCEAN_SUNSET = 3,
    ELECTRIC_VIBES = 4
};

class SettingsData
{
public:
    SettingsData(uint64_t data1, uint64_t data2) : m_data1(data1), m_data2(data2) {}

    // Get raw data for CRC calculation
    void GetRawData(uint64_t& out_data1, uint64_t& out_data2) const
    {
        out_data1 = m_data1;
        out_data2 = m_data2;
    }

    // Calculate CRC-8 checksum for this packet (includes both uint64_t values)
    uint8_t CalculateCRC() const
    {
        uint8_t bytes[16];
        // Convert both uint64_t to big-endian bytes
        for (int i = 7; i >= 0; --i)
        {
            bytes[7 - i] = (m_data1 >> (i * 8)) & 0xFF;
            bytes[15 - i] = (m_data2 >> (i * 8)) & 0xFF;
        }
        return CRC8::Calculate(bytes, 16);
    }

    // Validate packet with provided CRC
    bool ValidateCRC(uint8_t expected_crc) const
    {
        return CalculateCRC() == expected_crc;
    }

    LEDTheme GetLEDTheme() const
    {
        return static_cast<LEDTheme>((m_data1 >> static_cast<uint32_t>(SettingsDataBitsOffset::LED_THEME)) & 0x7);
    }

    uint8_t GetBrightness() const
    {
        return (m_data1 >> static_cast<uint32_t>(SettingsDataBitsOffset::BRIGHTNESS)) & 0x7F;
    }

    uint32_t GetFetchIntervalMs() const
    {
        return (m_data1 >> static_cast<uint32_t>(SettingsDataBitsOffset::FETCH_INTERVAL)) & 0xFFFFF;
    }

    // Returns latitude in degrees (converts from fixed-point)
    float GetLatitude() const
    {
        // Extract 21-bit signed value
        uint32_t raw = (m_data1 >> static_cast<uint32_t>(SettingsDataBitsOffset::LATITUDE)) & 0x1FFFFF;
        // Convert from fixed-point: value represents lat * 10000
        // Sign-extend if negative (bit 20 is sign bit)
        int32_t signed_val = (raw & 0x100000) ? (raw | 0xFFE00000) : raw;
        return signed_val / 10000.0f;
    }

    // Returns longitude in degrees (converts from fixed-point)
    float GetLongitude() const
    {
        // Extract 22-bit signed value
        uint32_t raw = (m_data2 >> static_cast<uint32_t>(SettingsDataBitsOffset::LONGITUDE)) & 0x3FFFFF;
        // Convert from fixed-point: value represents lon * 10000
        // Sign-extend if negative (bit 21 is sign bit)
        int32_t signed_val = (raw & 0x200000) ? (raw | 0xFFC00000) : raw;
        return signed_val / 10000.0f;
    }

    // Returns timezone offset in seconds
    int32_t GetTzOffset() const
    {
        // Extract 17-bit signed value
        uint32_t raw = (m_data2 >> static_cast<uint32_t>(SettingsDataBitsOffset::TZ_OFFSET)) & 0x1FFFF;
        // Sign-extend if negative (bit 16 is sign bit)
        return (raw & 0x10000) ? (raw | 0xFFFE0000) : raw;
    }

    static void Pack(LEDTheme theme, uint8_t brightness, uint32_t fetch_interval_ms,
                     float latitude, float longitude, int32_t tz_offset,
                     uint64_t& out_data1, uint64_t& out_data2)
    {
        // Convert latitude to fixed-point (21 bits signed, -90 to +90, precision 0.0001°)
        int32_t lat_fixed = static_cast<int32_t>(latitude * 10000.0f);
        uint32_t lat_bits = lat_fixed & 0x1FFFFF;

        // Convert longitude to fixed-point (22 bits signed, -180 to +180, precision 0.0001°)
        int32_t lon_fixed = static_cast<int32_t>(longitude * 10000.0f);
        uint32_t lon_bits = lon_fixed & 0x3FFFFF;

        // Pack tz_offset (17 bits signed)
        uint32_t tz_bits = tz_offset & 0x1FFFF;

        out_data1 = ((uint64_t)(static_cast<uint8_t>(theme) & 0x7) << static_cast<uint32_t>(SettingsDataBitsOffset::LED_THEME)) |
                    ((uint64_t)(brightness & 0x7F) << static_cast<uint32_t>(SettingsDataBitsOffset::BRIGHTNESS)) |
                    ((uint64_t)(fetch_interval_ms & 0xFFFFF) << static_cast<uint32_t>(SettingsDataBitsOffset::FETCH_INTERVAL)) |
                    ((uint64_t)lat_bits << static_cast<uint32_t>(SettingsDataBitsOffset::LATITUDE));

        out_data2 = ((uint64_t)lon_bits << static_cast<uint32_t>(SettingsDataBitsOffset::LONGITUDE)) |
                    ((uint64_t)tz_bits << static_cast<uint32_t>(SettingsDataBitsOffset::TZ_OFFSET));
    }

private:
    uint64_t m_data1;
    uint64_t m_data2;
};

#endif // ESP_SERVER_ENCODING_HPP
