import logging
from datetime import datetime
import pytz
from data_base import LOCATION_TIMEZONES

logger = logging.getLogger(__name__)

def convert_wind_direction(degrees):
    """Convert wind direction from degrees to compass direction"""
    if degrees is None:
        return "--"
    
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

def is_quiet_hours(user_location, quiet_start_hour=22, quiet_end_hour=6):
    """
    Check if current time in user's location is within quiet hours.
    """
    if not user_location or user_location not in LOCATION_TIMEZONES:
        return False

    try:
        timezone_str = LOCATION_TIMEZONES[user_location]
        local_tz = pytz.timezone(timezone_str)
        current_time = datetime.now(local_tz)
        current_hour = current_time.hour

        if quiet_start_hour > quiet_end_hour:
            return current_hour >= quiet_start_hour or current_hour < quiet_end_hour
        else:
            return quiet_start_hour <= current_hour < quiet_end_hour

    except Exception as e:
        logger.warning(f"Error checking quiet hours for {user_location}: {e}")
        return False

# --- Context Module Functions ---

def get_core_context(user_data, conditions_data):
    """Core context - always included"""
    # Format current conditions
    if conditions_data:
        wave_height = f"{conditions_data.wave_height_m:.1f}m" if conditions_data.wave_height_m else "N/A"
        wave_period = f"{conditions_data.wave_period_s:.1f}s" if conditions_data.wave_period_s else "N/A"
        wind_speed = f"{conditions_data.wind_speed_mps:.1f} m/s ({conditions_data.wind_speed_mps * 1.94384:.1f} knots)" if conditions_data.wind_speed_mps else "N/A"
        wind_dir = convert_wind_direction(conditions_data.wind_direction_deg) if conditions_data.wind_direction_deg else "N/A"
        status = "Online"
    else:
        wave_height = wave_period = wind_speed = wind_dir = "N/A"
        status = "No data (offline or recently registered)"

    in_quiet_hours = is_quiet_hours(user_data.location)
    night_mode_status = "Active" if in_quiet_hours else "Inactive"

    return f"""**USER'S SURF LAMP DATA:**
- Location: {user_data.location}
- Wave Alert Threshold: {user_data.wave_threshold_m}m
- Wind Alert Threshold: {user_data.wind_threshold_knots} knots
- Current Theme: {user_data.theme if user_data.theme else 'classic_surf'}
- Lamp Status: {status}
- Night Mode: {night_mode_status}

**CURRENT SURF CONDITIONS FOR {user_data.location}:**
- Wave Height: {wave_height}
- Wave Period: {wave_period}
- Wind Speed: {wind_speed}
- Wind Direction: {wind_dir}

**HOW THE SURF LAMP WORKS:**
Three LED strips show real-time surf conditions:
- Left Strip (Wave Period): Brightness = period length (each LED ~2s)
- Middle Strip (Wind Speed): Color = wind direction, brightness = speed (each LED ~2-3 knots)
- Right Strip (Wave Height): Brightness = wave height (each LED ~0.33m)

**WIND DIRECTION COLORS:**
N=Green, NE=Green-Yellow, E=Yellow, SE=Yellow-Orange, S=Red, SW=Purple, W=Blue, NW=Cyan

**ALERTS:** Blinking = threshold exceeded (wave height > {user_data.wave_threshold_m}m OR wind > {user_data.wind_threshold_knots} knots)"""

def get_wifi_module():
    """WiFi setup and troubleshooting"""
    return """
**WIFI SETUP:**
- Blue LEDs = setup mode
- Connect to "SurfLamp-Setup" network (open network, no password)
- Configure at 192.168.4.1
- Must use 2.4GHz WiFi (NOT 5GHz)
- Red blinking = lost connection, auto-retry
- Reset: Press BOOT button 1 second OR unplug 10 seconds"""

def get_theme_module():
    """LED theme information"""
    return """
**LED THEMES:**
5 themes available: classic_surf, vibrant_mix, tropical_paradise, ocean_sunset, electric_vibes
- Change: Dashboard → "Configure" button in LED Colors row
- Updates within 13 minutes
- Affects overall palette, not wind direction colors"""

def get_night_mode_module():
    """Night mode details"""
    return """
**NIGHT MODE (10 PM - 6 AM):**
- Only TOP LED of each strip lit (ambient lighting)
- Threshold blinking disabled
- Automatic based on location timezone"""

def get_registration_module():
    """Arduino ID and registration"""
    return """
**ARDUINO ID & REGISTRATION:**
- Arduino ID: Unique device number on QR code/card in box
- Registration: Enter Arduino ID during account creation
- Links physical lamp to your dashboard account
- Updates every 13 minutes"""

def get_troubleshooting_module():
    """Common issues"""
    return """
**TROUBLESHOOTING:**
- No data: Recently registered, connection issue, or updating (13min cycle)
- All LEDs lit: Maximum conditions (check dashboard for values)
- One LED only: Night mode active
- Red blinking: WiFi lost
- Change settings: Use dashboard controls (location dropdown, threshold inputs)
- Location changes: Limited to 5/day"""

def detect_relevant_modules(user_message):
    """Detect which context modules are needed based on user's question"""
    message_lower = user_message.lower()
    modules = []

    # WiFi/Setup keywords
    if any(word in message_lower for word in ['wifi', 'setup', 'connect', 'network', '2.4', '5ghz', 'blue led', 'setup mode', 'reset', 'boot button']):
        modules.append('wifi')

    # Theme keywords
    if any(word in message_lower for word in ['theme', 'color', 'bright', 'dim', 'appearance', 'classic', 'vibrant', 'tropical', 'sunset', 'electric']):
        modules.append('theme')

    # Night mode keywords
    if any(word in message_lower for word in ['night', 'sleep', 'one led', 'single led', '10pm', '6am', 'dark', 'ambient']):
        modules.append('night_mode')

    # Registration keywords
    if any(word in message_lower for word in ['arduino id', 'register', 'registration', 'qr code', 'device number', 'link lamp', 'sign up']):
        modules.append('registration')

    # Troubleshooting keywords
    if any(word in message_lower for word in ['not working', 'problem', 'issue', 'broken', 'fix', 'error', 'offline', 'no data', 'help', "won't", "can't", "doesn't"]):
        modules.append('troubleshooting')

    return modules

def build_chat_context(user_data, conditions_data, user_message):
    """Build modular context based on user's specific question"""

    # Always include core context
    context_parts = [
        "You are a helpful assistant for the Surf Lamp system. Your role is to help users understand their surf lamp and surf conditions.",
        "",
        get_core_context(user_data, conditions_data)
    ]

    # Detect and add relevant modules
    relevant_modules = detect_relevant_modules(user_message)

    if 'wifi' in relevant_modules:
        context_parts.append(get_wifi_module())
    if 'theme' in relevant_modules:
        context_parts.append(get_theme_module())
    if 'night_mode' in relevant_modules:
        context_parts.append(get_night_mode_module())
    if 'registration' in relevant_modules:
        context_parts.append(get_registration_module())
    if 'troubleshooting' in relevant_modules:
        context_parts.append(get_troubleshooting_module())

    # Add role and guidelines
    context_parts.append("""
**YOUR ROLE:**
- Answer questions concisely (2-4 sentences unless more detail needed)
- Explain LED meanings and surf conditions
- Read-only: Direct users to dashboard controls for changes
- Base answers on user's specific data shown above""")

    return "\n".join(context_parts)
