import logging
import os
import sys
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from config import limiter, SURF_LOCATIONS
from utils.decorators import login_required, admin_required
from waitlist_db import get_all_waitlist_entries, get_recent_signups, get_waitlist_count
from forms import sanitize_input
from data_base import SessionLocal, User, Broadcast

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__)

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
