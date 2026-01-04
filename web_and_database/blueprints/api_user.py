import logging
from flask import Blueprint, request, session, jsonify
from config import limiter, SURF_LOCATIONS
from utils.decorators import login_required
from utils.rate_limit import check_location_change_limit, record_location_change
from data_base import SessionLocal, User, update_user_location

logger = logging.getLogger(__name__)

bp = Blueprint('api_user', __name__)

@bp.route("/update-location", methods=['POST'])
@login_required
@limiter.limit("10/minute")
def update_location():
    """Update user's lamp location"""
    try:
        data = request.get_json()
        new_location = data.get('location')
        user_id = session.get('user_id')
        
        # Validate location
        if new_location not in SURF_LOCATIONS:
            return {'success': False, 'message': 'Invalid location selected'}, 400
        
        # Check rate limit
        if not check_location_change_limit(user_id):
            return {'success': False, 'message': "Maximum 5 location changes per day reached"}, 429
            
        # Record this change
        record_location_change(user_id)
        
        # Update location in database
        success, message = update_user_location(user_id, new_location)
        
        if success:
            # Update session
            session['user_location'] = new_location
            return {'success': True, 'message': 'Update success, data will update soon'}
        else:
            return {'success': False, 'message': message}, 500
            
    except Exception as e:
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-threshold", methods=['POST'])
@login_required
@limiter.limit("30/minute")
def update_threshold():
    try:
        data = request.get_json()
        threshold = float(data.get('threshold', 1.0))
        user_id = session.get('user_id')
        
        if threshold < 0.1 or threshold > 10.0:
            return {'success': False, 'message': 'Threshold must be between 0.1 and 10.0 meters'}, 400
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.wave_threshold_m = threshold
                db.commit()
                return {'success': True, 'message': 'Wave threshold updated successfully'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()
            
    except Exception as e:
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-wind-threshold", methods=['POST'])
@login_required
@limiter.limit("30/minute")
def update_wind_threshold():
    try:
        data = request.get_json()
        threshold = int(data.get('threshold', 22))
        user_id = session.get('user_id')
        
        if threshold < 1 or threshold > 25:
            return {'success': False, 'message': 'Wind threshold must be between 1 and 25 knots'}, 400
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.wind_threshold_knots = threshold
                db.commit()
                return {'success': True, 'message': 'Wind threshold updated successfully'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()
            
    except Exception as e:
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-off-times", methods=['POST'])
@login_required
@limiter.limit("30/minute")
def update_off_times():
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        user_id = session.get('user_id')

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.off_times_enabled = enabled
                if start_time:
                    user.off_time_start = start_time
                if end_time:
                    user.off_time_end = end_time
                db.commit()
                return {'success': True, 'message': 'Off-times updated successfully'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()

    except Exception as e:
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-theme", methods=['POST'])
@login_required
@limiter.limit("20/minute")
def update_theme():
    """Update user's LED color theme preference"""
    try:
        data = request.get_json()
        theme = data.get('theme')
        user_id = session.get('user_id')

        if theme not in ['day', 'dark']:
            return {'success': False, 'message': 'Invalid theme. Must be day or dark'}, 400

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.theme = theme
                db.commit()
                logger.info(f"✅ User {user.username} updated LED theme to: {theme}")
                return {'success': True, 'message': f'LED theme updated to {theme}'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error updating theme: {e}")
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-led-theme", methods=['POST'])
@login_required
def update_led_theme():
    """Update user's LED color theme to one of the predefined themes"""
    try:
        data = request.get_json()
        theme_id = data.get('theme_id')
        user_id = session.get('user_id')

        # Valid LED theme IDs - 5 themes with distinct colors (minimal red)
        valid_themes = [
            'classic_surf', 'vibrant_mix', 'tropical_paradise', 'ocean_sunset', 'electric_vibes'
        ]

        if theme_id not in valid_themes:
            return {'success': False, 'message': 'Invalid LED theme selected'}, 400

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.theme = theme_id
                db.commit()
                logger.info(f"✅ User {user.username} updated LED theme to: {theme_id}")
                return {'success': True, 'message': f'LED theme updated to {theme_id}'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error updating LED theme: {e}")
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-brightness", methods=['POST'])
@login_required
@limiter.limit("30/minute")
def update_brightness():
    """Update user's global brightness multiplier"""
    try:
        data = request.get_json()
        brightness = float(data.get('brightness'))
        user_id = session.get('user_id')

        # Validate brightness level (Low=0.007, Mid=0.4, High=1.0)
        valid_levels = [0.007, 0.4, 1.0]
        if brightness not in valid_levels:
            return {'success': False, 'message': 'Invalid brightness level. Must be 0.007, 0.4, or 1.0'}, 400

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.brightness_level = brightness
                db.commit()
                logger.info(f"✅ User {user.username} updated brightness to: {brightness}")
                return {'success': True, 'message': f'Brightness updated successfully'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error updating brightness: {e}")
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@bp.route("/update-unit-preference", methods=['POST'])
@login_required
@limiter.limit("30/minute")
def update_unit_preference():
    """Update user's wave height unit preference (meters or feet - wind always stays in knots)"""
    try:
        data = request.get_json()
        unit_preference = data.get('unit_preference')
        user_id = session.get('user_id')

        # Validate unit preference
        if unit_preference not in ['meters', 'feet']:
            return {'success': False, 'message': 'Invalid unit preference. Must be meters or feet'}, 400

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.preferred_output = unit_preference
                db.commit()
                logger.info(f"✅ User {user.username} updated unit preference to: {unit_preference}")
                return {'success': True, 'message': f'Unit preference updated to {unit_preference}'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error updating unit preference: {e}")
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500
