"""
C++ Binary Encoder for Surf Lamp V3 API

Uses C++ message_wrapper module for encoding (12.5x faster than Python).
Drop-in replacement for binary_protocol.encode_v3_response().
"""

import message_wrapper
from typing import Dict


def theme_to_enum(theme_name: str) -> message_wrapper.LEDTheme:
    """Convert theme string to C++ enum"""
    mapping = {
        'classic_surf': message_wrapper.LEDTheme.CLASSIC_SURF,
        'vibrant_mix': message_wrapper.LEDTheme.VIBRANT_MIX,
        'tropical_paradise': message_wrapper.LEDTheme.TROPICAL_PARADISE,
        'ocean_sunset': message_wrapper.LEDTheme.OCEAN_SUNSET,
        'electric_vibes': message_wrapper.LEDTheme.ELECTRIC_VIBES,
    }
    return mapping.get(theme_name, message_wrapper.LEDTheme.CLASSIC_SURF)


def encode_v3_response_cpp(surf_data: Dict, settings_data: Dict) -> bytes:
    """
    Encode surf and settings data into 26-byte binary format using C++.

    Drop-in replacement for binary_protocol.encode_v3_response().
    12.5x faster than Python encoding.

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

    # Extract and clamp surf data
    period = int(surf_data.get('wave_period_s', 0)) & 0x3F
    height = int(surf_data.get('wave_height_cm', 0)) & 0x3FF
    wave_thresh = int(surf_data.get('wave_threshold_cm', 100)) & 0x3FF
    speed = int(surf_data.get('wind_speed_mps', 0)) & 0x3FF
    wind_thresh = int(surf_data.get('wind_speed_threshold_knots', 15)) & 0x7F
    direction = int(surf_data.get('wind_direction_deg', 0)) & 0x3FF

    stale = surf_data.get('stale_data_warning', False)
    available = surf_data.get('data_available', True)
    quiet = surf_data.get('quiet_hours_active', False)
    off = surf_data.get('off_hours_active', False)

    # Pack surf data using C++
    surf_packed = message_wrapper.SurfData.pack_data(
        period, height, wave_thresh, speed, wind_thresh, direction,
        stale, available, quiet, off
    )

    # Create SurfData instance and calculate CRC
    surf_obj = message_wrapper.SurfData(surf_packed)
    surf_crc = surf_obj.calculate_crc()

    # Extract and process settings data
    # Convert latitude/longitude to float32 to match C++ float precision
    import struct
    theme = theme_to_enum(settings_data.get('led_theme', 'classic_surf'))
    brightness = int(settings_data.get('brightness_multiplier', 0.6) * 100) & 0x7F
    interval = int(settings_data.get('fetch_interval_ms', 13*60*1000)) & 0xFFFFF

    # Match C++ float precision by round-tripping through float32
    latitude_f32 = struct.unpack('f', struct.pack('f', float(settings_data.get('latitude', 0.0))))[0]
    longitude_f32 = struct.unpack('f', struct.pack('f', float(settings_data.get('longitude', 0.0))))[0]
    tz_offset = int(settings_data.get('tz_offset', 0))

    # Pack settings data using C++ (returns tuple of two 64-bit integers)
    settings_data1, settings_data2 = message_wrapper.SettingsData.pack(
        theme, brightness, interval, latitude_f32, longitude_f32, tz_offset
    )

    # Create SettingsData instance and calculate CRC
    settings_obj = message_wrapper.SettingsData(settings_data1, settings_data2)
    settings_crc = settings_obj.calculate_crc()

    # Assemble 26-byte packet
    packet = (
        surf_packed.to_bytes(8, byteorder='big') +
        bytes([surf_crc]) +
        settings_data1.to_bytes(8, byteorder='big') +
        settings_data2.to_bytes(8, byteorder='big') +
        bytes([settings_crc])
    )

    return packet
