import logging
import time
import sys
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from data_base import SessionLocal, Arduino, Location, User, ErrorReport
from utils.helpers import is_quiet_hours, is_off_hours, get_current_tz_offset
from config import BRIGHTNESS_LEVELS

# Add processor path to import sunset calculator
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
processor_path = os.path.join(os.path.dirname(parent_dir), 'surf-lamp-processor')
sys.path.insert(0, processor_path)
from sunset_calculator import get_sunset_info, LOCATION_COORDS

logger = logging.getLogger(__name__)

bp = Blueprint('api_arduino', __name__)

@bp.route("/api/arduino/callback", methods=['POST'])
def handle_arduino_callback():
    """
    Handle callbacks from Arduino devices confirming surf data receipt and processing.
    """
    try:
        # Get JSON data from Arduino
        data = request.get_json()
        
        if not data:
            logger.error("No JSON data received in Arduino callback")
            return {'success': False, 'message': 'No JSON data provided'}, 400
        
        # Extract required fields
        arduino_id = data.get('arduino_id')
        data_received = data.get('data_received', False)
        
        if not arduino_id:
            logger.error("Arduino callback missing arduino_id")
            return {'success': False, 'message': 'arduino_id is required'}, 400
        
        logger.info(f"📥 Arduino Callback - ID: {arduino_id}, Data Received: {data_received}")
        logger.info(f"   Arduino IP: {data.get('local_ip', 'unknown')}")
        
        # Update database with confirmed delivery
        db = SessionLocal()
        try:
            # Find the arduino
            arduino = db.query(Arduino).filter(Arduino.arduino_id == arduino_id).first()

            if not arduino:
                logger.warning(f"⚠️  Arduino {arduino_id} not found in database")
                return {'success': False, 'message': f'Arduino {arduino_id} not found'}, 404

            # Update arduino timestamp (confirms delivery)
            arduino.last_poll_time = datetime.now(timezone.utc)
            logger.info(f"✅ Updated arduino {arduino.arduino_id} timestamp")

            # Commit all changes
            db.commit()

            logger.info(f"✅ Database updated successfully for Arduino {arduino_id}")
            logger.info(f"   Timestamp updated: {arduino.last_poll_time}")

            # Return success response to Arduino
            response_data = {
                'success': True,
                'message': 'Callback processed successfully',
                'arduino_id': arduino_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return response_data, 200
            
        except Exception as db_error:
            db.rollback()
            logger.error(f"❌ Database error in Arduino callback: {db_error}")
            return {'success': False, 'message': f'Database error: {str(db_error)}'}, 500
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error processing Arduino callback: {e}")
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/api/arduino/<int:arduino_id>/data", methods=['GET'])
def get_arduino_surf_data(arduino_id):
    """
    New endpoint: Arduino pulls surf data from server
    This doesn't break existing push functionality
    """
    logger.info(f"📥 Arduino {arduino_id} requesting surf data (PULL mode)")
    
    try:
        # Get arduino data
        db = SessionLocal()
        try:
            # Join to get location conditions for this Arduino
            result = db.query(Arduino, Location, User).select_from(Arduino) \
                .join(User, Arduino.user_id == User.user_id) \
                .join(Location, Arduino.location == Location.location) \
                .filter(Arduino.arduino_id == arduino_id) \
                .first()

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404

            arduino, location, user = result

            # Check if current time is within quiet hours for this user's location
            quiet_hours_active = is_quiet_hours(user.location)

            # Check if current time is within user-defined off hours
            off_hours_active = is_off_hours(
                user.location,
                getattr(user, 'off_time_start', None),
                getattr(user, 'off_time_end', None),
                getattr(user, 'off_times_enabled', False)
            )

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {user.location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

            # Calculate sunset info for user's location
            sunset_info = get_sunset_info(user.location, trigger_window_minutes=15)
            logger.info(f"🌅 Sunset info: trigger={sunset_info['sunset_trigger']}, day={sunset_info['day_of_year']}")

            # Return location conditions data
            surf_data = {
                'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
                'wave_period_s': location.wave_period_s or 0.0,
                'wind_speed_mps': int(round(location.wind_speed_mps or 0)),
                'wind_direction_deg': location.wind_direction_deg or 0,
                'wave_threshold_cm': int((user.wave_threshold_m or 1.0) * 100),
                'wind_speed_threshold_knots': int(round(user.wind_threshold_knots or 22.0)),
                'led_theme': user.theme or 'day',
                'quiet_hours_active': quiet_hours_active,
                'off_hours_active': off_hours_active,
                'sunset_animation': sunset_info['sunset_trigger'],
                'day_of_year': sunset_info['day_of_year'],
                'brightness_multiplier': getattr(user, 'brightness_level', BRIGHTNESS_LEVELS['MID']),
                'last_updated': location.last_updated.isoformat() if location.last_updated else '1970-01-01T00:00:00Z',
                'data_available': bool(location.wave_height_m or location.wind_speed_mps)
            }

            # Update arduino timestamp to track when Arduino last pulled data
            arduino.last_poll_time = datetime.now(timezone.utc)
            db.commit()

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
            # Join to get location conditions for this Arduino
            result = db.query(Arduino, Location, User).select_from(Arduino) \
                .join(User, Arduino.user_id == User.user_id) \
                .join(Location, Arduino.location == Location.location) \
                .filter(Arduino.arduino_id == arduino_id) \
                .first()

            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404

            arduino, location, user = result

            # Get coordinates for user's location
            location_data = LOCATION_COORDS.get(user.location)
            if not location_data:
                logger.warning(f"⚠️ Location '{user.location}' not in LOCATION_COORDS, using Tel Aviv defaults")
                location_data = LOCATION_COORDS.get("Tel Aviv", {"latitude": 32.0853, "longitude": 34.7818})

            # Calculate current timezone offset (handles DST automatically)
            tz_offset = get_current_tz_offset(user.location)

            # Check quiet/off hours
            quiet_hours_active = is_quiet_hours(user.location)
            off_hours_active = is_off_hours(
                user.location,
                getattr(user, 'off_time_start', None),
                getattr(user, 'off_time_end', None),
                getattr(user, 'off_times_enabled', False)
            )

            if off_hours_active:
                logger.info(f"🔴 Off hours active for {user.location} - lamp turned off")
            elif quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

            # Quiet hours uses fixed safe brightness to avoid power supply minimum load issues
            # During normal hours, respect user's brightness preference
            brightness_value = BRIGHTNESS_LEVELS['MID'] if quiet_hours_active else getattr(user, 'brightness_level', BRIGHTNESS_LEVELS['MID'])

            # Build response (NO sunset_animation or day_of_year - Arduino calculates locally)
            surf_data = {
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                'tz_offset': tz_offset,
                'wave_height_cm': int(round((location.wave_height_m or 0) * 100)),
                'wave_period_s': location.wave_period_s or 0.0,
                'wind_speed_mps': int(round(location.wind_speed_mps or 0)),
                'wind_direction_deg': location.wind_direction_deg or 0,
                'wave_threshold_cm': int((user.wave_threshold_m or 1.0) * 100),
                'wind_speed_threshold_knots': int(round(user.wind_threshold_knots or 22.0)),
                'led_theme': user.theme or 'day',
                'quiet_hours_active': quiet_hours_active,
                'off_hours_active': off_hours_active,
                'brightness_multiplier': brightness_value,
                'last_updated': location.last_updated.isoformat() if location.last_updated else '1970-01-01T00:00:00Z',
                'data_available': bool(location.wave_height_m or location.wind_speed_mps)
            }

            # Update arduino timestamp to track when Arduino last pulled data
            arduino.last_poll_time = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"✅ V2 data for Arduino {arduino_id}: lat={surf_data['latitude']}, lon={surf_data['longitude']}, tz_offset={tz_offset}")
            return surf_data, 200

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting V2 surf data for Arduino {arduino_id}: {e}")
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

@bp.route("/api/arduino/status", methods=['GET'])
def arduino_status_overview():
    """
    Optional: Get overview of all Arduino devices and their last callback times.
    """
    try:
        db = SessionLocal()
        try:
            # Query all arduinos with their location conditions
            results = db.query(Arduino, Location).join(
                Location, Arduino.location == Location.location
            ).all()

            arduino_status = []
            for arduino, location in results:
                status_info = {
                    'arduino_id': arduino.arduino_id,
                    'location': arduino.location,
                    'last_poll_time': arduino.last_poll_time.isoformat() if arduino.last_poll_time else None,
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
