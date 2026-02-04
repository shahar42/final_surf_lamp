# binary_protocol.py
"""
Binary Protocol Encoder for Surf Lamp V3 API
Implements the same packing and CRC logic as the C++ esp_Server_encoding.hpp
"""

import struct

class CRC8:
    """
    CRC-8 Checksum Calculation
    Uses polynomial 0x07 (x^8 + x^2 + x + 1)
    """
    POLYNOMIAL = 0x07

    @staticmethod
    def calculate(data: bytes) -> int:
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ CRC8.POLYNOMIAL
                else:
                    crc <<= 1
                crc &= 0xFF # Keep it 8-bit
        return crc

    @staticmethod
    def calculate_int64(value: int) -> int:
        """Calculate CRC for a 64-bit integer (big-endian)"""
        return CRC8.calculate(value.to_bytes(8, byteorder='big'))

class LEDTheme:
    CLASSIC_SURF = 0
    VIBRANT_MIX = 1
    TROPICAL_PARADISE = 2
    OCEAN_SUNSET = 3
    ELECTRIC_VIBES = 4

    @staticmethod
    def from_string(theme_name: str) -> int:
        mapping = {
            'classic_surf': 0,
            'vibrant_mix': 1,
            'tropical_paradise': 2,
            'ocean_sunset': 3,
            'electric_vibes': 4
        }
        return mapping.get(theme_name, 0)

def encode_v3_response(surf_data: dict, settings_data: dict) -> bytes:
    """
    Encode surf and settings data into the 26-byte binary format.
    
    Args:
        surf_data: Dict containing:
            - wave_period_s (int)
            - wave_height_cm (int)
            - wave_threshold_cm (int)
            - wind_speed_mps (int)
            - wind_speed_threshold_knots (int)
            - wind_direction_deg (int)
            - stale_data_warning (bool)
            - data_available (bool)
            - quiet_hours_active (bool)
            - off_hours_active (bool)
            
        settings_data: Dict containing:
            - led_theme (str)
            - brightness_multiplier (float)
            - fetch_interval_ms (int)
            - latitude (float)
            - longitude (float)
            - tz_offset (int)
            
    Returns:
        bytes: 26-byte binary payload
    """
    
    # --- PACK SURF DATA (56 bits) ---
    # Bits 0-5:   wave_period_s (6 bits)
    # Bits 6-15:  wave_height_cm (10 bits)
    # Bits 16-25: wave_threshold_cm (10 bits)
    # Bits 26-35: wind_speed_mps (10 bits)
    # Bits 36-42: wind_threshold_knots (7 bits)
    # Bits 43-52: wind_direction_deg (10 bits)
    # Bit 53:     stale_data
    # Bit 54:     data_available
    # Bit 55:     quiet_hours
    # Bit 56:     off_hours
    
    period = int(surf_data.get('wave_period_s', 0)) & 0x3F
    height = int(surf_data.get('wave_height_cm', 0)) & 0x3FF
    wave_thresh = int(surf_data.get('wave_threshold_cm', 100)) & 0x3FF
    speed = int(surf_data.get('wind_speed_mps', 0)) & 0x3FF
    wind_thresh = int(surf_data.get('wind_speed_threshold_knots', 15)) & 0x7F
    direction = int(surf_data.get('wind_direction_deg', 0)) & 0x3FF
    
    stale = 1 if surf_data.get('stale_data_warning', False) else 0
    available = 1 if surf_data.get('data_available', True) else 0
    quiet = 1 if surf_data.get('quiet_hours_active', False) else 0
    off = 1 if surf_data.get('off_hours_active', False) else 0
    
    surf_packed = (
        (period << 0) |
        (height << 6) |
        (wave_thresh << 16) |
        (speed << 26) |
        (wind_thresh << 36) |
        (direction << 43) |
        (stale << 53) |
        (available << 54) |
        (quiet << 55) |
        (off << 56)
    )
    
    surf_crc = CRC8.calculate_int64(surf_packed)
    
    # --- PACK SETTINGS DATA (128 bits -> two 64-bit chunks) ---
    
    # Chunk 1:
    # Bits 0-2:   led_theme (3 bits)
    # Bits 3-9:   brightness (7 bits)
    # Bits 10-29: fetch_interval_ms (20 bits)
    # Bits 30-50: latitude fixed-point (21 bits)
    
    theme = LEDTheme.from_string(settings_data.get('led_theme', 'classic_surf')) & 0x7
    brightness_val = int(settings_data.get('brightness_multiplier', 0.6) * 100) & 0x7F
    interval = int(settings_data.get('fetch_interval_ms', 13*60*1000)) & 0xFFFFF
    
    lat = float(settings_data.get('latitude', 0.0))
    lat_fixed = int(lat * 10000)
    lat_bits = lat_fixed & 0x1FFFFF # 21 bits signed handled as unsigned bits
    
    settings_1 = (
        (theme << 0) |
        (brightness_val << 3) |
        (interval << 10) |
        (lat_bits << 30)
    )
    
    # Chunk 2:
    # Bits 0-21:  longitude fixed-point (22 bits)
    # Bits 22-38: tz_offset (17 bits)
    
    lon = float(settings_data.get('longitude', 0.0))
    lon_fixed = int(lon * 10000)
    lon_bits = lon_fixed & 0x3FFFFF # 22 bits
    
    tz = int(settings_data.get('tz_offset', 0))
    tz_bits = tz & 0x1FFFF # 17 bits
    
    settings_2 = (
        (lon_bits << 0) |
        (tz_bits << 22)
    )
    
    # Calculate Settings CRC (over both chunks)
    # Pack both chunks into 16 bytes big-endian
    settings_bytes = settings_1.to_bytes(8, byteorder='big') + settings_2.to_bytes(8, byteorder='big')
    settings_crc = CRC8.calculate(settings_bytes)
    
    # --- ASSEMBLE PACKET (26 bytes) ---
    # 8 bytes SurfData
    # 1 byte SurfData CRC
    # 8 bytes Settings1
    # 8 bytes Settings2
    # 1 byte Settings CRC
    
    packet = (
        surf_packed.to_bytes(8, byteorder='big') +
        bytes([surf_crc]) +
        settings_bytes +
        bytes([settings_crc])
    )
    
    return packet
