import os
import logging
from datetime import timedelta
import google.generativeai as genai
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from security_config import SecurityConfig, apply_security_headers

logger = logging.getLogger(__name__)

# Initialize extensions
bcrypt = Bcrypt()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)

# Constants
SURF_LOCATIONS = [
    "Hadera, Israel",
    "Tel Aviv, Israel", 
    "Ashdod, Israel",
    "Haifa, Israel",
    "Netanya, Israel",
    "Ashkelon, Israel",
    "Nahariya, Israel"
]

BRIGHTNESS_LEVELS = {
    'LOW': 0.35,
    'MID': 0.3,
    'HIGH': 1.0
}

def configure_app(app):
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        # Raise error if SECRET_KEY is missing, as in original app.py
        raise ValueError("SECRET_KEY environment variable is required")

    # Secure session cookie configuration
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    # Mail Config
    app.config.update(
        MAIL_SERVER=os.environ.get('MAIL_SERVER'),
        MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')
    )

    # Apply security headers and configuration
    apply_security_headers(app)
    app.config.from_object(SecurityConfig)

    # Redis for Limiter
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    app.config['RATELIMIT_STORAGE_URI'] = redis_url

    # Initialize extensions with app
    bcrypt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Gemini AI Configuration
    app.config['CHAT_BOT_ENABLED'] = os.environ.get('CHAT_BOT_ENABLED', 'false').lower() == 'true'
    app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY')
    app.config['GEMINI_MODEL'] = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

    if app.config['CHAT_BOT_ENABLED'] and app.config['GEMINI_API_KEY']:
        genai.configure(api_key=app.config['GEMINI_API_KEY'])
        logger.info(f"Gemini AI chatbot enabled with model: {app.config['GEMINI_MODEL']}")
    elif app.config['CHAT_BOT_ENABLED']:
        logger.warning("CHAT_BOT_ENABLED is true but GEMINI_API_KEY is not set")