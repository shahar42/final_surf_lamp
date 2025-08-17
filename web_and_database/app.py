"""
This module implements the main Flask web application for the Surf Lamp project.

It provides user-facing routes for registration, login, and viewing the dashboard.
The application handles user authentication, session management, and serves as the
primary interface for users to interact with their Surf Lamp data.

Key Features:
- **User Authentication:** Handles user registration, login, and logout functionality.
- **Session Management:** Uses Flask sessions to maintain user login state.
- **Dashboard Display:** Fetches and displays user-specific data, including lamp
  details and the latest surf conditions.
- **Rate Limiting:** Implements rate limiting on authentication routes to prevent abuse.
- **Database Integration:** Interacts with the database via functions defined in
  the `data_base` module.
- **Environment-based Configuration:** Configured via environment variables for
  seamless deployment.
"""

import os
import logging
import redis
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

# Import the database function and models
from data_base import add_user_and_lamp, get_user_lamp_data, SessionLocal, User, Lamp, update_user_location

from forms import RegistrationForm, LoginForm

def convert_wind_direction(degrees):
    """Convert wind direction from degrees to compass direction"""
    if degrees is None:
        return "--"
    
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

# --- Configuration ---
app = Flask(__name__)

app.jinja_env.filters['wind_direction'] = convert_wind_direction

# Fix for Render's reverse proxy - prevents redirect loops
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("SECRET_KEY environment variable is required")
bcrypt = Bcrypt(app)

# --- Redis and Rate Limiter Setup ---
# Use the REDIS_URL from environment variables provided by Render.
# Fallback to localhost for local development.
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# Initialize the limiter with the correct storage URI
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)
# Then, associate it with your app
limiter.init_app(app)

# Location change rate limiting storage
location_changes = {}  # {user_id: [timestamp1, timestamp2, ...]}


# --- Static Data ---
SURF_LOCATIONS = [
    "Hadera, Israel",
    "Tel Aviv, Israel", 
    "Ashdod, Israel",
    "Haifa, Israel",
    "Netanya, Israel",
    "Ashkelon, Israel",
    "Nahariya, Israel"
]

# --- Helper Functions ---
def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.

    If the user is not logged in (i.e., 'user_email' not in session), it flashes
    an error message and redirects them to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_location_change_limit(user_id):
    """Check if user has exceeded 5 location changes per day"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if user_id not in location_changes:
        location_changes[user_id] = []
    
    # Remove old entries (older than 24 hours)
    location_changes[user_id] = [
        timestamp for timestamp in location_changes[user_id] 
        if timestamp > today_start
    ]
    
    # Check if limit exceeded
    if len(location_changes[user_id]) >= 7:
        return False, "Maximum 7 location changes per day reached"
    
    # Add current timestamp
    location_changes[user_id].append(now)
    return True, "OK"

# --- ---Routes ---------------------------

@app.route("/")
def index():
    """
    Serves the main page.

    If the user is logged in, it displays their personalized dashboard.
    Otherwise, it redirects to the registration page.
    """
    if 'user_email' in session:
        # Get user's surf data (same logic as dashboard)
        user_email = session.get('user_email')
        user, lamp, conditions = get_user_lamp_data(user_email)
        
        if not user or not lamp:
            flash('Error loading your lamp data. Please contact support.', 'error')
            return redirect(url_for('login'))
        
        # Prepare surf data for display
        dashboard_data = {
            'user': {
                'username': user.username,
                'email': user.email,
                'location': user.location,
                'theme': user.theme,
                'preferred_output': user.preferred_output,
                'wave_threshold_m': user.wave_threshold_m or 1.0
            },
            'lamp': {
                'lamp_id': lamp.lamp_id,
                'arduino_id': lamp.arduino_id,
                'last_updated': lamp.last_updated
            },
            'conditions': None
        }
        
        # Add surf conditions if available
        if conditions:
            dashboard_data['conditions'] = {
                'wave_height_m': conditions.wave_height_m,
                'wave_period_s': conditions.wave_period_s,
                'wind_speed_mps': conditions.wind_speed_mps,
                'wind_direction_deg': conditions.wind_direction_deg,
                'last_updated': conditions.last_updated
            }
        
        return render_template('dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS)
    
    return redirect(url_for('register'))

@app.route("/register", methods=['GET', 'POST'])
@limiter.limit("10/minute") # Add rate limiting to registration
def register():
    """
    Handles user registration.

    On GET, it displays the registration form.
    On POST, it validates the form data, creates a new user and lamp via
    `add_user_and_lamp`, and redirects to the login page upon success.
    """
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
        
    form = RegistrationForm()
    form.location.choices = [(loc, loc) for loc in SURF_LOCATIONS]

    if form.validate_on_submit():
        # Get Form Data
        name = form.name.data
        email = form.email.data
        password = form.password.data
        lamp_id = form.lamp_id.data
        arduino_id = form.arduino_id.data
        location = form.location.data
        theme = form.theme.data
        units = form.units.data

        # Process and Store Data
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        success, message = add_user_and_lamp(
            name=name,
            email=email,
            password_hash=hashed_password,
            lamp_id=int(lamp_id),
            arduino_id=int(arduino_id),
            location=location,
            theme=theme,
            units=units
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            # We redirect to register, but the form will be populated with the previous data
            return render_template('register.html', form=form, locations=SURF_LOCATIONS)

    return render_template('register.html', form=form, locations=SURF_LOCATIONS)

@app.route("/login", methods=['GET', 'POST'])
@limiter.limit("10/minute") # Add rate limiting to login
def login():
    """
    Handles user login.

    On GET, it displays the login form.
    On POST, it validates credentials against the database. On success,
    it creates a user session and redirects to the dashboard.
    """
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                # Set session data
                session['user_email'] = user.email
                session['user_id'] = user.user_id
                session['username'] = user.username
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
                return redirect(url_for('login'))
        finally:
            db.close()

    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    """
    Logs out the current user by clearing the session.
    """
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    """
    Displays the user's personalized dashboard.

    Requires the user to be logged in. It fetches the user's lamp data and
    the latest surf conditions and renders them in the dashboard template.
    """
    user_email = session.get('user_email')
    
    # Get user, lamp, and conditions data
    user, lamp, conditions = get_user_lamp_data(user_email)
    
    if not user or not lamp:
        flash('Error loading your lamp data. Please contact support.', 'error')
        return redirect(url_for('login'))
    
    # Prepare data for template
    dashboard_data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'location': user.location,
            'theme': user.theme,
            'preferred_output': user.preferred_output,
            'wave_threshold_m': user.wave_threshold_m or 1.0
        },
        'lamp': {
            'lamp_id': lamp.lamp_id,
            'arduino_id': lamp.arduino_id,
            'last_updated': lamp.last_updated
        },
        'conditions': None
    }
    
    # Add surf conditions if available
    if conditions:
        dashboard_data['conditions'] = {
            'wave_height_m': conditions.wave_height_m,
            'wave_period_s': conditions.wave_period_s,
            'wind_speed_mps': conditions.wind_speed_mps,
            'wind_direction_deg': conditions.wind_direction_deg,
            'last_updated': conditions.last_updated
        }
    
    return render_template('dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS)

@app.route("/dashboard/<view_type>")
@login_required
def dashboard_view(view_type):
    """
    Displays the user's personalized dashboard with a specific view.

    Requires the user to be logged in. It fetches the user's lamp data and
    the latest surf conditions and renders them in the specified template.
    """
    user_email = session.get('user_email')
    
    # Get user, lamp, and conditions data
    user, lamp, conditions = get_user_lamp_data(user_email)
    
    if not user or not lamp:
        flash('Error loading your lamp data. Please contact support.', 'error')
        return redirect(url_for('login'))
    
    # Prepare data for template
    dashboard_data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'location': user.location,
            'theme': user.theme,
            'preferred_output': user.preferred_output,
            'wave_threshold_m': user.wave_threshold_m or 1.0
        },
        'lamp': {
            'lamp_id': lamp.lamp_id,
            'arduino_id': lamp.arduino_id,
            'last_updated': lamp.last_updated
        },
        'conditions': None
    }
    
    # Add surf conditions if available
    if conditions:
        dashboard_data['conditions'] = {
            'wave_height_m': conditions.wave_height_m,
            'wave_period_s': conditions.wave_period_s,
            'wind_speed_mps': conditions.wind_speed_mps,
            'wind_direction_deg': conditions.wind_direction_deg,
            'last_updated': conditions.last_updated
        }
    
    if view_type == 'experimental':
        return render_template('experimental_dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS)
    else:
        return render_template('dashboard.html', data=dashboard_data, locations=SURF_LOCATIONS)

@app.route("/update-location", methods=['POST'])
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
        can_change, rate_message = check_location_change_limit(user_id)
        if not can_change:
            return {'success': False, 'message': rate_message}, 429
        
        # Import the update function
        from data_base import update_user_location
        
        # Update location in database
        success, message = update_user_location(user_id, new_location)
        
        if success:
            # Update session
            session['user_location'] = new_location
            return {'success': True, 'message': 'Location updated successfully'}
        else:
            return {'success': False, 'message': message}, 500
            
    except Exception as e:
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@app.route("/update-theme", methods=['POST'])
@login_required
def update_theme():
    """Update user's theme"""
    try:
        data = request.get_json()
        new_theme = data.get('theme')
        user_id = session.get('user_id')

        # Validate theme
        if new_theme not in ['dark', 'light']:
            return {'success': False, 'message': 'Invalid theme selected'}, 400

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.theme = new_theme
                db.commit()
                session['theme'] = new_theme
                return {'success': True, 'message': 'Theme updated successfully'}
            else:
                return {'success': False, 'message': 'User not found'}, 404
        finally:
            db.close()
            
    except Exception as e:
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500

@app.route("/update-threshold", methods=['POST'])
@login_required
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

@app.route("/admin/trigger-processor")
@login_required  # Only logged-in users can trigger
def trigger_processor():
    """Manually trigger the background processor once"""
    try:
        # Import the processor function
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'surf-lamp-processor'))
        from background_processor import run_once
        
        # Run the processor once
        success = run_once()
        
        if success:
            flash('Background processor completed successfully! Check your dashboard for updated data.', 'success')
        else:
            flash('Background processor encountered errors. Check logs for details.', 'error')
            
    except Exception as e:
        flash(f'Error running processor: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route("/api/arduino/callback", methods=['POST'])
def handle_arduino_callback():
    """
    Handle callbacks from Arduino devices confirming surf data receipt and processing.
    
    Expected JSON format from Arduino:
    {
        "arduino_id": 4433,
        "status": "received", 
        "wave_height_m": 0.64,
        "wave_period_s": 5.0,
        "wind_speed_mps": 4.2,
        "wind_direction_deg": 160,
        "local_ip": "192.168.1.123",
        "timestamp": 12345678,
        "free_memory": 245760
    }
    """
    try:
        # Get JSON data from Arduino
        data = request.get_json()
        
        if not data:
            logger.error("No JSON data received in Arduino callback")
            return {'success': False, 'message': 'No JSON data provided'}, 400
        
        # Extract required fields
        arduino_id = data.get('arduino_id')
        status = data.get('status', 'unknown')
        
        if not arduino_id:
            logger.error("Arduino callback missing arduino_id")
            return {'success': False, 'message': 'arduino_id is required'}, 400
        
        logger.info(f"📥 Arduino Callback - ID: {arduino_id}, Status: {status}")
        logger.info(f"   Data: Wave {data.get('wave_height_m', 0)}m, Wind {data.get('wind_speed_mps', 0)}m/s")
        logger.info(f"   Arduino IP: {data.get('local_ip', 'unknown')}, Memory: {data.get('free_memory', 0)} bytes")
        
        # Update database with confirmed delivery
        db = SessionLocal()
        try:
            # Find the lamp by arduino_id
            lamp = db.query(Lamp).filter(Lamp.arduino_id == arduino_id).first()
            
            if not lamp:
                logger.warning(f"⚠️  Arduino {arduino_id} not found in database")
                return {'success': False, 'message': f'Arduino {arduino_id} not found'}, 404
            
            # Update lamp timestamp (confirms delivery)
            lamp.last_updated = datetime.now()
            logger.info(f"✅ Updated lamp {lamp.lamp_id} timestamp")
            
            # Update or create current conditions with CONFIRMED values from Arduino
            conditions = db.query(CurrentConditions).filter(
                CurrentConditions.lamp_id == lamp.lamp_id
            ).first()
            
            if not conditions:
                # Create new conditions record
                conditions = CurrentConditions(lamp_id=lamp.lamp_id)
                db.add(conditions)
                logger.info(f"🆕 Created new conditions record for lamp {lamp.lamp_id}")
            
            # Update with the ACTUAL values that Arduino processed and displayed
            conditions.wave_height_m = data.get('wave_height_m', 0.0)
            conditions.wave_period_s = data.get('wave_period_s', 0.0)
            conditions.wind_speed_mps = data.get('wind_speed_mps', 0.0)
            conditions.wind_direction_deg = data.get('wind_direction_deg', 0)
            conditions.last_updated = datetime.now()
            
            # Commit all changes
            db.commit()
            
            logger.info(f"✅ Database updated successfully for Arduino {arduino_id}")
            logger.info(f"   Lamp ID: {lamp.lamp_id}, Conditions updated: {conditions.last_updated}")
            
            # Return success response to Arduino
            response_data = {
                'success': True,
                'message': 'Callback processed successfully',
                'lamp_id': lamp.lamp_id,
                'arduino_id': arduino_id,
                'timestamp': datetime.now().isoformat(),
                'database_updated': True
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

@app.route("/api/arduino/status", methods=['GET'])
def arduino_status_overview():
    """
    Optional: Get overview of all Arduino devices and their last callback times.
    Useful for monitoring and debugging.
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
                'timestamp': datetime.now().isoformat()
            }, 200
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting Arduino status overview: {e}")
        return {'success': False, 'message': str(e)}, 500

@app.route("/debug/users")
def debug_users():
    """
    A debug route to display the contents of all database tables.

    This provides a raw, unstyled view of the data in the `users`, `lamps`,
    `current_conditions`, `daily_usage`, `location_websites`, and `usage_lamps`
    tables for easy debugging.
    """
    db = SessionLocal()
    try:
        # Import all the models
        from data_base import User, Lamp, DailyUsage, LocationWebsites, UsageLamps, CurrentConditions
        
        users = db.query(User).all()
        lamps = db.query(Lamp).all()
        daily_usage = db.query(DailyUsage).all()
        location_websites = db.query(LocationWebsites).all()
        usage_lamps = db.query(UsageLamps).all()
        current_conditions = db.query(CurrentConditions).all()
        
        html = """
        <style>
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .empty { color: #999; font-style: italic; }
        </style>
        <h1>All Database Tables</h1>
        """
        
        # Users table
        html += f"<h2>1. Users ({len(users)} records)</h2>"
        if users:
            html += "<table><tr><th>ID</th><th>Username</th><th>Email</th><th>Location</th><th>Theme</th><th>Units</th></tr>"
            for user in users:
                html += f"<tr><td>{user.user_id}</td><td>{user.username}</td><td>{user.email}</td><td>{user.location}</td><td>{user.theme}</td><td>{user.preferred_output}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No users found</p>"
        
        # Lamps table
        html += f"<h2>2. Lamps ({len(lamps)} records)</h2>"
        if lamps:
            html += "<table><tr><th>Lamp ID</th><th>User ID</th><th>Arduino ID</th><th>Last Updated</th></tr>"
            for lamp in lamps:
                html += f"<tr><td>{lamp.lamp_id}</td><td>{lamp.user_id}</td><td>{lamp.arduino_id}</td><td>{lamp.last_updated}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No lamps found</p>"
            
        # Current Conditions table
        html += f"<h2>3. Current Conditions ({len(current_conditions)} records)</h2>"
        if current_conditions:
            html += "<table><tr><th>Lamp ID</th><th>Wave Height (m)</th><th>Wave Period (s)</th><th>Wind Speed (mps)</th><th>Wind Direction (deg)</th><th>Last Updated</th></tr>"
            for cc in current_conditions:
                html += f"<tr><td>{cc.lamp_id}</td><td>{cc.wave_height_m}</td><td>{cc.wave_period_s}</td><td>{cc.wind_speed_mps}</td><td>{cc.wind_direction_deg}</td><td>{cc.last_updated}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No current conditions found</p>"
        
        # Daily Usage table
        html += f"<h2>4. Daily Usage ({len(daily_usage)} records)</h2>"
        if daily_usage:
            html += "<table><tr><th>Usage ID</th><th>Website URL</th><th>Last Updated</th></tr>"
            for usage in daily_usage:
                html += f"<tr><td>{usage.usage_id}</td><td>{usage.website_url}</td><td>{usage.last_updated}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No daily usage records found</p>"
        
        # Location Websites table
        html += f"<h2>5. Location Websites ({len(location_websites)} records)</h2>"
        if location_websites:
            html += "<table><tr><th>Location</th><th>Usage ID</th></tr>"
            for loc in location_websites:
                html += f"<tr><td>{loc.location}</td><td>{loc.usage_id}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No location website mappings found</p>"
        
        # Usage Lamps table
        html += f"<h2>6. Usage Lamps ({len(usage_lamps)} records)</h2>"
        if usage_lamps:
            html += "<table><tr><th>Usage ID</th><th>Lamp ID</th><th>API Key</th><th>HTTP Endpoint</th></tr>"
            for ul in usage_lamps:
                html += f"<tr><td>{ul.usage_id}</td><td>{ul.lamp_id}</td><td>{ul.api_key}</td><td>{ul.http_endpoint}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No usage lamp configurations found</p>"
        
        return html
        
    finally:
        db.close()

if __name__ == '__main__':
    # For production on Render, use a WSGI server like Gunicorn.
    # The start command should be: gunicorn app:app
    app.run(debug=True, port=5001)
