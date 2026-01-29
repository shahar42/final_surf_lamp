"""
Binary Protocol Encoder for Arduino Communication
Matches esp_Server_encoding.hpp C++ implementation

Provides 94% compression vs JSON (26 bytes vs 450 bytes)
- SurfData: 8 bytes + 1 byte CRC
- SettingsData: 16 bytes + 1 byte CRC
"""

import struct
from enum import IntEnum


class LEDTheme(IntEnum):
    """LED theme enum matching C++ LEDTheme"""
    CLASSIC_SURF = 0
    VIBRANT_MIX = 1
    TROPICAL_PARADISE = 2
    OCEAN_SUNSET = 3
    ELECTRIC_VIBES = 4


class CRC8:
    """CRC-8 checksum calculator using polynomial 0x07"""
    POLYNOMIAL = 0x07

    @staticmethod
    def calculate(data: bytes) -> int:
        """Calculate CRC-8 for byte array"""
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ CRC8.POLYNOMIAL) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc


class SurfDataEncoder:
    """
    Encodes dynamic surf conditions into 8 bytes

    Bit Layout:
    Bits 0-5:   wave_period_s (6 bits, 0-63)
    Bits 6-15:  wave_height_cm (10 bits, 0-1023)
    Bits 16-25: wave_threshold_cm (10 bits, 0-1023)
    Bits 26-35: wind_speed_mps (10 bits, 0-1023)
    Bits 36-42: wind_threshold_knots (7 bits, 0-127)
    Bits 43-52: wind_direction_deg (10 bits, 0-1023)
    Bit 53:     stale_data (1 bit)
    Bit 54:     data_available (1 bit)
    Bit 55:     quiet_hours (1 bit)
    Bit 56:     off_hours (1 bit)
    """

    @staticmethod
    def pack(period: int, height: int, wave_threshold: int,
             speed: int, wind_threshold: int, direction: int,
             stale: bool, available: bool, quiet: bool, off: bool) -> bytes:
        """
        Pack surf data into 9 bytes (8 data + 1 CRC)

        Returns:
            bytes: 9-byte packet ready for transmission
        """
        # Pack into 64-bit integer
        packed = (
            ((period & 0x3F) << 0) |
            ((height & 0x3FF) << 6) |
            ((wave_threshold & 0x3FF) << 16) |
            ((speed & 0x3FF) << 26) |
            ((wind_threshold & 0x7F) << 36) |
            ((direction & 0x3FF) << 43) |
            ((1 if stale else 0) << 53) |
            ((1 if available else 0) << 54) |
            ((1 if quiet else 0) << 55) |
            ((1 if off else 0) << 56)
        )

        # Convert to big-endian bytes
        data_bytes = packed.to_bytes(8, byteorder='big')

        # Calculate CRC
        crc = CRC8.calculate(data_bytes)

        # Return data + CRC
        return data_bytes + bytes([crc])


class SettingsDataEncoder:
    """
    Encodes static user settings into 16 bytes

    First uint64 (bytes 0-7):
    Bits 0-2:   led_theme (3 bits)
    Bits 3-9:   brightness (7 bits, 0-100%)
    Bits 10-29: fetch_interval_ms (20 bits)
    Bits 30-50: latitude fixed-point (21 bits, -90 to +90, precision 0.0001°)

    Second uint64 (bytes 8-15):
    Bits 0-21:  longitude fixed-point (22 bits, -180 to +180, precision 0.0001°)
    Bits 22-38: tz_offset (17 bits, -43200 to +43200 seconds)
    """

    @staticmethod
    def pack(theme: LEDTheme, brightness: int, fetch_interval_ms: int,
             latitude: float, longitude: float, tz_offset: int) -> bytes:
        """
        Pack settings data into 17 bytes (16 data + 1 CRC)

        Returns:
            bytes: 17-byte packet ready for transmission
        """
        # Convert GPS coords to fixed-point
        lat_fixed = int(latitude * 10000.0) & 0x1FFFFF  # 21 bits
        lon_fixed = int(longitude * 10000.0) & 0x3FFFFF  # 22 bits
        tz_bits = tz_offset & 0x1FFFF  # 17 bits

        # Pack first uint64
        data1 = (
            ((int(theme) & 0x7) << 0) |
            ((brightness & 0x7F) << 3) |
            ((fetch_interval_ms & 0xFFFFF) << 10) |
            ((lat_fixed) << 30)
        )

        # Pack second uint64
        data2 = (
            ((lon_fixed) << 0) |
            ((tz_bits) << 22)
        )

        # Convert to big-endian bytes
        data1_bytes = data1.to_bytes(8, byteorder='big')
        data2_bytes = data2.to_bytes(8, byteorder='big')
        data_bytes = data1_bytes + data2_bytes

        # Calculate CRC
        crc = CRC8.calculate(data_bytes)

        # Return data + CRC
        return data_bytes + bytes([crc])


def encode_v3_response(surf_data: dict, settings_data: dict) -> bytes:
    """
    Encode complete v3 response (surf + settings)

    Args:
        surf_data: Dict with surf condition keys
        settings_data: Dict with user settings keys

    Returns:
        bytes: 26-byte packet (9 surf + 17 settings)
    """
    # Map theme string to enum
    theme_map = {
        'classic_surf': LEDTheme.CLASSIC_SURF,
        'vibrant_mix': LEDTheme.VIBRANT_MIX,
        'tropical_paradise': LEDTheme.TROPICAL_PARADISE,
        'ocean_sunset': LEDTheme.OCEAN_SUNSET,
        'electric_vibes': LEDTheme.ELECTRIC_VIBES
    }

    # Encode surf conditions
    surf_packet = SurfDataEncoder.pack(
        period=surf_data['wave_period_s'],
        height=surf_data['wave_height_cm'],
        wave_threshold=surf_data['wave_threshold_cm'],
        speed=surf_data['wind_speed_mps'],
        wind_threshold=surf_data['wind_speed_threshold_knots'],
        direction=surf_data['wind_direction_deg'],
        stale=surf_data['stale_data_warning'],
        available=surf_data['data_available'],
        quiet=surf_data['quiet_hours_active'],
        off=surf_data['off_hours_active']
    )

    # Encode settings
    settings_packet = SettingsDataEncoder.pack(
        theme=theme_map.get(settings_data['led_theme'], LEDTheme.CLASSIC_SURF),
        brightness=int(settings_data['brightness_multiplier'] * 100),
        fetch_interval_ms=settings_data['fetch_interval_ms'],
        latitude=settings_data['latitude'],
        longitude=settings_data['longitude'],
        tz_offset=settings_data['tz_offset']
    )

    return surf_packet + settings_packet
