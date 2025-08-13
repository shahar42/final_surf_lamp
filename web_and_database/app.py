import os
import redis
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import logging
from sqlalchemy import text

# Import the database function and models
from data_base import add_user_and_lamp, get_user_lamp_data, SessionLocal, User, Lamp
from forms import RegistrationForm, LoginForm

# --- Production Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration ---
app = Flask(__name__)

# Production-ready session configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_12345'),
    SESSION_COOKIE_SECURE=True if os.environ.get('FLASK_ENV') == 'production' else False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour
)

bcrypt = Bcrypt(app)

# --- Redis and Rate Limiter Setup with Error Handling ---
def setup_rate_limiter():
    """Setup rate limiter with fallback for Redis failures"""
    try:
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            # Test Redis connection
            redis_client = redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
            redis_client.ping()  # Test connection
            logger.info("Redis connection successful")
            
            limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=redis_url,
                storage_options={"socket_connect_timeout": 30},
                strategy="fixed-window",
            )
            return limiter
        else:
            logger.warning("No REDIS_URL provided, using memory storage")
            # Fallback to memory storage
            limiter = Limiter(
                key_func=get_remote_address,
                storage_uri="memory://",
                strategy="fixed-window",
            )
            return limiter
            
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        logger.info("Falling back to memory storage for rate limiting")
        
        # Fallback to memory storage if Redis fails
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri="memory://",
            strategy="fixed-window",
        )
        return limiter

# Initialize rate limiter
limiter = setup_rate_limiter()
limiter.init_app(app)

# --- Static Data ---
SURF_LOCATIONS = [
    "Bondi Beach, Australia",
    "Pipeline, Hawaii, USA",
    "Jeffreys Bay, South Africa",
    "Uluwatu, Bali, Indonesia",
    "Hossegor, France",
    "Tofino, British Columbia, Canada",
    "Santa Cruz, California, USA"
]

# --- Helper Functions ---
def safe_rate_limit(limit_string):
    """Decorator that safely applies rate limiting with fallback"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Apply rate limiting if available
                if limiter:
                    return limiter.limit(limit_string)(f)(*args, **kwargs)
                else:
                    return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                # Continue without rate limiting if it fails
                return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            logger.info("User not logged in, redirecting to login")
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def test_database_connection():
    """Test database connection and log any issues"""
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        db.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

# --- Routes ---

@app.route("/")
def index():
    """Root route with proper error handling"""
    try:
        logger.info(f"Index route accessed. Session data: {dict(session)}")
        
        # Test database connection
        if not test_database_connection():
            flash('Database connection issue. Please try again later.', 'error')
            return render_template('login.html', form=LoginForm())
        
        if 'user_email' in session:
            logger.info(f"User {session['user_email']} already logged in, redirecting to dashboard")
            return redirect(url_for('dashboard'))
        else:
            logger.info("No user session, redirecting to login")
            return redirect(url_for('login'))
            
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        flash('An error occurred. Please try again.', 'error')
        return render_template('login.html', form=LoginForm())

@app.route("/register", methods=['GET', 'POST'])
@safe_rate_limit("5/minute")
def register():
    """Handles user registration with comprehensive error handling"""
    try:
        logger.info("Register route accessed")
        
        if 'user_email' in session:
            logger.info("User already logged in, redirecting to dashboard")
            return redirect(url_for('dashboard'))
            
        form = RegistrationForm()
        form.location.choices = [(loc, loc) for loc in SURF_LOCATIONS]

        if form.validate_on_submit():
            logger.info(f"Registration form submitted for email: {form.email.data}")
            
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
            try:
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
                    logger.info(f"User registration successful: {email}")
                    flash(message, 'success')
                    return redirect(url_for('login'))
                else:
                    logger.warning(f"User registration failed: {message}")
                    flash(message, 'error')
                    
            except Exception as e:
                logger.error(f"Registration processing error: {e}")
                flash('Registration failed due to a system error. Please try again.', 'error')

        return render_template('register.html', form=form, locations=SURF_LOCATIONS)
        
    except Exception as e:
        logger.error(f"Error in register route: {e}")
        flash('An error occurred during registration. Please try again.', 'error')
        return render_template('register.html', form=RegistrationForm(), locations=SURF_LOCATIONS)

@app.route("/login", methods=['GET', 'POST'])
@safe_rate_limit("5/minute")
def login():
    """Handles user login with comprehensive error handling"""
    try:
        logger.info("Login route accessed")
        
        if 'user_email' in session:
            logger.info("User already logged in, redirecting to dashboard")
            return redirect(url_for('dashboard'))
            
        form = LoginForm()
        
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            logger.info(f"Login attempt for email: {email}")

            try:
                db = SessionLocal()
                user = db.query(User).filter(User.email == email).first()
                
                if user and bcrypt.check_password_hash(user.password_hash, password):
                    # Set session data
                    session['user_email'] = user.email
                    session['user_id'] = user.user_id
                    session['username'] = user.username
                    session.permanent = True
                    
                    logger.info(f"Login successful for user: {email}")
                    flash(f"Welcome back, {user.username}!", 'success')
                    
                    db.close()
                    return redirect(url_for('dashboard'))
                else:
                    logger.warning(f"Login failed for email: {email}")
                    flash('Invalid email or password. Please try again.', 'error')
                    
                db.close()
                
            except Exception as e:
                logger.error(f"Database error during login: {e}")
                flash('Login failed due to a system error. Please try again.', 'error')

        return render_template('login.html', form=form)
        
    except Exception as e:
        logger.error(f"Error in login route: {e}")
        flash('An error occurred during login. Please try again.', 'error')
        return render_template('login.html', form=LoginForm())

@app.route("/logout")
def logout():
    """Log out the current user"""
    try:
        user_email = session.get('user_email', 'unknown')
        session.clear()
        logger.info(f"User logged out: {user_email}")
        flash('You have been logged out.', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard showing user's lamp and current surf conditions."""
    try:
        user_email = session.get('user_email')
        logger.info(f"Dashboard accessed by: {user_email}")
        
        # Get user, lamp, and conditions data
        user, lamp, conditions = get_user_lamp_data(user_email)
        
        if not user or not lamp:
            logger.error(f"No lamp data found for user: {user_email}")
            flash('Error loading your lamp data. Please contact support.', 'error')
            session.clear()  # Clear invalid session
            return redirect(url_for('login'))
        
        # Prepare data for template
        dashboard_data = {
            'user': {
                'username': user.username,
                'email': user.email,
                'location': user.location,
                'theme': user.theme,
                'preferred_output': user.preferred_output
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
        
        return render_template('dashboard.html', data=dashboard_data)
        
    except Exception as e:
        logger.error(f"Error in dashboard route: {e}")
        flash('Error loading dashboard. Please try logging in again.', 'error')
        session.clear()
        return redirect(url_for('login'))

@app.route("/debug/users")
def debug_users():
    """Show all tables in the database - only for development"""
    if os.environ.get('FLASK_ENV') != 'development':
        logger.warning("Debug route accessed in production")
        return "Debug routes disabled in production", 403
        
    try:
        db = SessionLocal()
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
        
        db.close()
        return html
        
    except Exception as e:
        logger.error(f"Error in debug route: {e}")
        return f"Debug error: {str(e)}", 500

# --- Error Handlers ---
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    flash('Too many requests. Please try again later.', 'error')
    return redirect(url_for('login')), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('login')), 500

if __name__ == '__main__':
    # For production on Render, use a WSGI server like Gunicorn.
    # The start command should be: gunicorn app:app
    logger.info("Starting Flask application")
    app.run(debug=True, port=5001)
