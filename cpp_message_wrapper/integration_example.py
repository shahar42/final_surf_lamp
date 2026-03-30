"""
Integration Example: Using C++ Message Parser in Surf Lamp

This demonstrates how to use the C++ message_wrapper module
instead of the Python binary_protocol parser.
"""

import message_wrapper
from typing import Optional, Dict

# Global parser instance (thread-safe via atomic counters)
_cpp_parser = message_wrapper.MessageHandler()


def parse_v3_message_cpp(raw_bytes: bytes) -> Optional[Dict]:
    """
    Parse V3 binary message using C++ parser.

    This is a drop-in replacement for the Python binary_protocol parser.

    Args:
        raw_bytes: 26-byte binary message from Arduino

    Returns:
        Dict with surf and settings data, or None if validation fails
    """
    # Parse using C++ (fast, shared_ptr allocation)
    msg = _cpp_parser.parse(list(raw_bytes))

    if msg is None:
        # Validation failed
        return None

    # Convert C++ message to Python dict (same format as Python parser)
    return {
        'surf': {
            'wave_period_s': msg.surf.get_wave_period(),
            'wave_height_cm': msg.surf.get_wave_height(),
            'wave_threshold_cm': msg.surf.get_wave_threshold(),
            'wind_speed_mps': msg.surf.get_wind_speed(),
            'wind_speed_threshold_knots': msg.surf.get_wind_threshold(),
            'wind_direction_deg': msg.surf.get_wind_direction(),
            'stale_data_warning': msg.surf.get_stale_data(),
            'data_available': msg.surf.get_data_available(),
            'quiet_hours_active': msg.surf.get_quiet_hours(),
            'off_hours_active': msg.surf.get_off_hours(),
        },
        'settings': {
            'led_theme': {
                0: 'classic_surf',
                1: 'vibrant_mix',
                2: 'tropical_paradise',
                3: 'ocean_sunset',
                4: 'electric_vibes',
            }[msg.settings.get_led_theme()],
            'brightness_multiplier': msg.settings.get_brightness() / 100.0,
            'fetch_interval_ms': msg.settings.get_fetch_interval_ms(),
            'latitude': msg.settings.get_latitude(),
            'longitude': msg.settings.get_longitude(),
            'tz_offset': msg.settings.get_tz_offset(),
        },
        'received_at': msg.received_at,
    }


def get_parser_stats() -> Dict:
    """Get parser statistics"""
    return {
        'total_parsed': _cpp_parser.get_total_parsed(),
        'validation_failures': _cpp_parser.get_validation_failures(),
    }


# ============================================================================
# USAGE IN SURF LAMP BACKEND
# ============================================================================
#
# In web_and_database/blueprints/api_arduino.py or similar:
#
# from cpp_message_wrapper.integration_example import parse_v3_message_cpp
#
# @app.route('/api/arduino/update', methods=['POST'])
# def handle_arduino_update():
#     raw_bytes = request.get_data()  # 26 bytes from Arduino
#
#     # Parse using C++ (no copying, shared_ptr)
#     parsed = parse_v3_message_cpp(raw_bytes)
#
#     if parsed is None:
#         return {'error': 'Invalid message'}, 400
#
#     # Use parsed data...
#     logger.log(parsed)
#     database.store(parsed)
#     broadcaster.send(parsed)
#
#     return {'status': 'ok'}
