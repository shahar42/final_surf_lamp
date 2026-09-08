"""
C++ Binary Encoder for Surf Lamp V3 API

Uses C++ message_wrapper module for encoding (12.5x faster than Python).
Drop-in replacement for binary_protocol.encode_v3_response().
"""

import message_wrapper
from typing import Dict

# Wire field widths, from esp_Server_encoding.hpp (single source of truth for
# the layout). If a width changes there, change it here and in the firmware.
FIELD_MAX_PERIOD = 0x3F            # 6 bits, seconds
FIELD_MAX_HEIGHT_CM = 0x3FF        # 10 bits
FIELD_MAX_WAVE_THRESH_CM = 0x3FF   # 10 bits
FIELD_MAX_WIND_MPS = 0x3FF         # 10 bits
FIELD_MAX_WIND_THRESH_KN = 0x7F    # 7 bits
FIELD_MAX_DIRECTION = 0x3FF        # 10 bits, degrees
FIELD_MAX_BRIGHTNESS_PCT = 0x7F    # 7 bits
FIELD_MAX_INTERVAL_MS = 0xFFFFF    # 20 bits (~17.5 minutes)


def _clamp(value, maximum: int, minimum: int = 0) -> int:
    """Truncate to int and saturate into [minimum, maximum]."""
    value = int(value)
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


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

    # Extract and SATURATE surf data to each field's wire width.
    # Saturating (not masking) matters: the threshold shim sends 9999 as an
    # "impossible" threshold when the reading is above the user's max. Masked
    # with & 0x7F that becomes 9999 % 128 = 15 knots, which would make the lamp
    # blink in exactly the case it must stay quiet. A saturated field maximum
    # is still unreachable by any real reading, so the sentinel keeps working.
    period = _clamp(surf_data.get('wave_period_s', 0), FIELD_MAX_PERIOD)
    height = _clamp(surf_data.get('wave_height_cm', 0), FIELD_MAX_HEIGHT_CM)
    wave_thresh = _clamp(surf_data.get('wave_threshold_cm', 100), FIELD_MAX_WAVE_THRESH_CM)
    speed = _clamp(surf_data.get('wind_speed_mps', 0), FIELD_MAX_WIND_MPS)
    wind_thresh = _clamp(surf_data.get('wind_speed_threshold_knots', 15), FIELD_MAX_WIND_THRESH_KN)
    direction = _clamp(surf_data.get('wind_direction_deg', 0), FIELD_MAX_DIRECTION)

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
    brightness = _clamp(settings_data.get('brightness_multiplier', 0.6) * 100, FIELD_MAX_BRIGHTNESS_PCT)
    # 20-bit field: anything above ~17.5 min saturates rather than wrapping to
    # a tiny interval that would make the lamp hammer the server.
    interval = _clamp(settings_data.get('fetch_interval_ms', 13*60*1000), FIELD_MAX_INTERVAL_MS)

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
