import logging
import os
import sys
import re
import requests
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from config import limiter, SURF_LOCATIONS
from utils.decorators import login_required, admin_required
from waitlist_db import get_all_waitlist_entries, get_recent_signups, get_waitlist_count
from forms import sanitize_input
from data_base import SessionLocal, User, Broadcast, Lamp, CurrentConditions
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__)

# Render API configuration
RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = 'srv-d3bddhogjchc73feqi8g'  # final-surf-lamp-web

def get_arduino_activity_from_logs():
    """
    Fetch Render logs and extract Arduino polling activity with timestamps.
    Returns dict mapping arduino_id -> last_seen_timestamp
    """
    if not RENDER_API_KEY:
        logger.error("RENDER_API_KEY not configured")
        return {}

    try:
        # Fetch recent logs from Render API
        headers = {'Authorization': f'Bearer {RENDER_API_KEY}'}
        response = requests.get(
            f'https://api.render.com/v1/services/{RENDER_SERVICE_ID}/logs',
            headers=headers,
            params={'limit': 1000},  # Get more logs to capture all devices
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Render API error: {response.status_code}")
            return {}

        logs = response.text
        arduino_activity = {}

        # Regex to match Arduino API requests: /api/arduino/{id}/data
        arduino_pattern = re.compile(r'/api/arduino/(?:v2/)?(\d+)/data')
        # Regex to extract timestamp from log line (Render format: "YYYY-MM-DD HH:MM:SS")
        timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})')

        for line in logs.split('\n'):
            # Only count actual Arduino devices (ESP32HTTPClient), not browser requests
            if '/api/arduino/' in line and '200' in line and 'ESP32HTTPClient' in line:
                arduino_match = arduino_pattern.search(line)
                timestamp_match = timestamp_pattern.search(line)

                if arduino_match and timestamp_match:
                    arduino_id = int(arduino_match.group(1))
                    timestamp_str = timestamp_match.group(1).replace(' ', 'T')

                    try:
                        # Parse timestamp (assume UTC)
                        log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                        # Keep the most recent timestamp for each Arduino
                        if arduino_id not in arduino_activity or log_time > arduino_activity[arduino_id]:
                            arduino_activity[arduino_id] = log_time
                    except ValueError as e:
                        logger.warning(f"Failed to parse timestamp: {timestamp_str} - {e}")
                        continue

        logger.info(f"Found activity for {len(arduino_activity)} Arduino devices in logs")
        return arduino_activity

    except Exception as e:
        logger.error(f"Failed to fetch Arduino activity from logs: {e}")
        return {}

@bp.route("/admin/waitlist")
@login_required
def admin_waitlist():
    """Admin dashboard to view all waitlist entries. Requires login."""
    # Check if user is admin (user_id = 1 is typical admin pattern)
    if session.get('user_id') != 1:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard.dashboard'))

    entries = get_all_waitlist_entries()
    recent_24h = get_recent_signups(hours=24)
    total_count = get_waitlist_count()

    return render_template('admin_waitlist.html',
                          entries=entries,
                          recent_24h=recent_24h,
                          total_count=total_count)

@bp.route("/admin/trigger-processor")
@login_required  # Only logged-in users can trigger
def trigger_processor():
    """Manually trigger the background processor once"""
    try:
        # Import the processor function
        # Need to find where surf-lamp-processor is relative to here.
        # blueprints/admin.py -> web_and_database -> root -> surf-lamp-processor
        # root is .../Git_Surf_Lamp_Agent
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.append(os.path.join(root_dir, 'surf-lamp-processor'))
        
        # We need to handle ImportError if the directory doesn't exist
        try:
            from background_processor import run_once
            # Run the processor once
            success = run_once()
            
            if success:
                flash('Background processor completed successfully! Check your dashboard for updated data.', 'success')
            else:
                flash('Background processor encountered errors. Check logs for details.', 'error')
        except ImportError:
             flash('Background processor module not found.', 'error')

    except Exception as e:
        flash(f'Error running processor: {str(e)}', 'error')
    
    return redirect(url_for('dashboard.dashboard'))

@bp.route('/admin/broadcast', methods=['GET'])
@admin_required
def admin_broadcast():
    """Admin page to create broadcast messages"""
    return render_template('admin_broadcast.html', locations=SURF_LOCATIONS)

@bp.route('/admin/broadcast/create', methods=['POST'])
@admin_required
@limiter.limit("10 per hour")
def create_broadcast():
    """Create a new broadcast message (admin only)"""

    message = request.json.get('message', '').strip()
    target_location = request.json.get('target_location')  # "all" or specific location

    # Validation
    if not message or len(message) > 500:
        return jsonify({'success': False, 'message': 'Invalid message (max 500 characters)'}), 400

    if target_location and target_location != 'all' and target_location not in SURF_LOCATIONS:
        return jsonify({'success': False, 'message': 'Invalid location'}), 400

    # Sanitize message
    message = sanitize_input(message)

    # Calculate expiry (2 hours from now)
    expires_at = datetime.utcnow() + timedelta(hours=2)

    # Create broadcast
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == session['user_email']).first()

        # Deactivate all previous broadcasts (new broadcast overrides all old ones)
        db.query(Broadcast).filter(Broadcast.is_active).update({'is_active': False})

        broadcast = Broadcast(
            admin_user_id=user.user_id,
            message=message,
            target_location=None if target_location == 'all' else target_location,
            expires_at=expires_at
        )
        db.add(broadcast)
        db.commit()

        logger.info(f"📢 Admin {user.username} created broadcast: {message[:50]}... (location: {target_location})")
        return jsonify({'success': True, 'message': 'Broadcast sent!'})
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create broadcast: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        db.close()

@bp.route('/api/broadcasts', methods=['GET'])
@login_required
def get_active_broadcasts():
    """Fetch active broadcasts for current user's location"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == session['user_email']).first()
        if not user:
            return jsonify({'broadcasts': []})

        now = datetime.utcnow()

        # Get broadcasts: (not expired) AND (all users OR user's location)
        broadcasts = db.query(Broadcast).filter(
            Broadcast.is_active,
            Broadcast.expires_at > now,
            (Broadcast.target_location.is_(None)) | (Broadcast.target_location == user.location)
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

@bp.route('/admin/arduino-monitor')
@login_required
def arduino_monitor():
    """Arduino monitoring dashboard showing device connectivity status"""
    return render_template('arduino_monitor.html')

@bp.route('/api/admin/arduino-status')
@login_required
def arduino_status_api():
    """API endpoint returning Arduino device status based on actual polling activity from logs"""
    db = SessionLocal()
    try:
        # Get registered Arduino IDs from database
        lamps = db.query(Lamp).filter(Lamp.arduino_id.isnot(None)).all()

        # Get actual Arduino polling activity from Render logs
        arduino_activity = get_arduino_activity_from_logs()

        now = datetime.utcnow()
        devices = []

        for lamp in lamps:
            arduino_id = lamp.arduino_id

            # Check if this Arduino has recent polling activity
            if arduino_id in arduino_activity:
                last_seen = arduino_activity[arduino_id]

                # Make last_seen timezone-aware if needed
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=None)

                time_diff = (now - last_seen).total_seconds()
                minutes_ago = int(time_diff / 60)

                # Classify status based on actual polling time
                if minutes_ago < 15:
                    status = 'active'
                    status_text = f'{minutes_ago} min ago' if minutes_ago > 0 else 'Just now'
                elif minutes_ago < 60:
                    status = 'stale'
                    status_text = f'{minutes_ago} min ago'
                else:
                    hours_ago = int(minutes_ago / 60)
                    if hours_ago < 48:
                        status = 'offline'
                        status_text = f'{hours_ago} hour{"s" if hours_ago > 1 else ""} ago'
                    else:
                        days_ago = int(hours_ago / 24)
                        status = 'offline'
                        status_text = f'{days_ago} day{"s" if days_ago > 1 else ""} ago'

                last_updated = last_seen.isoformat()
            else:
                # No polling activity found in logs
                status = 'never'
                status_text = 'No recent activity'
                last_updated = None

            devices.append({
                'arduino_id': arduino_id,
                'lamp_id': lamp.lamp_id,
                'status': status,
                'status_text': status_text,
                'last_updated': last_updated
            })

        # Sort by status priority (active -> stale -> offline -> never), then by arduino_id descending
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
