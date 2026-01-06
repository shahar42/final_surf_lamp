"""
This module handles all database interactions for the Surf Lamp web application.

It defines the database schema using SQLAlchemy ORM, provides functions for creating,
reading, and updating data, and manages the database connection.

Key Components:
- **SQLAlchemy Engine and Session:** Configured using environment variables for
  portability between local development and production environments (e.g., Render).
- **ORM Models:** Defines the `User`, `Lamp`, `CurrentConditions`, `DailyUsage`,
  `LocationWebsites`, and `UsageLamps` tables.
- **Database Interaction Functions:**
  - `add_user_and_lamp`: Handles the user registration process, creating records
    in multiple tables within a single transaction.
  - `get_user_lamp_data`: Retrieves a user's profile, lamp details, and the
    latest surf conditions for the dashboard.
"""

import os
import logging
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, Float, Boolean, Time
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from config import BRIGHTNESS_LEVELS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Setup ---
# Get the database URL from environment variables. This is crucial for deployment on Render.
DATABASE_URL = os.environ.get('DATABASE_URL')
logger.info(f"DATABASE_URL from environment: {'SET' if DATABASE_URL else 'NOT SET'}")

if not DATABASE_URL:
    DB_USER = os.environ.get('DB_USER')
    DB_PASS = os.environ.get('DB_PASS')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_NAME = os.environ.get('DB_NAME')
    
    logger.info(f"Individual DB variables - USER: {'SET' if DB_USER else 'NOT SET'}, "
                f"HOST: {DB_HOST or 'NOT SET'}, PORT: {DB_PORT or 'NOT SET'}, "
                f"NAME: {DB_NAME or 'NOT SET'}, PASS: {'SET' if DB_PASS else 'NOT SET'}")
    
    if all([DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME]):
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        logger.info("Built DATABASE_URL from individual components")
    else:
        DATABASE_URL = 'postgresql://user:password@localhost/surfboard_lamp'
        logger.warning("Using localhost fallback DATABASE_URL - this will fail in production!")

# Log the database URL (without password for security)
if DATABASE_URL:
    # Hide password in logs
    safe_url = DATABASE_URL.replace(DATABASE_URL.split('://')[1].split('@')[0].split(':')[1], '***') if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Final DATABASE_URL: {safe_url}")

# Create the SQLAlchemy engine with optimized connection pooling
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,           # 10 persistent connections (up from default 5)
        max_overflow=20,        # Allow 30 total connections under load (up from 10)
        pool_pre_ping=True,     # Test connections before use (critical for Supabase)
        pool_recycle=1800,      # Recycle connections after 30min (Supabase idle timeout is 1hr)
        echo=False              # Set to True for SQL query logging during debugging
    )
    logger.info("SQLAlchemy engine created with optimized connection pool (size=10, max=30)")
except Exception as e:
    logger.error(f"Failed to create SQLAlchemy engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models (updated to match current database schema) ---

class User(Base):
    """
    Represents a user of the application.

    Attributes:
        user_id (int): Primary key.
        username (str): User's chosen username.
        password_hash (str): Hashed password for security.
        email (str): User's email address, used for login.
        location (str): User's dashboard default view location (arduinos can override).
        theme (str): Preferred visual theme (e.g., 'dark', 'light').
        preferred_output (str): Preferred unit system (e.g., 'metric', 'imperial').
        sport_type (str): User's chosen water sport type.
    """
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    location = Column(String(255), nullable=False)  # Dashboard default view
    theme = Column(String(50), nullable=False)
    preferred_output = Column(String(50), nullable=False)
    sport_type = Column(String(20), nullable=False, default='surfing')
    wave_threshold_m = Column(Float, nullable=True, default=1.0)
    wave_threshold_max_m = Column(Float, nullable=True, default=None)
    wind_threshold_knots = Column(Float, nullable=True, default=22.0)
    wind_threshold_max_knots = Column(Float, nullable=True, default=None)
    is_admin = Column(Boolean, default=False, nullable=False)
    off_time_start = Column(Time, nullable=True)
    off_time_end = Column(Time, nullable=True)
    off_times_enabled = Column(Boolean, default=False, nullable=False)
    brightness_level = Column(Float, default=BRIGHTNESS_LEVELS['MID'], nullable=False)

    arduinos = relationship("Arduino", back_populates="user", cascade="all, delete-orphan")

class PasswordResetToken(Base):
    """Stores password reset tokens"""
    __tablename__ = 'password_reset_tokens'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False)
    expiration_time = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    used_at = Column(TIMESTAMP, nullable=True)
    is_invalidated = Column(Boolean, default=False, nullable=False)
    
    user = relationship("User", backref="reset_tokens")
    
    def is_valid(self):
        from datetime import datetime
        return (self.expiration_time > datetime.utcnow() and
                self.used_at is None and
                not self.is_invalidated)

class ErrorReport(Base):
    """Stores user-submitted error reports from the dashboard"""
    __tablename__ = 'error_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    arduino_id = Column(Integer, ForeignKey('arduinos.arduino_id'), nullable=True)
    error_description = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    user = relationship("User", backref="error_reports")
    arduino = relationship("Arduino", backref="error_reports")

class Broadcast(Base):
    """Stores admin broadcast messages for dashboard notifications"""
    __tablename__ = 'broadcasts'

    broadcast_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    message = Column(Text, nullable=False)
    target_location = Column(String(255), nullable=True)  # NULL = all users
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    admin = relationship("User", backref="broadcasts")

class Arduino(Base):
    """
    Represents a physical Surf Lamp Arduino device.

    Attributes:
        arduino_id (int): Primary key - the unique ID of the ESP32 microcontroller.
        user_id (int): Foreign key linking to the User who owns the device.
        location (str): Foreign key to Location - where this specific arduino fetches data.
        last_poll_time (datetime): Timestamp of the last time Arduino polled for data.
    """
    __tablename__ = 'arduinos'
    arduino_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    location = Column(String(255), ForeignKey('locations.location'), nullable=False)
    last_poll_time = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="arduinos")
    location_data = relationship("Location", back_populates="arduinos")

class Location(Base):
    """
    Stores surf conditions and API endpoints for a geographic location.

    Location-centric architecture: One API call per location updates this table,
    then all arduinos at that location inherit the data.

    Attributes:
        location (str): Primary key - location name (e.g., "Hadera, Israel").
        wave_api_url (str): API endpoint for wave data.
        wind_api_url (str): API endpoint for wind data.
        wave_height_m (float): Current wave height in meters.
        wave_period_s (float): Current wave period in seconds.
        wind_speed_mps (float): Current wind speed in meters per second.
        wind_direction_deg (int): Current wind direction in degrees.
        last_updated (datetime): Timestamp of when conditions were last fetched.
    """
    __tablename__ = 'locations'
    location = Column(String(255), primary_key=True)
    wave_api_url = Column(Text, nullable=False)
    wind_api_url = Column(Text, nullable=False)
    wave_height_m = Column(Float, nullable=True)
    wave_period_s = Column(Float, nullable=True)
    wind_speed_mps = Column(Float, nullable=True)
    wind_direction_deg = Column(Integer, nullable=True)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    arduinos = relationship("Arduino", back_populates="location_data")



# ============================================================================
# STORMGLASS.IO CONFIGURATION - PREMIUM UNIFIED API
# ============================================================================
# Set to True when you activate the paid plan (€129/month for 25k requests/day)
# Free tier has only 10 requests/day - insufficient for production use
USE_STORMGLASS = False  # ⚠️ Set to True to activate stormglass as primary source
STORMGLASS_API_KEY = os.environ.get('STORMGLASS_API_KEY', '')
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

# Stormglass locations (single API call provides wave + wind data)
STORMGLASS_LOCATIONS = {
    "Tel Aviv, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=32.0853&lng=34.7818&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Hadera, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=32.4343&lng=34.9197&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Ashdod, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=31.7939&lng=34.6328&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Haifa, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=32.7940&lng=34.9896&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Netanya, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=32.3215&lng=34.8532&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Nahariya, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=33.006&lng=35.094&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Ashkelon, Israel": [
        {
            "url": "https://api.stormglass.io/v2/weather/point?lat=31.6699&lng=34.5738&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ]
}

# ============================================================================
# LOCATION TO TIMEZONE MAPPING (SHARED CONFIG)
# ============================================================================
# Single source of truth for location-based timezone mapping.
# Used by both web app (quiet hours/off hours) and background processor (timestamps).
#
# Usage:
#   - Web app (app.py): is_quiet_hours(), is_off_hours() for time-based features
#   - Processor (background_processor.py): format_for_arduino() for local timestamps
#
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

# MULTI-SOURCE CONFIGURATION - FREE APIS (CURRENT PRODUCTION)
# ============================================================================
# Multi-source locations (require multiple API calls)
# ⚠️  CRITICAL: ALL Open-Meteo wind URLs MUST include "&wind_speed_unit=ms" parameter!
# Without this parameter, APIs return km/h instead of m/s and break wind calculations.
MULTI_SOURCE_LOCATIONS = {
    "Tel Aviv, Israel": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": f"http://api.openweathermap.org/data/2.5/weather?q=Tel Aviv&appid={OPENWEATHERMAP_API_KEY}",
            "priority": 2,
            "type": "wind"
        }
    ],
    "Hadera, Israel": [
        {
            "url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": f"http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid={OPENWEATHERMAP_API_KEY}",
            "priority": 2,
            "type": "wind"
        }
    ],
    "Ashdod, Israel": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.7939&longitude=34.6328&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": f"http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid={OPENWEATHERMAP_API_KEY}",
            "priority": 2,
            "type": "wind"
        }
    ],
    "Haifa, Israel": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.7940&longitude=34.9896&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": f"http://api.openweathermap.org/data/2.5/weather?q=Haifa&appid={OPENWEATHERMAP_API_KEY}",
            "priority": 2,
            "type": "wind"
        }
    ],
    "Netanya, Israel": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.3215&longitude=34.8532&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": f"http://api.openweathermap.org/data/2.5/weather?q=Netanya&appid={OPENWEATHERMAP_API_KEY}",
            "priority": 2,
            "type": "wind"
        }
    ],
    "Nahariya, Israel": [
    {
        "url": "https://marine-api.open-meteo.com/v1/marine?latitude=33.006&longitude=35.094&hourly=wave_height,wave_period,wave_direction",
        "priority": 1,
        "type": "wave"
    },
    {
        "url": f"http://api.openweathermap.org/data/2.5/weather?q=Nahariya&appid={OPENWEATHERMAP_API_KEY}",
        "priority": 2,
        "type": "wind"
    }
    ],
    "Ashkelon, Israel": [
        {
            "url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.6699&longitude=34.5738&hourly=wave_height,wave_period,wave_direction",
            "priority": 1,
            "type": "wave"
        },
        {
            "url": f"http://api.openweathermap.org/data/2.5/weather?q=Ashkelon&appid={OPENWEATHERMAP_API_KEY}",
            "priority": 2,
            "type": "wind"
        }
    ]
}

# Single-source locations (one API provides everything)
SINGLE_SOURCE_LOCATIONS = {
    # Future locations that provide wave + wind in one API
}

def get_active_location_config():
    """
    Returns the active location configuration based on USE_STORMGLASS flag.

    Returns:
        dict: STORMGLASS_LOCATIONS if USE_STORMGLASS=True, else MULTI_SOURCE_LOCATIONS
    """
    if USE_STORMGLASS:
        logger.info("🌊 Using STORMGLASS.IO as primary source (paid plan active)")
        return STORMGLASS_LOCATIONS
    else:
        logger.info("📡 Using MULTI_SOURCE free APIs (current production)")
        return MULTI_SOURCE_LOCATIONS

def add_user_and_lamp(name, email, password_hash, arduino_id, location, theme, units, sport_type='surfing'):
    """
    Creates a new user and registers their arduino device.
    Uses location-centric architecture: Location record must exist first.
    """
    logger.info(f"Starting user registration for email: {email}, arduino_id: {arduino_id}")

    db = SessionLocal()
    logger.info("Database session created")

    try:
        # Get active location configuration (stormglass or multi-source)
        active_config = get_active_location_config()

        # Determine API sources for this location
        if location in active_config:
            api_sources = active_config[location]
            logger.info(f"Location '{location}' uses {len(api_sources)} API sources")
        elif location in SINGLE_SOURCE_LOCATIONS:
            api_sources = SINGLE_SOURCE_LOCATIONS[location]
            logger.info(f"Location '{location}' uses 1 API source")
        else:
            logger.error(f"Unsupported location for registration: {location}")
            return False, f"Location '{location}' is not supported yet."

        # 1. Ensure Location record exists
        location_record = db.query(Location).filter(Location.location == location).first()
        if not location_record:
            # Create location with API endpoints
            wave_source = next((s for s in api_sources if s.get('type') == 'wave'), api_sources[0])
            wind_source = next((s for s in api_sources if s.get('type') == 'wind'), api_sources[-1])

            location_record = Location(
                location=location,
                wave_api_url=wave_source['url'],
                wind_api_url=wind_source['url']
            )
            db.add(location_record)
            db.flush()
            logger.info(f"Created Location record: {location}")

        # 2. Create the new User
        logger.info("Creating new User record")
        new_user = User(
            username=name,
            email=email,
            password_hash=password_hash,
            location=location,  # Dashboard default view
            theme=theme,
            preferred_output=units,
            sport_type=sport_type
        )
        db.add(new_user)
        db.flush()
        logger.info(f"Created User record with user_id: {new_user.user_id}")

        # 3. Create the new Arduino
        logger.info("Creating new Arduino record")
        new_arduino = Arduino(
            arduino_id=arduino_id,
            user_id=new_user.user_id,
            location=location
        )
        db.add(new_arduino)
        logger.info(f"Created Arduino record with arduino_id: {arduino_id}")

        # 4. Commit the entire transaction
        logger.info("Committing transaction")
        db.commit()
        logger.info("User and arduino registered successfully")
        return True, "User and arduino registered successfully."

    except IntegrityError as e:
        logger.error(f"IntegrityError during registration: {e}")
        db.rollback()

        # Parse the error to determine which constraint was violated
        error_msg = str(e.orig)

        if 'users_email_key' in error_msg:
            return False, "This email address is already registered. Please use a different email or login."
        elif 'users_username_key' in error_msg:
            return False, "This username is already taken. Please choose a different username."
        elif 'arduinos_pkey' in error_msg or 'arduino' in error_msg.lower():
            return False, "This Device ID is already registered to another user. Please check your Device ID."
        else:
            # Fallback for unexpected constraint violations
            return False, "Registration failed due to duplicate data. Please check your information."
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        db.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        logger.info("Closing database session")
        db.close()


def add_arduino_to_user(user_id, arduino_id, location):
    """
    Links a new Arduino device to an existing user.
    """
    logger.info(f"Linking arduino {arduino_id} to user_id: {user_id} at location: {location}")

    db = SessionLocal()
    try:
        # 1. Ensure Location record exists
        active_config = get_active_location_config()
        if location not in active_config and location not in SINGLE_SOURCE_LOCATIONS:
            return False, f"Location '{location}' is not supported"

        location_record = db.query(Location).filter(Location.location == location).first()
        if not location_record:
            api_sources = active_config.get(location) or SINGLE_SOURCE_LOCATIONS[location]
            wave_source = next((s for s in api_sources if s.get('type') == 'wave'), api_sources[0])
            wind_source = next((s for s in api_sources if s.get('type') == 'wind'), api_sources[-1])

            location_record = Location(
                location=location,
                wave_api_url=wave_source['url'],
                wind_api_url=wind_source['url']
            )
            db.add(location_record)
            db.flush()

        # 2. Create Arduino record
        new_arduino = Arduino(
            arduino_id=arduino_id,
            user_id=user_id,
            location=location
        )
        db.add(new_arduino)
        db.commit()
        
        logger.info(f"Successfully linked arduino {arduino_id} to user {user_id}")
        return True, "Arduino linked successfully"

    except IntegrityError:
        db.rollback()
        return False, "This Arduino ID is already registered to another user"
    except Exception as e:
        logger.error(f"Error linking arduino: {e}")
        db.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        db.close()


def get_user_lamp_data(email):
    """
    Retrieves all relevant data for the user dashboard.

    This function fetches the user's profile, their arduinos, and the
    surf conditions for the user's default location.

    Args:
        email (str): The email address of the logged-in user.

    Returns:
        tuple: A tuple containing (User, list[Arduino], Location) objects.
               If the user is not found, returns (None, None, None).
    """
    logger.info(f"Fetching arduino data for user: {email}")

    db = SessionLocal()
    try:
        # Query user and their default location conditions
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.warning(f"No user found with email: {email}")
            return None, None, None

        # Get all arduinos for this user
        arduinos = db.query(Arduino).filter(Arduino.user_id == user.user_id).all()

        # Get location data for user's default dashboard view
        location = db.query(Location).filter(Location.location == user.location).first()

        logger.info(f"Found user {user.username} with {len(arduinos)} arduino(s)")

        return user, arduinos, location

    except Exception as e:
        logger.error(f"Error fetching user arduino data: {e}")
        return None, None, None
    finally:
        db.close()

def update_user_location(user_id, new_location):
    """
    Update user's dashboard default location.
    Note: Arduino locations are independent and not modified by this function.
    """
    logger.info(f"Updating dashboard location for user_id: {user_id} to: {new_location}")

    db = SessionLocal()

    # Get active location configuration to validate location exists
    active_config = get_active_location_config()

    # Determine API sources for new location
    if new_location in active_config:
        api_sources = active_config[new_location]
    elif new_location in SINGLE_SOURCE_LOCATIONS:
        api_sources = SINGLE_SOURCE_LOCATIONS[new_location]
    else:
        logger.error(f"No API mapping found for location: {new_location}")
        return False, f"Location '{new_location}' is not supported"

    try:
        # 1. Ensure Location record exists
        location_record = db.query(Location).filter(Location.location == new_location).first()
        if not location_record:
            # Create location with API endpoints
            wave_source = next((s for s in api_sources if s.get('type') == 'wave'), api_sources[0])
            wind_source = next((s for s in api_sources if s.get('type') == 'wind'), api_sources[-1])

            location_record = Location(
                location=new_location,
                wave_api_url=wave_source['url'],
                wind_api_url=wind_source['url']
            )
            db.add(location_record)
            logger.info(f"Created Location record: {new_location}")

        # 2. Update user's dashboard location
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False, "User not found"

        old_location = user.location
        user.location = new_location

        # 3. Commit changes
        db.commit()
        logger.info(f"Successfully updated dashboard location from '{old_location}' to '{new_location}'")
        return True, "Dashboard location updated successfully"

    except Exception as e:
        logger.error(f"Error updating location: {e}")
        db.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        db.close()

def cleanup_expired_password_reset_tokens():
    """
    Delete expired, used, or invalidated password reset tokens.

    Deletes tokens that are:
    - Older than 24 hours (regardless of state)
    - Already used (used_at is not null)
    - Invalidated (is_invalidated is true)

    This function should be called periodically (e.g., daily via cron job)
    to prevent unbounded table growth.

    Returns:
        int: Number of tokens deleted
    """
    from datetime import datetime, timezone, timedelta

    db = SessionLocal()
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        # Delete tokens matching any of these conditions:
        # 1. Created more than 24 hours ago
        # 2. Already used
        # 3. Manually invalidated
        deleted_count = db.query(PasswordResetToken).filter(
            (PasswordResetToken.created_at < cutoff_time) |
            (PasswordResetToken.used_at.isnot(None)) |
            PasswordResetToken.is_invalidated
        ).delete(synchronize_session=False)

        db.commit()

        if deleted_count > 0:
            logger.info(f"✅ Cleaned up {deleted_count} password reset tokens")

        return deleted_count

    except Exception as e:
        logger.error(f"❌ Error cleaning up password reset tokens: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

# --- Main execution block to create tables ---
if __name__ == '__main__':
    logger.info("Creating database tables based on the defined schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
