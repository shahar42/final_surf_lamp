import os
import redis
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import the database function and models
from data_base import add_user_and_lamp, SessionLocal, User, Lamp
from forms import RegistrationForm, LoginForm

# --- Enhanced Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_12345')
bcrypt = Bcrypt(app)

# --- Redis and Rate Limiter Setup ---
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)
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

# --- Routes ---

@app.route("/")
def index():
    """Redirects to the registration page by default."""
    return redirect(url_for('register'))

@app.route("/register", methods=['GET', 'POST'])
@limiter.limit("10/minute")
def register():
    """Handles user registration by collecting form data and calling the database handler."""
    logger.info(f"Registration attempt - Method: {request.method}, IP: {request.remote_addr}")
    
    form = RegistrationForm()
    form.location.choices = [(loc, loc) for loc in SURF_LOCATIONS]

    if request.method == 'POST':
        logger.info(f"POST data received: {list(request.form.keys())}")
        
        if form.validate_on_submit():
            logger.info("Form validation passed, attempting database registration")
            
            # Get Form Data
            name = form.name.data
            email = form.email.data
            password = form.password.data
            lamp_id = form.lamp_id.data
            arduino_id = form.arduino_id.data
            location = form.location.data
            theme = form.theme.data
            units = form.units.data

            logger.info(f"Registration data - Email: {email}, Lamp ID: {lamp_id}, Arduino ID: {arduino_id}, Location: {location}")

            # Process and Store Data
            try:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                logger.info("Password hashed successfully")
                
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

                logger.info(f"Database operation result - Success: {success}, Message: {message}")

                if success:
                    flash(message, 'success')
                    logger.info(f"Registration successful for {email}, redirecting to login")
                    return redirect(url_for('login'))
                else:
                    flash(message, 'error')
                    logger.warning(f"Registration failed for {email}: {message}")
                    return render_template('register.html', form=form, locations=SURF_LOCATIONS)
                    
            except Exception as e:
                logger.error(f"Unexpected error during registration for {email}: {str(e)}")
                flash("An unexpected error occurred. Please try again.", 'error')
                return render_template('register.html', form=form, locations=SURF_LOCATIONS)
        else:
            # Form validation failed
            logger.warning(f"Form validation failed for IP {request.remote_addr}")
            logger.warning(f"Form errors: {form.errors}")
            # Flash the first error for each field
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'error')
                    logger.warning(f"Validation error - {field}: {error}")

    return render_template('register.html', form=form, locations=SURF_LOCATIONS)

@app.route("/login", methods=['GET', 'POST'])
@limiter.limit("10/minute")
def login():
    """Handles user login by querying the database."""
    logger.info(f"Login attempt - Method: {request.method}, IP: {request.remote_addr}")
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        logger.info(f"Login attempt for email: {email}")

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                logger.info(f"Successful login for {email}")
                flash(f"Welcome back, {user.username}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"Failed login attempt for {email}")
                flash('Invalid email or password. Please try again.', 'error')
                return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Database error during login for {email}: {str(e)}")
            flash('A database error occurred. Please try again.', 'error')
        finally:
            db.close()

    return render_template('login.html', form=form)

@app.route("/dashboard")
def dashboard():
    """A placeholder for a logged-in user's dashboard."""
    return "<h1>Welcome to your Dashboard!</h1><p>Your surf lamp is now active and configured.</p>"

@app.route("/debug/users")
def debug_users():
    """Show all tables in the database"""
    logger.info(f"Debug users page accessed from IP: {request.remote_addr}")
    
    db = SessionLocal()
    try:
        # Import all the models
        from data_base import User, Lamp, DailyUsage, LocationWebsites, UsageLamps
        
        users = db.query(User).all()
        lamps = db.query(Lamp).all()
        daily_usage = db.query(DailyUsage).all()
        location_websites = db.query(LocationWebsites).all()
        usage_lamps = db.query(UsageLamps).all()
        
        logger.info(f"Debug query results - Users: {len(users)}, Lamps: {len(lamps)}, Daily Usage: {len(daily_usage)}")
        
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
        
        # Daily Usage table
        html += f"<h2>3. Daily Usage ({len(daily_usage)} records)</h2>"
        if daily_usage:
            html += "<table><tr><th>Usage ID</th><th>Website URL</th><th>Last Updated</th></tr>"
            for usage in daily_usage:
                html += f"<tr><td>{usage.usage_id}</td><td>{usage.website_url}</td><td>{usage.last_updated}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No daily usage records found</p>"
        
        # Location Websites table
        html += f"<h2>4. Location Websites ({len(location_websites)} records)</h2>"
        if location_websites:
            html += "<table><tr><th>Location</th><th>Usage ID</th></tr>"
            for loc in location_websites:
                html += f"<tr><td>{loc.location}</td><td>{loc.usage_id}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No location website mappings found</p>"
        
        # Usage Lamps table
        html += f"<h2>5. Usage Lamps ({len(usage_lamps)} records)</h2>"
        if usage_lamps:
            html += "<table><tr><th>Usage ID</th><th>Lamp ID</th><th>API Key</th><th>HTTP Endpoint</th></tr>"
            for ul in usage_lamps:
                html += f"<tr><td>{ul.usage_id}</td><td>{ul.lamp_id}</td><td>{ul.api_key}</td><td>{ul.http_endpoint}</td></tr>"
            html += "</table>"
        else:
            html += "<p class='empty'>No usage lamp configurations found</p>"
        
        return html
        
    except Exception as e:
        logger.error(f"Error in debug_users: {str(e)}")
        return f"<h1>Database Error</h1><p>{str(e)}</p>"
    finally:
        db.close()

if __name__ == '__main__':
    # For production on Render, use a WSGI server like Gunicorn.
    # The start command should be: gunicorn app:app
    app.run(debug=True, port=5001)
