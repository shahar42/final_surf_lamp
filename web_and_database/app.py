import os
import redis
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import the database function and models
from data_base import add_user_and_lamp, SessionLocal, User
from forms import RegistrationForm, LoginForm

# --- Configuration ---
app = Flask(__name__)
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
@limiter.limit("10/minute") # Add rate limiting to registration
def register():
    """Handles user registration by collecting form data and calling the database handler."""
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
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                flash(f"Welcome back, {user.username}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
                return redirect(url_for('login'))
        finally:
            db.close()

    return render_template('login.html', form=form)

@app.route("/dashboard")
def dashboard():
    """A placeholder for a logged-in user's dashboard."""
    return "<h1>Welcome to your Dashboard!</h1><p>Your surf lamp is now active and configured.</p>"

@app.route("/debug/users")
def debug_users():
    """Show all users in a simple table"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        lamps = db.query(Lamp).all()
        
        html = """
        <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
        <h1>Database Contents</h1>
        
        <h2>Users</h2>
        <table>
            <tr><th>ID</th><th>Username</th><th>Email</th><th>Location</th><th>Theme</th><th>Units</th></tr>
        """
        
        for user in users:
            html += f"<tr><td>{user.user_id}</td><td>{user.username}</td><td>{user.email}</td><td>{user.location}</td><td>{user.theme}</td><td>{user.preferred_output}</td></tr>"
        
        html += """
        </table>
        
        <h2>Lamps</h2>
        <table>
            <tr><th>Lamp ID</th><th>User ID</th><th>Arduino ID</th><th>Last Updated</th></tr>
        """
        
        for lamp in lamps:
            html += f"<tr><td>{lamp.lamp_id}</td><td>{lamp.user_id}</td><td>{lamp.arduino_id}</td><td>{lamp.last_updated}</td></tr>"
        
        html += "</table>"
        return html
        
    finally:
        db.close()

if __name__ == '__main__':
    # For production on Render, use a WSGI server like Gunicorn.
    # The start command should be: gunicorn app:app
    app.run(debug=True, port=5001)
