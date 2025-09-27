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
import time
from datetime import datetime
import pytz

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import text
from forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mail import Mail, Message
import secrets
import hashlib
from datetime import datetime, timedelta
from data_base import PasswordResetToken
from data_base import add_user_and_lamp, get_user_lamp_data, SessionLocal, User, Lamp, update_user_location, CurrentConditions
from forms import RegistrationForm, LoginForm



# --- Configuration ---
app = Flask(__name__)

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

# Location to timezone mapping (for quiet hours)
LOCATION_TIMEZONES = {
    "Hadera, Israel": "Asia/Jerusalem",
    "Tel Aviv, Israel": "Asia/Jerusalem",
    "Ashdod, Israel": "Asia/Jerusalem",
    "Haifa, Israel": "Asia/Jerusalem",
    "Netanya, Israel": "Asia/Jerusalem",
    "Nahariya, Israel": "Asia/Jerusalem",
    "Ashkelon, Israel": "Asia/Jerusalem",
    "San Diego, USA": "America/Los_Angeles",
    "Barcelona, Spain": "Europe/Madrid",
    # Add more locations as needed
}

def is_quiet_hours(user_location, quiet_start_hour=22, quiet_end_hour=6):
    """
    Check if current time in user's location is within quiet hours (sleep time).

    Args:
        user_location: User's location string (e.g., "Tel Aviv, Israel")
        quiet_start_hour: Hour when quiet period starts (22 = 10 PM)
        quiet_end_hour: Hour when quiet period ends (6 = 6 AM)

    Returns:
        bool: True if within quiet hours, False otherwise
    """
    if not user_location or user_location not in LOCATION_TIMEZONES:
        return False  # Default to no quiet hours if location unknown

    try:
        timezone_str = LOCATION_TIMEZONES[user_location]
        local_tz = pytz.timezone(timezone_str)
        current_time = datetime.now(local_tz)
        current_hour = current_time.hour

        # Handle overnight quiet hours (e.g., 22:00 to 06:00)
        if quiet_start_hour > quiet_end_hour:
            return current_hour >= quiet_start_hour or current_hour < quiet_end_hour
        else:
            return quiet_start_hour <= current_hour < quiet_end_hour

    except Exception as e:
        logger.warning(f"Error checking quiet hours for {user_location}: {e}")
        return False  # Default to no quiet hours on error


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

def convert_wind_direction(degrees):
    """Convert wind direction from degrees to compass direction"""
    if degrees is None:
        return "--"
    
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

# Add the filter after the function is defined
app.jinja_env.filters['wind_direction'] = convert_wind_direction

# --- Helper Functions ---

app.config.update(
    MAIL_SERVER=os.environ.get('MAIL_SERVER'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')
)
mail = Mail(app)



def send_reset_email(user_email, username, token):
    reset_link = url_for('reset_password_form', token=token, _external=True)
    subject = "Password Reset Request"
    
    msg = Message(subject, recipients=[user_email])
    msg.body = f"""Hello {username},

Click this link to reset your password:
{reset_link}

This link expires in 20 minutes.
If you didn't request this, ignore this email.
"""
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False

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
                'wave_threshold_m': user.wave_threshold_m or 1.0,
                'wind_threshold_knots': user.wind_threshold_knots or 22.0
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

@app.route("/forgot-password", methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def forgot_password():
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower()
        
        # Always show same message (prevent enumeration)
        flash('If an account exists with that email, a reset link has been sent.', 'info')
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user:
                # Generate secure token
                token = secrets.token_urlsafe(48)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expiration = datetime.utcnow() + timedelta(minutes=20)
                
                # Invalidate old tokens
                db.query(PasswordResetToken).filter(
                    PasswordResetToken.user_id == user.user_id,
                    PasswordResetToken.used_at.is_(None)
                ).update({"is_invalidated": True})
                
                # Create new token
                reset_token = PasswordResetToken(
                    user_id=user.user_id,
                    token_hash=token_hash,
                    expiration_time=expiration
                )
                db.add(reset_token)
                db.commit()
                
                # Send email
                send_reset_email(user.email, user.username, token)
        finally:
            db.close()
            
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html', form=form)

@app.route("/reset-password/<token>", methods=['GET', 'POST'])
@limiter.limit("3 per 15 minutes")
def reset_password_form(token):
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        db = SessionLocal()
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            reset_token = db.query(PasswordResetToken).filter(
                PasswordResetToken.token_hash == token_hash
            ).first()
            
            if not reset_token or not reset_token.is_valid():
                flash('Invalid or expired reset link.', 'error')
                return redirect(url_for('forgot_password'))
            
            # Update password
            user = db.query(User).get(reset_token.user_id)
            user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            
            # Mark token as used
            reset_token.used_at = datetime.utcnow()
            db.commit()
            
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.rollback()
            flash('An error occurred. Please try again.', 'error')
        finally:
            db.close()
    
    return render_template('reset_password.html', form=form, token=token)

@app.route("/test-reset-db")
def test_reset_db():
    try:
        db = SessionLocal()
        
        # Get your actual user_id
        user = db.query(User).filter(User.email == 'shaharisn1@gmail.com').first()
        if not user:
            db.close()
            return "❌ User not found"
        
        # Get username before the session is closed
        username = user.username

        # Test with your real user_id
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expiration = datetime.utcnow() + timedelta(minutes=20)
        
        reset_token = PasswordResetToken(
            user_id=user.user_id,  # Use actual user_id
            token_hash=token_hash,
            expiration_time=expiration
        )
        db.add(reset_token)
        db.commit()
        db.close()
        
        return f"✅ Database test passed! Token created for user {username}"
        
    except Exception as e:
        return f"❌ Database test failed: {e}" 

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
        sport_type = form.sport_type.data
        theme = 'day'  # Default theme
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
            units=units,
            sport_type=sport_type
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            # We redirect to register, but the form will be populated with the previous data
            return render_template('register.html', form=form, locations=SURF_LOCATIONS)
    else:
        # Debug: Show validation errors when form doesn't validate
        if request.method == 'POST':
            for field_name, errors in form.errors.items():
                for error in errors:
                    flash(f"{field_name.replace('_', ' ').title()}: {error}", 'error')

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
            'wave_threshold_m': user.wave_threshold_m or 1.0,
            'wind_threshold_knots': user.wind_threshold_knots or 22.0
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
            'wave_threshold_m': user.wave_threshold_m or 1.0,
            'wind_threshold_knots': user.wind_threshold_knots or 22.0
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
            return {'success': True, 'message': 'Update success, data will update soon'}
        else:
            return {'success': False, 'message': message}, 500
            
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

@app.route("/update-wind-threshold", methods=['POST'])
@login_required
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

@app.route("/update-theme", methods=['POST'])
@login_required
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
            
            # Store Arduino IP address from callback
            arduino_ip = data.get('local_ip')
            if arduino_ip:
                lamp.arduino_ip = arduino_ip
                logger.info(f"📍 Updated Arduino {arduino_id} IP address: {arduino_ip}")
            
            # Update lamp timestamp (confirms delivery)
            lamp.last_updated = datetime.now()
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
                'timestamp': datetime.now().isoformat()
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

@app.route("/api/arduino/<int:arduino_id>/data", methods=['GET'])
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
            result = db.query(Lamp, CurrentConditions, User).select_from(Lamp)                .outerjoin(CurrentConditions, Lamp.lamp_id == CurrentConditions.lamp_id)                .join(User, Lamp.user_id == User.user_id)                .filter(Lamp.arduino_id == arduino_id)                .first()
            
            if not result:
                logger.warning(f"⚠️ Arduino {arduino_id} not found in database")
                return {'error': 'Arduino not found'}, 404
            
            lamp, conditions, user = result
            
            # Check if current time is within quiet hours for this user's location
            quiet_hours_active = is_quiet_hours(user.location)

            if quiet_hours_active:
                logger.info(f"🌙 Quiet hours active for {user.location} - threshold alerts disabled")

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

@app.route("/api/discovery/server", methods=['GET'])
def get_server_discovery():
    """
    Discovery endpoint: Returns current API server information
    Allows Arduino to find the correct server dynamically
    """
    try:
        # For now, return the current server info
        # Later we can make this configurable
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

@app.route("/themes")
@login_required
def themes_page():
    """
    Displays the LED theme configuration page.
    Shows available LED color themes with visual previews.
    """
    user_email = session.get('user_email')
    user, lamp, conditions = get_user_lamp_data(user_email)

    if not user or not lamp:
        flash('Error loading your lamp data. Please contact support.', 'error')
        return redirect(url_for('login'))

    # Prepare user data for template
    user_data = {
        'user': {
            'username': user.username,
            'theme': user.theme or 'classic_surf'
        }
    }

    return render_template('themes.html', data=user_data)

@app.route("/update-led-theme", methods=['POST'])
@login_required
def update_led_theme():
    """Update user's LED color theme to one of the predefined themes"""
    try:
        data = request.get_json()
        theme_id = data.get('theme_id')
        user_id = session.get('user_id')

        # Valid LED theme IDs
        valid_themes = [
            'classic_surf', 'ocean_breeze', 'sunset_surf', 'tropical_paradise', 'arctic_wind',
            'fire_storm', 'midnight_ocean', 'spring_meadow', 'royal_purple', 'golden_hour'
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


if __name__ == '__main__':
    # For production on Render, use a WSGI server like Gunicorn.
    # The start command should be: gunicorn app:app
    app.run(host='0.0.0.0', port=5001, debug=True)
