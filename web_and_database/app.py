from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import redis
# Import the database function and models
from data_base import add_user_and_lamp, SessionLocal, User
# Import forms and security config
from forms import RegistrationForm, LoginForm, validate_location_choice, sanitize_input
from security_config import apply_security_headers

# --- Configuration ---
SURF_LOCATIONS = [
    "Bondi Beach, Australia",
    "Pipeline, Hawaii, USA",
    "Jeffreys Bay, South Africa",
    "Uluwatu, Bali, Indonesia",
    "Hossegor, France",
    "Tofino, British Columbia, Canada",
    "Santa Cruz, California, USA"
]

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_123')

# Initialize extensions
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

# Configure rate limiting with Redis (fallback to memory)
try:
    redis_client = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'),
                              port=int(os.environ.get('REDIS_PORT', 6379)),
                              db=0, decode_responses=True)
    redis_client.ping()  # Test connection
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        storage_uri=f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', 6379)}"
    )
except (redis.ConnectionError, redis.TimeoutError):
    # Fallback to memory storage if Redis is not available
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        storage_uri="memory://"
    )

# Apply security headers\napply_security_headers(app)

# --- Helper Functions ---
def is_valid_email(email):
    """A basic email validation (kept for backward compatibility)."""
    return "@" in email and "." in email

def is_valid_id(id_value):
    """Checks if an ID is a positive integer (kept for backward compatibility)."""
    return id_value.isdigit() and int(id_value) > 0

# Rate limiting decorators
def rate_limit_login():
    """Rate limit for login attempts"""
    return limiter.limit("5 per minute, 20 per hour")

def rate_limit_register():
    """Rate limit for registration attempts"""
    return limiter.limit("3 per minute, 10 per hour")

def rate_limit_general():
    """General rate limit"""
    return limiter.limit("100 per minute")

# --- Routes ---

@app.route("/")
def index():
    """Redirects to the registration page by default."""
    return redirect(url_for('register'))

@app.route("/register", methods=['GET', 'POST'])
@rate_limit_register()
def register():
    """Handles user registration with enhanced security validation."""
    form = RegistrationForm()
    
    # Set location choices dynamically
    form.location.choices = [('', 'Select Your Nearest Beach')] + [(loc, loc) for loc in SURF_LOCATIONS]
    
    if form.validate_on_submit():
        # Additional location validation
        if not validate_location_choice(form.location.data, SURF_LOCATIONS):
            flash('Invalid location selected.', 'error')
            return render_template('register.html', form=form, locations=SURF_LOCATIONS)
        
        # Sanitize all inputs (WTF forms already do basic sanitization)
        name = sanitize_input(form.name.data)
        email = sanitize_input(form.email.data.lower())
        location = sanitize_input(form.location.data)
        theme = sanitize_input(form.theme.data)
        units = sanitize_input(form.units.data)
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # Call the database function
        success, message = add_user_and_lamp(
            name=name,
            email=email,
            password_hash=hashed_password,
            lamp_id=form.lamp_id.data,
            arduino_id=form.arduino_id.data,
            location=location,
            theme=theme,
            units=units
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    # Display form errors
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{field.title()}: {error}", 'error')
            
    return render_template('register.html', form=form, locations=SURF_LOCATIONS)

@app.route("/login", methods=['GET', 'POST'])
@rate_limit_login()
def login():
    """Handles user login with enhanced security."""
    form = LoginForm()
    
    if form.validate_on_submit():
        email = sanitize_input(form.email.data.lower())
        password = form.password.data
        
        db = SessionLocal()
        try:
            # Use parameterized query to prevent SQL injection
            user = db.query(User).filter(User.email == email).first()
            
            if user and bcrypt.check_password_hash(user.password_hash, password):
                # In a real app, you would create a user session here (e.g., Flask-Login)
                flash(f"Welcome back, {sanitize_input(user.username)}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                # Generic error message to prevent user enumeration
                flash('Invalid email or password. Please try again.', 'error')
        except Exception as e:
            # Log the actual error but show generic message to user
            app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
        finally:
            db.close()
    
    # Display form errors
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{error}", 'error')
            
    return render_template('login.html', form=form)

@app.route("/dashboard")
@rate_limit_general()
def dashboard():
    """A placeholder for a logged-in user's dashboard."""
    return "<h1>Welcome to your Dashboard!</h1><p>Your surf lamp is now active and configured.</p>"

if __name__ == '__main__':
    # For production on Render, use a WSGI server like Gunicorn.
    # Example: gunicorn --bind 0.0.0.0:10000 app:app
    app.run(debug=True, port=5001)
