import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from config import limiter, SURF_LOCATIONS, STALE_DATA_THRESHOLD
from shared_config import WAVE_STATS_REFRESH_SECONDS
from security_config import SecurityConfig
from utils.decorators import login_required, admin_required
from utils.sorter import sort_by_wave_height
from forms import sanitize_input
from data_base import SessionLocal, User, Broadcast, BroadcastDismissal, Arduino, Location
from sqlalchemy.orm import joinedload
from blueprints.notifications import trigger_push_broadcast
from redis_manager import get_redis_client

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__)

def get_broadcast_expiry(requested_duration):
    """Calculate broadcast expiry time based on requested duration.

    Args:
        requested_duration: Duration in hours (2, 5, or 10)

    Returns:
        datetime: Expiry time in UTC
    """
    ALLOWED_DURATIONS = {
        2: timedelta(hours=2),
        5: timedelta(hours=5),
        10: timedelta(hours=10)
    }

    try:
        duration_hours = int(requested_duration) if requested_duration else 2
    except (ValueError, TypeError):
        duration_hours = 2

    expiry_delta = ALLOWED_DURATIONS.get(duration_hours, timedelta(hours=2))
    return datetime.utcnow() + expiry_delta


def get_device_status(last_poll_time, now):
    """Calculate device status and formatted status text based on last poll time.

    Args:
        last_poll_time: Datetime of last poll (may have timezone info)
        now: Current UTC datetime

    Returns:
        tuple: (status: str, status_text: str, last_updated: str or None)
    """
    if not last_poll_time:
        return 'never', 'Never connected', None

    # Remove timezone info if present
    if last_poll_time.tzinfo is not None:
        last_poll_time = last_poll_time.replace(tzinfo=None)

    # Calculate time difference
    time_diff = (now - last_poll_time).total_seconds()
    minutes_ago = int(time_diff / 60)

    # Determine status
    if minutes_ago < 15:
        status = 'active'
        status_text = f'{minutes_ago} min ago' if minutes_ago > 0 else 'Just now'
    elif minutes_ago < 60:
        status = 'stale'
        status_text = f'{minutes_ago} min ago'
    else:
        status = 'offline'
        hours_ago = int(minutes_ago / 60)
        if hours_ago < 48:
            status_text = f'{hours_ago} hour{"s" if hours_ago > 1 else ""} ago'
        else:
            days_ago = int(hours_ago / 24)
            status_text = f'{days_ago} day{"s" if days_ago > 1 else ""} ago'

    return status, status_text, last_poll_time.isoformat()


def save_broadcast(user_id, username, message, target_location, expires_at):
    """Save broadcast to database and trigger push notifications.

    Args:
        user_id: Admin user ID
        username: Admin username
        message: Broadcast message
        target_location: Target location (None for all)
        expires_at: Expiry datetime

    Returns:
        tuple: (success: bool, error_msg: str or None)
    """
    db = SessionLocal()
    try:
        # Deactivate all previous broadcasts
        db.query(Broadcast).filter(Broadcast.is_active).update({'is_active': False})

        # Create and save new broadcast
        broadcast = Broadcast(
            admin_user_id=user_id,
            message=message,
            target_location=target_location,
            expires_at=expires_at
        )
        db.add(broadcast)
        db.commit()

        # Trigger push notifications
        try:
            pushed_count = trigger_push_broadcast(message, target_location=target_location)
            logger.info(f"🚀 Push notification sent to {pushed_count} devices")
        except Exception as e:
            logger.error(f"⚠️ Push notification failed: {e}")

        logger.info(f"📢 Admin {username} created broadcast: {message[:50]}... (location: {target_location})")
        return True, None
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create broadcast: {e}")
        return False, str(e)
    finally:
        db.close()

@bp.route('/admin/broadcast', methods=['GET'])
@admin_required
def admin_broadcast():
    """Admin page to create broadcast messages"""
    return render_template('admin_broadcast.html', locations=SURF_LOCATIONS)

@bp.route('/admin/broadcast/create', methods=['POST'])
@admin_required
@limiter.limit(lambda: SecurityConfig.RATE_LIMITS['admin_create_broadcast'])
def create_broadcast():
    """Create a new broadcast message (admin only)"""
    message = request.json.get('message', '').strip()
    target_location = request.json.get('target_location')

    # Validation
    if not message or len(message) > SecurityConfig.MAX_BROADCAST_MESSAGE_LENGTH:
        return jsonify({'success': False, 'message': f'Invalid message (max {SecurityConfig.MAX_BROADCAST_MESSAGE_LENGTH} characters)'}), 400

    if target_location and target_location != 'all' and target_location not in SURF_LOCATIONS:
        return jsonify({'success': False, 'message': 'Invalid location'}), 400

    # Prepare data
    message = sanitize_input(message)
    expires_at = get_broadcast_expiry(request.json.get('duration'))
    target_location = None if target_location == 'all' else target_location

    # Get user
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == session['user_email']).first()
    finally:
        db.close()

    # Save broadcast
    success, error = save_broadcast(user.user_id, user.username, message, target_location, expires_at)
    if success:
        return jsonify({'success': True, 'message': 'Broadcast sent!'})
    else:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@bp.route('/api/broadcasts', methods=['GET'])
@login_required
def get_active_broadcasts():
    """Fetch active broadcasts for current user's location, excluding dismissed ones"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == session['user_email']).first()
        if not user:
            return jsonify({'broadcasts': []})

        now = datetime.utcnow()

        # Get dismissed broadcast IDs for this user
        dismissed_ids = db.query(BroadcastDismissal.broadcast_id).filter(
            BroadcastDismissal.user_id == user.user_id
        ).all()
        dismissed_ids = [d[0] for d in dismissed_ids]

        broadcasts = db.query(Broadcast).filter(
            Broadcast.is_active,
            Broadcast.expires_at > now,
            (Broadcast.target_location.is_(None)) | (Broadcast.target_location == user.location),
            ~Broadcast.broadcast_id.in_(dismissed_ids) if dismissed_ids else True
        ).order_by(Broadcast.created_at.desc()).all()

        return jsonify({
            'broadcasts': [{
                'id': b.broadcast_id,
                'message': b.message,
                'created_at': b.created_at.isoformat()
            } for b in broadcasts]
        })
    finally:
        db.close()

@bp.route('/api/broadcasts/<int:broadcast_id>/dismiss', methods=['POST'])
@login_required
def dismiss_broadcast(broadcast_id):
    """Mark a broadcast as dismissed for the current user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == session['user_email']).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Check if broadcast exists
        broadcast = db.query(Broadcast).filter(Broadcast.broadcast_id == broadcast_id).first()
        if not broadcast:
            return jsonify({'success': False, 'message': 'Broadcast not found'}), 404

        # Check if already dismissed
        existing = db.query(BroadcastDismissal).filter(
            BroadcastDismissal.user_id == user.user_id,
            BroadcastDismissal.broadcast_id == broadcast_id
        ).first()

        if existing:
            return jsonify({'success': True, 'message': 'Already dismissed'})

        # Create dismissal record
        dismissal = BroadcastDismissal(user_id=user.user_id, broadcast_id=broadcast_id)
        db.add(dismissal)
        db.commit()

        return jsonify({'success': True, 'message': 'Broadcast dismissed'})
    except Exception as e:
        db.rollback()
        logger.error(f"Error dismissing broadcast: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        db.close()

@bp.route('/admin/arduino-monitor')
@login_required
@admin_required
def arduino_monitor():
    """Arduino monitoring dashboard showing device connectivity status"""
    return render_template('arduino_monitor.html')

@bp.route('/api/admin/arduino-status')
@login_required
def arduino_status_api():
    """API endpoint returning Arduino device status merging DB and Redis (hot) timestamps"""
    db = SessionLocal()
    try:
        results = db.query(Arduino, User, Location).join(User, Arduino.user_id == User.user_id).join(Location, Arduino.location == Location.location).all()

        # Fetch hot timestamps from Redis
        redis = get_redis_client()
        redis_timestamps = {}
        if redis:
            try:
                redis_timestamps = redis.hgetall('arduino:last_seen')
            except Exception as e:
                logger.error(f"Failed to fetch Redis status for admin: {e}")

        now = datetime.utcnow()
        devices = []

        for arduino, user, location in results:
            # Determine effective last poll time (Hot source: Redis > Cold source: DB)
            last_poll = arduino.last_poll_time
            aid_str = str(arduino.arduino_id)
            if aid_str in redis_timestamps:
                try:
                    ts = float(redis_timestamps[aid_str])
                    redis_dt = datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None) # Keep naive for DB comparison
                    if last_poll is None or redis_dt > last_poll:
                        last_poll = redis_dt
                except (ValueError, TypeError):
                    pass

            status, status_text, last_updated = get_device_status(last_poll, now)
            
            # Determine data staleness
            staleness_warning = False
            staleness_text = ""
            consecutive = location.consecutive_identical_updates if hasattr(location, 'consecutive_identical_updates') else 0
            if consecutive and consecutive > STALE_DATA_THRESHOLD:
                staleness_warning = True
                staleness_text = f"Stale Data ({consecutive} identical fetches)"
            
            devices.append({
                'arduino_id': arduino.arduino_id,
                'location': arduino.location,
                'username': user.username,
                'status': status,
                'status_text': status_text,
                'last_updated': last_updated,
                'staleness_warning': staleness_warning,
                'staleness_text': staleness_text,
                'consecutive_updates': consecutive,
                'last_value_change': location.last_value_change.isoformat() if hasattr(location, 'last_value_change') and location.last_value_change else None
            })

        # Sort by status priority, then by arduino ID
        status_priority = {'active': 0, 'stale': 1, 'offline': 2, 'never': 3}
        devices.sort(key=lambda x: (status_priority[x['status']], -x['arduino_id']))

        return jsonify({
            'success': True,
            'timestamp': now.isoformat(),
            'devices': devices,
            'summary': {
                'total': len(devices),
                'active': sum(1 for d in devices if d['status'] == 'active'),
                'stale': sum(1 for d in devices if d['status'] == 'stale'),
                'offline': sum(1 for d in devices if d['status'] == 'offline'),
                'never': sum(1 for d in devices if d['status'] == 'never')
            }
        })
    except Exception as e:
        logger.error(f"❌ Arduino status API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
    
    @bp.route('/admin/stats')
    @login_required
    @admin_required
    def admin_stats():
        """Admin statistics page showing ranked surf conditions across all locations."""
        db = SessionLocal()
        try:
            locations = db.query(Location).all()
            
            # Prepare data for C-based sorting: (location_name, wave_height)
            sort_data = []
            for loc in locations:
                height = loc.wave_height_m if loc.wave_height_m is not None else 0.0
                sort_data.append((loc.location, height))
                
            # Use our high-performance C merge sort!
            sorted_results = sort_by_wave_height(sort_data)
            
            # Create a mapping for easy lookup of other fields
            loc_map = {loc.location: loc for loc in locations}
            
            ranked_locations = []
            for name, height in sorted_results:
                loc = loc_map[name]
                ranked_locations.append({
                    'name': name,
                    'wave_height': height,
                    'wave_period': loc.wave_period_s,
                    'wind_speed': loc.wind_speed_mps,
                    'wind_direction': loc.wind_direction_deg,
                    'last_updated': loc.last_updated
                })
                
            return render_template(
                'admin_stats.html', 
                locations=ranked_locations,
                refresh_interval=WAVE_STATS_REFRESH_SECONDS
            )
        except Exception as e:
            logger.error(f"Error loading admin stats: {e}")
            flash("Error loading statistics.", "error")
            return redirect(url_for('dashboard.dashboard'))
        finally:
            db.close()
    