'''
handles the data exchange between the flask app and the lamps
author: shahar nitzan
'''

import logging
import time
import sys
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, make_response
from data_base import SessionLocal, Arduino, Location, User, ErrorReport
from utils.helpers import is_quiet_hours, is_off_hours, get_current_tz_offset, get_sunset_info_cached, get_coordinates_cached
from utils.threshold_logic import calculate_effective_threshold
from config import BRIGHTNESS_LEVELS, STALE_DATA_THRESHOLD
from redis_manager import get_redis_client

# Add processor path to import sunset calculator
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
processor_path = os.path.join(os.path.dirname(parent_dir), 'surf-lamp-processor')
sys.path.insert(0, processor_path)
from sunset_calculator import get_sunset_info, LOCATION_COORDS
from binary_protocol import encode_v3_response

logger = logging.getLogger(__name__)

bp = Blueprint('api_arduino', __name__)


def get_clamped_fetch_interval_ms(arduino):
    """Get fetch interval in milliseconds, enforcing 7-minute minimum."""
    interval_minutes = (getattr(arduino, 'request_interval_minutes', 13) or 13)
    interval_minutes = max(interval_minutes, 7)  # Enforce 7-minute minimum
    return interval_minutes * 60 * 1000


def is_physical_device():
    """Check if request is from physical ESP32 hardware (vs dashboard)."""
    user_agent = request.headers.get('User-Agent', '')
    return 'ESP32' in user_agent


def record_heartbeat(arduino_id):
    """
    Records heartbeat in Redis (High Performance) or DB (Fallback).
    
    Strategy:
    1. Try Redis HSET (fast, O(1), cheap)
    2. Try Redis SETBIT (even faster, effectively 1 bit)
    3. If Redis unavailable, return False (caller may choose to update DB)
    """
    redis = get_redis_client()
    if redis:
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            # 1. Store exact timestamp in Hash
            redis.hset('arduino:last_seen', arduino_id, timestamp)
            # 2. Set bit in bitmap (The "One Bit" Optimization)
            # This allows checking 1M lamps in ~120KB of RAM
            redis.setbit('arduino:online_bitmap', arduino_id, 1)
            return True
        except Exception as e:
            logger.error(f"❌ Redis heartbeat failed for {arduino_id}: {e}")
    return False


def update_arduino_timestamp(arduino_id, is_physical):
    """Update Arduino's last poll timestamp if it's a physical device.

    Args:
        arduino_id: Arduino ID
        is_physical: True if ESP32 hardware, False if dashboard

    Returns:
        tuple: (arduino: Arduino object or None, error: str or None)
    """
    db = SessionLocal()
    try:
        arduino = db.query(Arduino).filter(Arduino.arduino_id == arduino_id).first()

        if not arduino:
            return None, f'Arduino {arduino_id} not found'

        if is_physical:
            # OPTIMIZATION: Use Redis for heartbeat if available
            if record_heartbeat(arduino_id):
                logger.info(f"⚡ Heartbeat recorded in Redis for {arduino_id}")
            else:
                # Redis unavailable: Log error but DO NOT write to DB to protect it
                logger.error(f"❌ Redis unavailable for heartbeat {arduino_id} - skipping DB update to prevent overload")
        else:
            logger.info(f"📊 Dashboard callback for arduino {arduino_id} (no timestamp update)")

        return arduino, None

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Database error: {e}")
        return None, str(e)
    finally:
        db.close()


def get_hours_status(location, user):
    """Check quiet/off hours status for a user's location."""
    quiet_hours_active = is_quiet_hours(
        location,
        getattr(user, 'quiet_times_enabled', True)
    )
    off_hours_active = is_off_hours(
        location,
        getattr(user, 'off_time_start', None),
        getattr(user, 'off_time_end', None),
        getattr(user, 'off_times_enabled', False)
    )
    return quiet_hours_active, off_hours_active


def calculate_thresholds(location, user):
    """Calculate effective wave and wind thresholds.

    Uses a server-side shim to simulate range-based alerts without modifying Arduino firmware.
    Arduino firmware has fixed logic: `if (current >= threshold) blink()`

    We dynamically manipulate the threshold sent to Arduino based on user's [min, max] range:
    - If current > max: Send threshold = 9999 (impossible value) → No blink
    - If min <= current <= max: Send threshold = min → Blinks
    - If current < min: Send threshold = min → No blink

    This allows range alerts (e.g., "alert only if waves 1m-3m") on old devices without firmware changes.
    """
    current_wind_knots = (location.wind_speed_mps * 1.944) if location.wind_speed_mps else None

    effective_wave_threshold_m = calculate_effective_threshold(
        current_value=location.wave_height_m,
        user_min=user.wave_threshold_m if user.wave_threshold_m is not None else 0.0,
        user_max=getattr(user, 'wave_threshold_max_m', None)
    )

    effective_wind_threshold_knots = calculate_effective_threshold(
        current_value=current_wind_knots,
        user_min=user.wind_threshold_knots or 22.0,
        user_max=getattr(user, 'wind_threshold_max_knots', None)
    )

    return effective_wave_threshold_m, effective_wind_threshold_knots


def get_arduino_with_location_and_user(db, arduino_id):
    """Query arduino with joined location and user data."""
    return db.query(Arduino, Location, User).select_from(Arduino) \
        .join(User, Arduino.user_id == User.user_id) \
        .join(Location, Arduino.location == Location.location) \
        .filter(Arduino.arduino_id == arduino_id) \
        .first()


def build_surf_data_v1_response(location, user, sunset_info, effective_wave_threshold_m, effective_wind_threshold_knots, quiet_hours_active, off_hours_active):
    """Build V1 response dict (server calculates sunset)."""
    # Check for stale data (more than 3 identical updates = ~45-60 mins)
    stale_warning = (getattr(location, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD

    return {
        'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
        'wave_period_s': location.wave_period_s or 0.0,
        'wind_speed_mps': int(round(location.wind_speed_mps or 0)),
        'wind_direction_deg': location.wind_direction_deg or 0,
        'wave_threshold_cm': int(effective_wave_threshold_m * 100),
        'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
        'led_theme': user.theme or 'day',
        'quiet_hours_active': quiet_hours_active,
        'off_hours_active': off_hours_active,
        'sunset_animation': sunset_info['sunset_trigger'],
        'day_of_year': sunset_info['day_of_year'],
        'brightness_multiplier': getattr(user, 'brightness_level', BRIGHTNESS_LEVELS['MID']),
        'last_updated': location.last_updated.isoformat() if location.last_updated else '1970-01-01T00:00:00Z',
        'data_available': bool(location.wave_height_m or location.wind_speed_mps),
        'stale_data_warning': stale_warning
    }


def build_surf_data_v2_response(location, location_data, tz_offset, arduino, user, effective_wave_threshold_m, effective_wind_threshold_knots, quiet_hours_active, off_hours_active, brightness_value):
    """Build V2 response dict (Arduino calculates sunset locally)."""
    # Check for stale data (more than 3 identical updates = ~45-60 mins)
    stale_warning = (getattr(location, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD

    return {
        'latitude': location_data['latitude'],
        'longitude': location_data['longitude'],
        'tz_offset': tz_offset,
        'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
        'wave_period_s': location.wave_period_s or 0.0,
        'wind_speed_mps': int(round(location.wind_speed_mps or 0)),
        'wind_direction_deg': location.wind_direction_deg or 0,
        'wave_threshold_cm': int(effective_wave_threshold_m * 100),
        'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
        'led_theme': user.theme or 'day',
        'quiet_hours_active': quiet_hours_active,
        'off_hours_active': off_hours_active,
        'brightness_multiplier': brightness_value,
        'fetch_interval_ms': get_clamped_fetch_interval_ms(arduino),
        'last_updated': location.last_updated.isoformat() if location.last_updated else '1970-01-01T00:00:00Z',
        'data_available': bool(location.wave_height_m or location.wind_speed_mps),
        'stale_data_warning': stale_warning
    }


@bp.route("/api/arduino/callback", methods=['POST'])
def handle_arduino_callback():
    """Handle callbacks from Arduino devices confirming surf data receipt."""
    try:
        # Validate input
        data = request.get_json()
        if not data:
            return {'success': False, 'message': 'No JSON data provided'}, 400

        arduino_id = data.get('arduino_id')
        if not arduino_id:
            return {'success': False, 'message': 'arduino_id is required'}, 400

        # Log callback
        data_received = data.get('data_received', False)
        local_ip = data.get('local_ip', 'unknown')
        logger.info(f"📥 Arduino Callback - ID: {arduino_id}, Data Received: {data_received}, IP: {local_ip}")

        # Update timestamp
        is_physical = is_physical_device()
        arduino, error = update_arduino_timestamp(arduino_id, is_physical)

        if error:
            logger.warning(f"⚠️ {error}")
            status_code = 404 if 'not found' in error else 500
            return {'success': False, 'message': error}, status_code

        logger.info(f"✅ Callback processed: Arduino {arduino_id}, Timestamp: {arduino.last_poll_time}")

        return {
            'success': True,
            'message': 'Callback processed successfully',
            'arduino_id': arduino_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, 200

    except Exception as e:
        logger.error(f"❌ Error processing Arduino callback: {e}")
        return {'success': False, 'message': 'Server error'}, 500

@bp.route("/api/arduino/<int:arduino_id>/data", methods=['GET'])
def get_arduino_data(arduino_id):
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (PULL mode)")

    try:
        # Get arduino data
        db = SessionLocal()
        try:
            result = get_arduino_with_location_and_user(db, arduino_id)

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404

            arduino, location, user = result

            # Check quiet/off hours status
            quiet_hours_active, off_hours_active = get_hours_status(user.location, user)

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {user.location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

            # Calculate sunset info for user's location (cached per location, expires every 24h)
            sunset_info = get_sunset_info_cached(user.location, get_sunset_info, trigger_window_minutes=15)
            logger.info(f"🌅 Sunset info: trigger={sunset_info['sunset_trigger']}, day={sunset_info['day_of_year']}")

            # Calculate effective thresholds
            effective_wave_threshold_m, effective_wind_threshold_knots = calculate_thresholds(location, user)

            # Build response
            surf_data = build_surf_data_v1_response(
                location, user, sunset_info,
                effective_wave_threshold_m, effective_wind_threshold_knots,
                quiet_hours_active, off_hours_active
            )

            # Update arduino timestamp only for physical devices (not dashboard views)
            is_physical = is_physical_device()
            if is_physical:
                if record_heartbeat(arduino_id):
                    logger.info(f"⚡ Heartbeat recorded in Redis for {arduino_id}")
                else:
                    logger.error(f"❌ Redis heartbeat failed for {arduino_id} (PULL V1)")
            else:
                logger.info(f"📊 Dashboard view for Arduino {arduino_id} (no timestamp update)")

            logger.info(f"✅ Returning surf data for Arduino {arduino_id}: wave={surf_data['wave_height_cm']}cm")
            return surf_data, 200

        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting surf data for Arduino {arduino_id}: {e}")
        return {'error': 'Server error'}, 500

@bp.route("/api/arduino/v2/<int:arduino_id>/data", methods=['GET'])
def get_arduino_surf_data_v2(arduino_id):
    """
    V2 endpoint: Returns surf data + location coordinates for autonomous sunset calculation.
    New devices use this endpoint to calculate sunset locally on ESP32.
    """
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (V2 - Autonomous Mode)")

    try:
        db = SessionLocal()
        try:
            result = get_arduino_with_location_and_user(db, arduino_id)

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404

            arduino, location, user = result

            # Get coordinates for user's location (cached per user, expires every 1 hour)
            location_data = get_coordinates_cached(user.user_id, user.location, LOCATION_COORDS)

            # Calculate current timezone offset (handles DST automatically)
            tz_offset = get_current_tz_offset(user.location)

            # Check quiet/off hours status
            quiet_hours_active, off_hours_active = get_hours_status(user.location, user)

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {user.location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

            # Quiet hours uses fixed safe brightness to avoid power supply minimum load issues
            # During normal hours, respect user's brightness preference
            brightness_value = BRIGHTNESS_LEVELS['MID'] if quiet_hours_active else getattr(user, 'brightness_level', BRIGHTNESS_LEVELS['MID'])

            # Calculate effective thresholds
            effective_wave_threshold_m, effective_wind_threshold_knots = calculate_thresholds(location, user)

            # Build response (NO sunset_animation or day_of_year - Arduino calculates locally)
            surf_data = build_surf_data_v2_response(
                location, location_data, tz_offset, arduino, user,
                effective_wave_threshold_m, effective_wind_threshold_knots,
                quiet_hours_active, off_hours_active, brightness_value
            )

            # Update arduino timestamp only for physical devices (not dashboard views)
            is_physical = is_physical_device()
            if is_physical:
                if record_heartbeat(arduino_id):
                    logger.info(f"⚡ Heartbeat recorded in Redis for {arduino_id} (V2)")
                else:
                    logger.error(f"❌ Redis heartbeat failed for {arduino_id} (PULL V2)")
            else:
                logger.info(f"📊 Dashboard view for Arduino {arduino_id} V2 endpoint (no timestamp update)")

            logger.info(f"✅ V2 data for Arduino {arduino_id}: lat={surf_data['latitude']}, lon={surf_data['longitude']}, tz_offset={tz_offset}")
            return surf_data, 200

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting V2 surf data for Arduino {arduino_id}: {e}")
        return {'error': 'Server error'}, 500

@bp.route("/api/arduino/v3/<int:arduino_id>/data", methods=['GET'])
def get_arduino_surf_data_v3(arduino_id):
    """
    V3 endpoint: Returns BINARY protocol data for new Arduinos (94% smaller than JSON)

    Backward compatible: Old Arduinos continue using v2 (JSON)
    New Arduinos use v3 (binary protocol with CRC-8 error detection)

    Response format:
    - 9 bytes: SurfData (8 data + 1 CRC)
    - 17 bytes: SettingsData (16 data + 1 CRC)
    Total: 26 bytes (vs ~450 bytes JSON)
    """
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (V3 - Binary Protocol)")

    try:
        db = SessionLocal()
        try:
            result = get_arduino_with_location_and_user(db, arduino_id)

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404

            arduino, location, user = result

            # Get coordinates for user's location
            location_data = get_coordinates_cached(user.user_id, user.location, LOCATION_COORDS)

            # Calculate current timezone offset
            tz_offset = get_current_tz_offset(user.location)

            # Check quiet/off hours status
            quiet_hours_active, off_hours_active = get_hours_status(user.location, user)

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {user.location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

            # Brightness handling
            brightness_value = BRIGHTNESS_LEVELS['MID'] if quiet_hours_active else getattr(user, 'brightness_level', BRIGHTNESS_LEVELS['MID'])

            # Calculate effective thresholds
            effective_wave_threshold_m, effective_wind_threshold_knots = calculate_thresholds(location, user)

            # Build surf data dict (for binary encoding)
            surf_data = {
                'wave_period_s': int(location.wave_period_s or 0),
                'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
                'wave_threshold_cm': int(effective_wave_threshold_m * 100),
                'wind_speed_mps': int(round(location.wind_speed_mps or 0)),
                'wind_speed_threshold_knots': int(round(effective_wind_threshold_knots)),
                'wind_direction_deg': location.wind_direction_deg or 0,
                'stale_data_warning': (getattr(location, 'consecutive_identical_updates', 0) or 0) > STALE_DATA_THRESHOLD,
                'data_available': bool(location.wave_height_m or location.wind_speed_mps),
                'quiet_hours_active': quiet_hours_active,
                'off_hours_active': off_hours_active
            }

            # Build settings data dict (for binary encoding)
            settings_data = {
                'led_theme': user.theme or 'classic_surf',
                'brightness_multiplier': brightness_value,
                'fetch_interval_ms': get_clamped_fetch_interval_ms(arduino),
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                'tz_offset': tz_offset
            }

            # Encode to binary protocol (26 bytes total)
            binary_data = encode_v3_response(surf_data, settings_data)

            # Update arduino timestamp only for physical devices
            is_physical = is_physical_device()
            if is_physical:
                if record_heartbeat(arduino_id):
                    logger.info(f"⚡ Heartbeat recorded in Redis for {arduino_id} (V3)")
                else:
                    logger.error(f"❌ Redis heartbeat failed for {arduino_id} (PULL V3)")
            else:
                logger.info(f"📊 Dashboard view for Arduino {arduino_id} V3 endpoint (no timestamp update)")

            logger.info(f"✅ V3 binary data for Arduino {arduino_id}: {len(binary_data)} bytes (wave={surf_data['wave_height_cm']}cm)")

            # Return binary data with correct Content-Type
            response = make_response(binary_data)
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Length'] = len(binary_data)
            return response

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting V3 binary surf data for Arduino {arduino_id}: {e}")
        return {'error': 'Server error'}, 500

@bp.route("/api/discovery/server", methods=['GET'])
def get_server_discovery():
    """
    Discovery endpoint: Returns current API server information
    """
    try:
        current_host = request.host
        
        discovery_info = {
            'api_server': current_host,
            'version': '1.0',
            'timestamp': int(time.time()),
            'endpoints': {
                'arduino_data': '/api/arduino/{arduino_id}/data',
                'status': '/api/arduino/status'
            }
        }
        
        logger.info(f"📡 Discovery request served: {current_host}")
        return discovery_info, 200
        
    except Exception as e:
        logger.error(f"❌ Discovery endpoint error: {e}")
        return {'error': 'Discovery unavailable'}, 500

@bp.route("/api/arduino/<int:arduino_id>/settings", methods=['GET'])
def get_arduino_settings(arduino_id):
    """
    PRIVATE ENDPOINT - User-specific settings (reserved for future scalability)

    Currently unused - V2 endpoint returns all data in one call.
    When scaling to many lamps, this endpoint will enable split caching:
    - Settings cached 1 hour (user preferences rarely change)
    - Conditions cached 13 min (fetched separately per location)
    Reduces redundant DB queries: 1M lamps at same location = 1M queries → 1 settings + 1 conditions query.

    Returns user preferences and thresholds for a specific arduino.

    This data changes infrequently (only when user modifies settings).
    Arduino should cache locally for 1 hour and only re-fetch when settings_version changes.

    Response includes:
    - Wave/wind thresholds (min/max)
    - LED theme
    - Brightness level
    - Quiet hours / off hours status
    - Location (tells arduino which /api/locations/{location}/conditions to call)
    - Coordinates + timezone for autonomous calculations

    Architecture:
    - Paired with /api/locations/{location}/conditions for split caching
    - Settings fetched every 60 minutes (or when user updates via server push notification)
    - Conditions fetched every 13 minutes from CDN
    - Arduino merges locally for efficiency
    """
    logger.info(f"⚙️ Settings requested for Arduino {arduino_id}")

    try:
        db = SessionLocal()
        try:
            # Query arduino with user data
            result = db.query(Arduino, User).select_from(Arduino) \
                .join(User, Arduino.user_id == User.user_id) \
                .filter(Arduino.arduino_id == arduino_id) \
                .first()

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404

            arduino, user = result

            # Check quiet/off hours status
            quiet_hours_active = is_quiet_hours(
                user.location,
                getattr(user, 'quiet_times_enabled', True)
            )
            off_hours_active = is_off_hours(
                user.location,
                getattr(user, 'off_time_start', None),
                getattr(user, 'off_time_end', None),
                getattr(user, 'off_times_enabled', False)
            )

            # Get location coordinates for autonomous calculations
            location_data = LOCATION_COORDS.get(user.location)
            if not location_data:
                logger.warning(f"⚠️ Location '{user.location}' not in LOCATION_COORDS")
                location_data = LOCATION_COORDS.get("Tel Aviv", {"latitude": 32.0853, "longitude": 34.7818})

            # Calculate timezone offset
            tz_offset = get_current_tz_offset(user.location)

            # Build settings response
            settings = {
                'arduino_id': arduino_id,
                'location': user.location,  # Tells arduino which /api/locations/{location}/conditions to call
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                'tz_offset': tz_offset,
                'wave_threshold_cm': int((user.wave_threshold_m or 0) * 100),
                'wave_threshold_max_cm': int((getattr(user, 'wave_threshold_max_m', None) or 999) * 100),
                'wind_speed_threshold_knots': int(user.wind_threshold_knots or 22),
                'wind_speed_threshold_max_knots': int(getattr(user, 'wind_threshold_max_knots', None) or 999),
                'led_theme': user.theme or 'day',
                'quiet_hours_active': quiet_hours_active,
                'off_hours_active': off_hours_active,
                'brightness_multiplier': getattr(user, 'brightness_level', BRIGHTNESS_LEVELS['MID']),
                'fetch_interval_ms': get_clamped_fetch_interval_ms(arduino),
                'settings_version': int(arduino.last_poll_time.timestamp()) if arduino.last_poll_time else 0
            }

            logger.info(f"✅ Returning settings for Arduino {arduino_id}: theme={settings['led_theme']}, location={settings['location']}")

            # Private data - don't cache publicly, but allow arduino to cache locally
            response = make_response(settings, 200)
            response.headers['Cache-Control'] = 'private, max-age=3600'  # 1 hour

            return response

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting settings for Arduino {arduino_id}: {e}")
        return {'error': 'Server error'}, 500


@bp.route("/api/arduino/status", methods=['GET'])
def arduino_status_overview():
    """
    Optional: Get overview of all Arduino devices and their last callback times.
    Merges data from DB and Redis (hot storage).
    """
    try:
        db = SessionLocal()
        try:
            # Query all arduinos with their location conditions
            results = db.query(Arduino, Location).join(
                Location, Arduino.location == Location.location
            ).all()

            # Fetch hot timestamps from Redis
            redis = get_redis_client()
            redis_timestamps = {}
            if redis:
                try:
                    # Returns dict {arduino_id: timestamp_str}
                    redis_timestamps = redis.hgetall('arduino:last_seen')
                except Exception as e:
                    logger.error(f"Failed to fetch Redis status: {e}")

            arduino_status = []
            for arduino, location in results:
                # Determine effective last poll time
                last_poll = arduino.last_poll_time
                
                # Check Redis for newer timestamp
                aid_str = str(arduino.arduino_id)
                if aid_str in redis_timestamps:
                    try:
                        ts = float(redis_timestamps[aid_str])
                        redis_dt = datetime.fromtimestamp(ts, timezone.utc)
                        # Use Redis time if it's newer or if DB is None
                        if last_poll is None or redis_dt > last_poll:
                            last_poll = redis_dt
                    except ValueError:
                        pass

                status_info = {
                    'arduino_id': arduino.arduino_id,
                    'location': arduino.location,
                    'last_poll_time': last_poll.isoformat() if last_poll else None,
                    'location_updated': location.last_updated.isoformat() if location.last_updated else None,
                    'wave_height_m': location.wave_height_m,
                    'wave_period_s': location.wave_period_s,
                    'wind_speed_mps': location.wind_speed_mps,
                    'wind_direction_deg': location.wind_direction_deg
                }

                arduino_status.append(status_info)

            return {
                'success': True,
                'arduino_count': len(arduino_status),
                'devices': arduino_status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 200

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting Arduino status overview: {e}")
        return {'success': False, 'message': str(e)}, 500

@bp.route("/api/error-reports")
def api_error_reports():
    """
    API endpoint for MCP tools to access error reports without authentication.
    Returns JSON array of all error reports from database.
    """
    try:
        db = SessionLocal()
        try:
            # Query all error reports ordered by timestamp (newest first)
            error_reports = db.query(ErrorReport).order_by(ErrorReport.timestamp.desc()).all()

            # Convert to list of dictionaries
            reports = []
            for report in error_reports:
                reports.append({
                    'id': report.id,
                    'timestamp': report.timestamp.isoformat() if report.timestamp else None,
                    'user_id': report.user_id,
                    'username': report.username,
                    'email': report.email,
                    'location': report.location,
                    'arduino_id': report.arduino_id,
                    'error_description': report.error_description,
                    'user_agent': report.user_agent
                })

            return jsonify({'reports': reports}), 200

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in api_error_reports endpoint: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
