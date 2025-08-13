import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, MetaData, Float
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
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    location = Column(String(255), nullable=False)
    theme = Column(String(50), nullable=False)
    preferred_output = Column(String(50), nullable=False)
    
    lamp = relationship("Lamp", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Lamp(Base):
    __tablename__ = 'lamps'
    lamp_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    arduino_id = Column(Integer, unique=True, nullable=True)
    arduino_ip = Column(String(15), unique=True, nullable=False)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="lamp")
    usage_configs = relationship("UsageLamps", back_populates="lamp", cascade="all, delete-orphan")
    current_conditions = relationship("CurrentConditions", back_populates="lamp", uselist=False, cascade="all, delete-orphan")

class CurrentConditions(Base):
    __tablename__ = 'current_conditions'
    lamp_id = Column(Integer, ForeignKey('lamps.lamp_id'), primary_key=True)
    wave_height_m = Column(Float, nullable=True)
    wave_period_s = Column(Float, nullable=True)
    wind_speed_mps = Column(Float, nullable=True)
    wind_direction_deg = Column(Integer, nullable=True)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    lamp = relationship("Lamp", back_populates="current_conditions")

class DailyUsage(Base):
    __tablename__ = 'daily_usage'
    usage_id = Column(Integer, primary_key=True, autoincrement=True)
    website_url = Column(String(255), unique=True, nullable=False)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    locations = relationship("LocationWebsites", back_populates="website")
    lamp_configs = relationship("UsageLamps", back_populates="website")

class LocationWebsites(Base):
    __tablename__ = 'location_websites'
    location = Column(String(255), primary_key=True)
    usage_id = Column(Integer, ForeignKey('daily_usage.usage_id'), unique=True, nullable=False)
    
    website = relationship("DailyUsage", back_populates="locations")

class UsageLamps(Base):
    __tablename__ = 'usage_lamps'
    usage_id = Column(Integer, ForeignKey('daily_usage.usage_id'), primary_key=True)
    lamp_id = Column(Integer, ForeignKey('lamps.lamp_id'), primary_key=True)
    api_key = Column(Text, nullable=True)
    http_endpoint = Column(Text, nullable=False)
    arduino_ip = Column(String(15), nullable=True)  # UPDATED: Added arduino_ip column
    
    lamp = relationship("Lamp", back_populates="usage_configs")
    website = relationship("DailyUsage", back_populates="lamp_configs")


# --- Database Interaction Function ---

def add_user_and_lamp(name, email, password_hash, lamp_id, arduino_id, location, theme, units):
    """
    Creates a new user, registers their lamp, and links it to the correct 
    data source based on location.
    Returns (True, "Success") on success, (False, "Error message") on failure.
    """
    logger.info(f"Starting user registration for email: {email}, lamp_id: {lamp_id}, arduino_id: {arduino_id}")
    
    db = SessionLocal()
    logger.info("Database session created")
    
    # Define which locations map to which website/API provider.
    LOCATIONS_WEBSITE_1 = [
        "Hadera, Israel"
    ]
    
    # Only support configured locations, no arbitrary fallbacks
    if location == "Hadera, Israel":
        target_website_url = "https://isramar.ocean.org.il"
    else:
        logger.error(f"Unsupported location for registration: {location}")
        return False, f"Location '{location}' is not supported yet. Currently supported: Hadera, Israel"

    try:
        # 1. Get or create the DailyUsage record for the target website
        logger.info(f"Looking for existing DailyUsage record for: {target_website_url}")
        website = db.query(DailyUsage).filter(DailyUsage.website_url == target_website_url).first()
        if not website:
            logger.info("Creating new DailyUsage record")
            website = DailyUsage(website_url=target_website_url)
            db.add(website)
            db.flush()
            logger.info(f"Created DailyUsage record with usage_id: {website.usage_id}")
        else:
            logger.info(f"Found existing DailyUsage record with usage_id: {website.usage_id}")

        # 2. Create the new User
        logger.info("Creating new User record")
        new_user = User(
            username=name,
            email=email,
            password_hash=password_hash,
            location=location,
            theme=theme,
            preferred_output=units
        )
        db.add(new_user)
        db.flush()
        logger.info(f"Created User record with user_id: {new_user.user_id}")

        # 3. Create the new Lamp and link it to the user
        logger.info("Creating new Lamp record")
        new_lamp = Lamp(
            lamp_id=lamp_id,
            user_id=new_user.user_id,
            arduino_id=arduino_id
        )
        db.add(new_lamp)
        logger.info(f"Created Lamp record with lamp_id: {new_lamp.lamp_id}")
        
        # 4. Link the Lamp to the Website via UsageLamps
        logger.info("Creating UsageLamps link")
        usage_lamp_link = UsageLamps(
            usage_id=website.usage_id,
            lamp_id=new_lamp.lamp_id,
            api_key=os.environ.get('DEFAULT_API_KEY', 'your_api_key_here'), # Get key from environment
            http_endpoint=f"{target_website_url}/{location.replace(' ', '_').lower()}",
            arduino_ip=None  # Will be populated later when Arduino IP is known
        )
        db.add(usage_lamp_link)
        logger.info(f"Created UsageLamps link: usage_id={website.usage_id}, lamp_id={new_lamp.lamp_id}")

        # 4.5. Create or get LocationWebsites mapping
        location_website = db.query(LocationWebsites).filter(LocationWebsites.location == location).first()
        if not location_website:
            logger.info("Creating LocationWebsites mapping")
            location_website = LocationWebsites(
                location=location,
                usage_id=website.usage_id
            )
            db.add(location_website)
            logger.info(f"Created LocationWebsites mapping: {location} -> usage_id={website.usage_id}")
        else:
            logger.info(f"Found existing LocationWebsites mapping for {location}")

        # 5. Commit the entire transaction
        logger.info("Committing transaction")
        db.commit()
        logger.info("User and lamp registered successfully")
        return True, "User and lamp registered successfully."

    except IntegrityError as e:
        logger.error(f"IntegrityError during registration: {e}")
        db.rollback()
        return False, "An account with this email, username, lamp ID, or Arduino ID already exists."
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        db.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        logger.info("Closing database session")
        db.close()


def get_user_lamp_data(email):
    """
    Get user and lamp data with current surf conditions for dashboard.
    Returns (user_data, lamp_data, conditions_data) or (None, None, None) if not found.
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


# --- Main execution block to create tables ---
if __name__ == '__main__':
    logger.info("Creating database tables based on the defined schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
