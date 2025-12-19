import logging
import time
import sys
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from data_base import SessionLocal, Lamp, CurrentConditions, User, ErrorReport
from utils.helpers import is_quiet_hours, is_off_hours

# Add processor path to import sunset calculator
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
processor_path = os.path.join(os.path.dirname(parent_dir), 'surf-lamp-processor')
sys.path.insert(0, processor_path)
from sunset_calculator import get_sunset_info

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
            # Find the lamp by arduino_id
            lamp = db.query(Lamp).filter(Lamp.arduino_id == arduino_id).first()
            
            if not lamp:
                logger.warning(f"⚠️  Arduino {arduino_id} not found in database")
                return {'success': False, 'message': f'Arduino {arduino_id} not found'}, 404

            # Update lamp timestamp (confirms delivery)
            lamp.last_updated = datetime.now(timezone.utc)
            logger.info(f"✅ Updated lamp {lamp.lamp_id} timestamp")
            
            # Commit all changes
            db.commit()
            
            logger.info(f"✅ Database updated successfully for Arduino {arduino_id}")
            logger.info(f"   Lamp ID: {lamp.lamp_id}, Timestamp updated: {lamp.last_updated}")
            
            # Return success response to Arduino
            response_data = {
                'success': True,
                'message': 'Callback processed successfully',
                'lamp_id': lamp.lamp_id,
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
        # Get lamp data for this Arduino
        db = SessionLocal()
        try:
            # Join to get current conditions for this Arduino
            result = db.query(Lamp, CurrentConditions, User).select_from(Lamp) \
                .outerjoin(CurrentConditions, Lamp.lamp_id == CurrentConditions.lamp_id) \
                .join(User, Lamp.user_id == User.user_id) \
                .filter(Lamp.arduino_id == arduino_id) \
                .first()
            
            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404
            
            lamp, conditions, user = result

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

            # If no conditions yet, return zeros (safe defaults)
            if not conditions:
                logger.info(f"ℹ️ No surf conditions yet for Arduino {arduino_id}, returning defaults")
                surf_data = {
                    'wave_height_cm': 0,
                    'wave_period_s': 0.0,
                    'wind_speed_mps': 0,
                    'wind_direction_deg': 0,
                    'wave_threshold_cm': int((user.wave_threshold_m or 1.0) * 100),
                    'wind_speed_threshold_knots': int(round(user.wind_threshold_knots or 22.0)),
                    'led_theme': user.theme or 'day',
                    'quiet_hours_active': quiet_hours_active,
                    'off_hours_active': off_hours_active,
                    'sunset_animation': sunset_info['sunset_trigger'],
                    'day_of_year': sunset_info['day_of_year'],
                    'last_updated': '1970-01-01T00:00:00Z',
                    'data_available': False
                }
            else:
                # Format data exactly like current POST format
                surf_data = {
                    'wave_height_cm': int(round((conditions.wave_height_m or 0) * 100)),
                    'wave_period_s': conditions.wave_period_s or 0.0,
                    'wind_speed_mps': int(round(conditions.wind_speed_mps or 0)),
                    'wind_direction_deg': conditions.wind_direction_deg or 0,
                    'wave_threshold_cm': int((user.wave_threshold_m or 1.0) * 100),
                    'wind_speed_threshold_knots': int(round(user.wind_threshold_knots or 22.0)),
                    'led_theme': user.theme or 'day',
                    'quiet_hours_active': quiet_hours_active,
                    'off_hours_active': off_hours_active,
                    'sunset_animation': sunset_info['sunset_trigger'],
                    'day_of_year': sunset_info['day_of_year'],
                    'last_updated': conditions.last_updated.isoformat() if conditions.last_updated else '1970-01-01T00:00:00Z',
                    'data_available': True
                }
            
            logger.info(f"✅ Returning surf data for Arduino {arduino_id}: wave={surf_data['wave_height_cm']}cm")
            return surf_data, 200
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting surf data for Arduino {arduino_id}: {e}")
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
            # Query all lamps with their current conditions
            results = db.query(Lamp, CurrentConditions).outerjoin(
                CurrentConditions, Lamp.lamp_id == CurrentConditions.lamp_id
            ).all()

            arduino_status = []
            for lamp, conditions in results:
                status_info = {
                    'arduino_id': lamp.arduino_id,
                    'lamp_id': lamp.lamp_id,
                    'last_updated': lamp.last_updated.isoformat() if lamp.last_updated else None,
                    'has_conditions': conditions is not None,
                    'conditions_updated': conditions.last_updated.isoformat() if conditions and conditions.last_updated else None
                }

                if conditions:
                    status_info.update({
                        'wave_height_m': conditions.wave_height_m,
                        'wave_period_s': conditions.wave_period_s,
                        'wind_speed_mps': conditions.wind_speed_mps,
                        'wind_direction_deg': conditions.wind_direction_deg
                    })

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
                    'lamp_id': report.lamp_id,
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
