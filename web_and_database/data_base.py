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
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, MetaData, Float, Boolean, Time
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
import datetime

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

# Create the SQLAlchemy engine
try:
    engine = create_engine(DATABASE_URL)
    logger.info("SQLAlchemy engine created successfully")
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
        location (str): User's selected surf location.
        theme (str): Preferred visual theme (e.g., 'dark', 'light').
        preferred_output (str): Preferred unit system (e.g., 'metric', 'imperial').
        sport_type (str): User's chosen water sport type.
    """
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    location = Column(String(255), nullable=False)
    theme = Column(String(50), nullable=False)
    preferred_output = Column(String(50), nullable=False)
    sport_type = Column(String(20), nullable=False, default='surfing')
    wave_threshold_m = Column(Float, nullable=True, default=1.0)
    wind_threshold_knots = Column(Float, nullable=True, default=22.0)
    is_admin = Column(Boolean, default=False, nullable=False)
    off_time_start = Column(Time, nullable=True)
    off_time_end = Column(Time, nullable=True)
    off_times_enabled = Column(Boolean, default=False, nullable=False)

    lamp = relationship("Lamp", back_populates="user", uselist=False, cascade="all, delete-orphan")

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
    lamp_id = Column(Integer, nullable=True)
    arduino_id = Column(Integer, nullable=True)
    error_description = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    user = relationship("User", backref="error_reports")

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

class Lamp(Base):
    """
    Represents a physical Surf Lamp device.

    Attributes:
        lamp_id (int): Primary key, auto-generated unique ID.
        user_id (int): Foreign key linking to the User who owns the lamp.
        arduino_id (int): The unique ID of the Arduino microcontroller (device serial number).
        last_updated (datetime): Timestamp of the last successful data sync.
    """
    __tablename__ = 'lamps'
    lamp_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    arduino_id = Column(Integer, unique=True, nullable=True)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="lamp")
    usage_configs = relationship("UsageLamps", back_populates="lamp", cascade="all, delete-orphan")
    current_conditions = relationship("CurrentConditions", back_populates="lamp", uselist=False, cascade="all, delete-orphan")

class CurrentConditions(Base):
    """
    Stores the latest surf conditions fetched for a specific lamp.

    This table is updated by the background processor.

    Attributes:
        lamp_id (int): Foreign key linking to the Lamp.
        wave_height_m (float): Wave height in meters.
        wave_period_s (float): Wave period in seconds.
        wind_speed_mps (float): Wind speed in meters per second.
        wind_direction_deg (int): Wind direction in degrees.
        last_updated (datetime): Timestamp of when this data was fetched.
    """
    __tablename__ = 'current_conditions'
    lamp_id = Column(Integer, ForeignKey('lamps.lamp_id'), primary_key=True)
    wave_height_m = Column(Float, nullable=True)
    wave_period_s = Column(Float, nullable=True)
    wind_speed_mps = Column(Float, nullable=True)
    wind_direction_deg = Column(Integer, nullable=True)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    lamp = relationship("Lamp", back_populates="current_conditions")

class DailyUsage(Base):
    """
    Represents a unique data source API endpoint.

    This table helps deduplicate API calls. If multiple lamps use the same
    API endpoint, the background processor will only fetch the data once.

    Attributes:
        usage_id (int): Primary key.
        website_url (str): The base URL of the data source API.
        last_updated (datetime): Timestamp of the last fetch from this source.
    """
    __tablename__ = 'daily_usage'
    usage_id = Column(Integer, primary_key=True, autoincrement=True)
    website_url = Column(String(255), unique=True, nullable=False)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    locations = relationship("LocationWebsites", back_populates="website")
    lamp_configs = relationship("UsageLamps", back_populates="website")

class LocationWebsites(Base):
    """
    Maps a surf location to a specific data source (DailyUsage).

    Attributes:
        location (str): The name of the surf location (e.g., "Hadera, Israel").
        usage_id (int): Foreign key linking to the DailyUsage record.
    """
    __tablename__ = 'location_websites'
    location = Column(String(255), primary_key=True)
    usage_id = Column(Integer, ForeignKey('daily_usage.usage_id'), unique=True, nullable=False)
    
    website = relationship("DailyUsage", back_populates="locations")

class UsageLamps(Base):
    """
    Links a Lamp to a data source (DailyUsage), creating a specific API configuration.

    This is a many-to-many join table between lamps and data sources.

    Attributes:
        usage_id (int): Foreign key to DailyUsage.
        lamp_id (int): Foreign key to Lamp.
        api_key (str): The API key for the data source, if required.
        http_endpoint (str): The full, specific URL for the API call.
        arduino_ip (str): The IP address of the Arduino (denormalized for the background processor).
        endpoint_priority (int): Priority order for multiple endpoints (1 = highest priority).
    """
    __tablename__ = 'usage_lamps'
    usage_id = Column(Integer, ForeignKey('daily_usage.usage_id'), primary_key=True)
    lamp_id = Column(Integer, ForeignKey('lamps.lamp_id'), primary_key=True)
    api_key = Column(Text, nullable=True)
    http_endpoint = Column(Text, nullable=False)
    endpoint_priority = Column(Integer, nullable=False, default=1)
    
    lamp = relationship("Lamp", back_populates="usage_configs")
    website = relationship("DailyUsage", back_populates="lamp_configs")



# ============================================================================
# STORMGLASS.IO CONFIGURATION - PREMIUM UNIFIED API
# ============================================================================
# Set to True when you activate the paid plan (€129/month for 25k requests/day)
# Free tier has only 10 requests/day - insufficient for production use
USE_STORMGLASS = False  # ⚠️ Set to True to activate stormglass as primary source
STORMGLASS_API_KEY = "15d52392-d22c-11f0-a0d3-0242ac130003-15d52414-d22c-11f0-a0d3-0242ac130003"

# Stormglass locations (single API call provides wave + wind data)
STORMGLASS_LOCATIONS = {
    "Tel Aviv, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=32.0853&lng=34.7818&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Hadera, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=32.4343&lng=34.9197&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Ashdod, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=31.7939&lng=34.6328&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Haifa, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=32.7940&lng=34.9896&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Netanya, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=32.3215&lng=34.8532&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Nahariya, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=33.006&lng=35.094&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
            "priority": 1,
            "type": "unified",
            "api_key": STORMGLASS_API_KEY
        }
    ],
    "Ashkelon, Israel": [
        {
            "url": f"https://api.stormglass.io/v2/weather/point?lat=31.6699&lng=34.5738&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg",
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
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Tel Aviv&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Haifa&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Netanya&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
        "url": "http://api.openweathermap.org/data/2.5/weather?q=Nahariya&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
            "url": "http://api.openweathermap.org/data/2.5/weather?q=Ashkelon&appid=d6ef64df6585b7e88e51c221bbd41c2b",
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
    Creates a new user and registers their lamp with appropriate API sources.
    lamp_id is auto-generated by the database.
    Supports both single-source and multi-source locations.
    """
    logger.info(f"Starting user registration for email: {email}, arduino_id: {arduino_id}")
    
    db = SessionLocal()
    logger.info("Database session created")

    try:
        # Get active location configuration (stormglass or multi-source)
        active_config = get_active_location_config()

        # Determine if location is single-source or multi-source
        if location in active_config:
            api_sources = active_config[location]
            logger.info(f"Location '{location}' uses {len(api_sources)} API sources")
        elif location in SINGLE_SOURCE_LOCATIONS:
            api_sources = SINGLE_SOURCE_LOCATIONS[location]
            logger.info(f"Location '{location}' uses 1 API source")
        else:
            logger.error(f"Unsupported location for registration: {location}")
            return False, f"Location '{location}' is not supported yet."

        # 1. Create the new User
        logger.info("Creating new User record")
        new_user = User(
            username=name,
            email=email,
            password_hash=password_hash,
            location=location,
            theme=theme,
            preferred_output=units,
            sport_type=sport_type
        )
        db.add(new_user)
        db.flush()
        logger.info(f"Created User record with user_id: {new_user.user_id}")

        # 2. Create the new Lamp (lamp_id auto-generated by database)
        logger.info("Creating new Lamp record")
        new_lamp = Lamp(
            user_id=new_user.user_id,
            arduino_id=arduino_id
        )
        db.add(new_lamp)
        db.flush()  # Flush to get auto-generated lamp_id
        logger.info(f"Created Lamp record with auto-generated lamp_id: {new_lamp.lamp_id}")
        
        # 3. Create API sources for this location
        for source in api_sources:
            logger.info(f"Processing {source['type']} API source")
            
            # Get or create DailyUsage record for this API URL
            website = db.query(DailyUsage).filter(DailyUsage.website_url == source['url']).first()
            if not website:
                logger.info(f"Creating new DailyUsage record for {source['type']}")
                website = DailyUsage(website_url=source['url'])
                db.add(website)
                db.flush()
                logger.info(f"Created DailyUsage record with usage_id: {website.usage_id}")
            else:
                logger.info(f"Found existing DailyUsage record with usage_id: {website.usage_id}")

            # Create UsageLamps link with priority
            usage_lamp_link = UsageLamps(
                usage_id=website.usage_id,
                lamp_id=new_lamp.lamp_id,
                api_key=None,
                http_endpoint=source['url'],
                endpoint_priority=source['priority']
            )
            db.add(usage_lamp_link)
            logger.info(f"Created UsageLamps link: {source['type']} (priority {source['priority']})")

        # 4. Create LocationWebsites mapping (use first source for mapping)
        first_source = api_sources[0]
        first_website = db.query(DailyUsage).filter(DailyUsage.website_url == first_source['url']).first()
        
        location_website = db.query(LocationWebsites).filter(LocationWebsites.location == location).first()
        if not location_website:
            logger.info("Creating LocationWebsites mapping")
            location_website = LocationWebsites(
                location=location,
                usage_id=first_website.usage_id
            )
            db.add(location_website)
            logger.info(f"Created LocationWebsites mapping: {location} -> usage_id={first_website.usage_id}")

        # 5. Commit the entire transaction
        logger.info("Committing transaction")
        db.commit()
        logger.info("User and lamp registered successfully")
        return True, "User and lamp registered successfully."

    except IntegrityError as e:
        logger.error(f"IntegrityError during registration: {e}")
        db.rollback()

        # Parse the error to determine which constraint was violated
        error_msg = str(e.orig)

        if 'users_email_key' in error_msg:
            return False, "This email address is already registered. Please use a different email or login."
        elif 'users_username_key' in error_msg:
            return False, "This username is already taken. Please choose a different username."
        elif 'lamps_arduino_id_key' in error_msg:
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


def get_user_lamp_data(email):
    """
    Retrieves all relevant data for the user dashboard.

    This function fetches the user's profile, their lamp's details, and the
    most recent surf conditions recorded for that lamp. It uses a LEFT JOIN
    to ensure that user and lamp data are returned even if no surf conditions
    have been recorded yet.

    Args:
        email (str): The email address of the logged-in user.

    Returns:
        tuple: A tuple containing (User, Lamp, CurrentConditions) objects.
               If the user is not found, returns (None, None, None).
    """
    logger.info(f"Fetching lamp data for user: {email}")
    
    db = SessionLocal()
    try:
        # Query user -> lamp -> current_conditions with LEFT JOIN
        result = db.query(User, Lamp, CurrentConditions).select_from(User)\
            .join(Lamp, User.user_id == Lamp.user_id)\
            .outerjoin(CurrentConditions, Lamp.lamp_id == CurrentConditions.lamp_id)\
            .filter(User.email == email)\
            .first()
        
        if not result:
            logger.warning(f"No user found with email: {email}")
            return None, None, None
        
        user, lamp, conditions = result
        logger.info(f"Found user {user.username} with lamp {lamp.lamp_id}")
        
        return user, lamp, conditions
        
    except Exception as e:
        logger.error(f"Error fetching user lamp data: {e}")
        return None, None, None
    finally:
        db.close()

def update_user_location(user_id, new_location):
    """Update user's location and reconfigure their lamp's API endpoints."""
    logger.info(f"Updating location for user_id: {user_id} to: {new_location}")

    db = SessionLocal()

    # Get active location configuration (stormglass or multi-source)
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
        # 1. Update user's location
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False, "User not found"
        
        old_location = user.location
        user.location = new_location
        
        # 2. Get user's lamp
        lamp = db.query(Lamp).filter(Lamp.user_id == user_id).first()
        if not lamp:
            return False, "No lamp found for user"
        
        # 3. Delete existing UsageLamps records for this lamp
        db.query(UsageLamps).filter(UsageLamps.lamp_id == lamp.lamp_id).delete()
        logger.info(f"Deleted old UsageLamps records for lamp {lamp.lamp_id}")
        
        # 4. Create new UsageLamps records for new location
        for source in api_sources:
            # Get or create DailyUsage record
            website = db.query(DailyUsage).filter(DailyUsage.website_url == source['url']).first()
            if not website:
                website = DailyUsage(website_url=source['url'])
                db.add(website)
                db.flush()
            
            # Create new UsageLamps record
            usage_lamp = UsageLamps(
                usage_id=website.usage_id,
                lamp_id=lamp.lamp_id,
                api_key=None,
                http_endpoint=source['url'],
                endpoint_priority=source['priority']
            )
            db.add(usage_lamp)
            logger.info(f"Added {source['type']} API source (priority {source['priority']})")
        
        # 5. Update LocationWebsites mapping
        first_website = db.query(DailyUsage).filter(DailyUsage.website_url == api_sources[0]['url']).first()
        location_website = db.query(LocationWebsites).filter(LocationWebsites.location == new_location).first()
        if not location_website:
            location_website = LocationWebsites(
                location=new_location,
                usage_id=first_website.usage_id
            )
            db.add(location_website)
        
        # 6. Commit changes
        db.commit()
        logger.info(f"Successfully updated location from '{old_location}' to '{new_location}'")
        return True, "Location updated successfully"
        
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
            (PasswordResetToken.is_invalidated == True)
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
