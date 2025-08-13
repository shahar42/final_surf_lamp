import os
import redis
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

# Import the database function and models
from data_base import add_user_and_lamp, get_user_lamp_data, SessionLocal, User, Lamp

from forms import RegistrationForm, LoginForm

# --- Configuration ---
app = Flask(__name__)

# Fix for Render's reverse proxy - prevents redirect loops
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_12345')
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


# --- Static Data ---
SURF_LOCATIONS = [
    "Hadera, Israel"
]

# --- Helper Functions ---
def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route("/")
def index():
    """Shows surf data for logged-in users, otherwise redirects to registration."""
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
    
    return redirect(url_for('register'))

@app.route("/register", methods=['GET', 'POST'])
@limiter.limit("10/minute") # Add rate limiting to registration
def register():
    """Handles user registration by collecting form data and calling the database handler."""
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
    """Handles user login by querying the database."""
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
                flash(f"Welcome back, {user.username}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
                return redirect(url_for('login'))
        finally:
            db.close()

    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    """Log out the current user"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard showing user's lamp and current surf conditions."""
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

@app.route("/debug/users")
def debug_users():
    """Show all tables in the database"""
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
