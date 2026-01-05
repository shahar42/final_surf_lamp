import os
import logging
import markdown
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from config import SURF_LOCATIONS, BRIGHTNESS_LEVELS
from utils.decorators import login_required
from data_base import get_user_lamp_data

logger = logging.getLogger(__name__)

bp = Blueprint('dashboard', __name__)

@bp.route("/dashboard")
@login_required
def dashboard():
    """
    Displays the user's personalized dashboard.
    """
    user_email = session.get('user_email')

    # Get user, arduinos, and location data
    user, arduinos, location = get_user_lamp_data(user_email)

    if not user:
        flash('Error loading your data. Please contact support.', 'error')
        return redirect(url_for('auth.login'))

    # Prepare data for template
    dashboard_data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'location': user.location,
            'theme': user.theme,
            'preferred_output': user.preferred_output,
            'wave_threshold_m': user.wave_threshold_m or 1.0,
            'wind_threshold_knots': user.wind_threshold_knots or 22.0,
            'is_admin': getattr(user, 'is_admin', False),
            'brightness_level': getattr(user, 'brightness_level', 0.4),
            'off_times_enabled': getattr(user, 'off_times_enabled', False),
            'off_time_start': getattr(user, 'off_time_start', None),
            'off_time_end': getattr(user, 'off_time_end', None)
        },
        'arduinos': [
            {
                'arduino_id': arduino.arduino_id,
                'location': arduino.location,
                'last_poll_time': arduino.last_poll_time
            }
            for arduino in arduinos
        ],
        'conditions': None
    }

    # Add surf conditions for user's default location if available
    if location:
        dashboard_data['conditions'] = {
            'wave_height_m': location.wave_height_m,
            'wave_period_s': location.wave_period_s,
            'wind_speed_mps': location.wind_speed_mps,
            'wind_direction_deg': location.wind_direction_deg,
            'last_updated': location.last_updated
        }

    # Check if off hours feature is enabled via env var
    off_hours_feature_enabled = os.getenv('OFF_HOURS_FEATURE_ENABLED', 'false').lower() == 'true'

    return render_template('dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS, off_hours_feature_enabled=off_hours_feature_enabled, brightness_levels=BRIGHTNESS_LEVELS)

@bp.route("/dashboard/<view_type>")
@login_required
def dashboard_view(view_type):
    """
    Displays the user's personalized dashboard with a specific view.
    """
    user_email = session.get('user_email')

    user, arduinos, location = get_user_lamp_data(user_email)

    if not user:
        flash('Error loading your data. Please contact support.', 'error')
        return redirect(url_for('auth.login'))

    dashboard_data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'location': user.location,
            'theme': user.theme,
            'preferred_output': user.preferred_output,
            'wave_threshold_m': user.wave_threshold_m or 1.0,
            'wind_threshold_knots': user.wind_threshold_knots or 22.0,
            'is_admin': getattr(user, 'is_admin', False)
        },
        'arduinos': [
            {
                'arduino_id': arduino.arduino_id,
                'location': arduino.location,
                'last_poll_time': arduino.last_poll_time
            }
            for arduino in arduinos
        ],
        'conditions': None
    }

    if location:
        dashboard_data['conditions'] = {
            'wave_height_m': location.wave_height_m,
            'wave_period_s': location.wave_period_s,
            'wind_speed_mps': location.wind_speed_mps,
            'wind_direction_deg': location.wind_direction_deg,
            'last_updated': location.last_updated
        }
    
    if view_type == 'experimental':
        return render_template('experimental_dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS, brightness_levels=BRIGHTNESS_LEVELS)
    else:
        return render_template('dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS, brightness_levels=BRIGHTNESS_LEVELS)

@bp.route("/themes")
@login_required
def themes_page():
    """
    Displays the LED theme configuration page.
    """
    user_email = session.get('user_email')
    user, lamp, conditions = get_user_lamp_data(user_email)

    if not user or not lamp:
        flash('Error loading your lamp data. Please contact support.', 'error')
        return redirect(url_for('auth.login'))

    user_data = {
        'user': {
            'username': user.username,
            'theme': user.theme or 'classic_surf'
        }
    }

    return render_template('themes.html', data=user_data)

@bp.route("/wifi-setup-guide")
@login_required
def wifi_setup_guide():
    """
    Display WiFi setup instructions for configuring lamp WiFi connection.
    """
    try:
        # Read markdown file from parent directory (web_and_database)
        markdown_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Wifi_Config_instructions.md')
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        html_content = markdown.markdown(markdown_content, extensions=['extra', 'nl2br'])

        return render_template('wifi_setup_guide.html', instructions_html=html_content)
    except FileNotFoundError:
        flash('WiFi setup guide not found. Please contact support.', 'error')
        return redirect(url_for('dashboard.dashboard'))
    except Exception as e:
        logger.error(f"Error loading WiFi setup guide: {e}")
        flash('Error loading WiFi setup guide.', 'error')
        return redirect(url_for('dashboard.dashboard'))
