import os
import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, session
from flask_limiter.util import get_remote_address
from config import limiter
from waitlist_db import add_to_waitlist, get_waitlist_count

logger = logging.getLogger(__name__)

bp = Blueprint('landing', __name__)

def get_landing_page_dir():
    # Go up 3 levels from blueprints/landing.py to get to project root
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root_dir, 'landing_page')

@bp.route("/")
def index():
    """
    Serves the landing page for new visitors.

    If the user is logged in, redirects to dashboard.
    """
    if 'user_email' in session:
        return redirect(url_for('dashboard.dashboard'))

    return send_from_directory(get_landing_page_dir(), 'index.html')

@bp.route("/styles.css")
def landing_styles():
    """Serve landing page CSS."""
    return send_from_directory(get_landing_page_dir(), 'styles.css')

@bp.route("/images/<path:filename>")
def landing_images(filename):
    """Serve landing page images."""
    images_dir = os.path.join(get_landing_page_dir(), 'images')
    return send_from_directory(images_dir, filename)

@bp.route("/teaser")
def teaser():
    """Minimalist anticipation teaser page."""
    return render_template('teaser.html')

@bp.route("/waitlist", methods=['GET'])
def waitlist_form():
    """Display the waitlist signup form."""
    total_signups = get_waitlist_count()
    return render_template('waitlist.html', total_signups=total_signups)

@bp.route("/waitlist/submit", methods=['POST'])
@limiter.limit("3 per hour")
def waitlist_submit():
    """Handle waitlist form submission."""
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip() or None

    # Basic validation
    if not all([first_name, last_name, email]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('landing.waitlist_form'))

    # Email format validation (basic)
    if '@' not in email or '.' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('landing.waitlist_form'))

    # Get request metadata for tracking
    ip_address = get_remote_address()
    user_agent = request.headers.get('User-Agent', '')

    # Add to database
    success, message, position = add_to_waitlist(
        first_name, last_name, email, phone, ip_address, user_agent
    )

    if success:
        logger.info(f"New waitlist signup: {email} (position {position})")
        return render_template('waitlist_confirmation.html',
                              first_name=first_name,
                              position=position)
    else:
        flash(message, 'error')
        return redirect(url_for('landing.waitlist_form'))

@bp.route("/privacy")
def privacy():
    """Display privacy policy page"""
    return render_template('privacy.html')
