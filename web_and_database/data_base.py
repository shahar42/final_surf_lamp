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
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    DB_USER = os.environ.get('DB_USER')
    DB_PASS = os.environ.get('DB_PASS')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_NAME = os.environ.get('DB_NAME')
    
    if all([DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME]):
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        DATABASE_URL = 'postgresql://user:password@localhost/surfboard_lamp'

try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False
    )
    logger.info("Database engine created")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---

class User(Base):
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
    wave_threshold_max_m = Column(Float, nullable=True, default=2.0)
    wind_threshold_knots = Column(Float, nullable=True, default=22.0)
    wind_threshold_max_knots = Column(Float, nullable=True, default=32.0)
    is_admin = Column(Boolean, default=False, nullable=False)
    off_time_start = Column(Time, nullable=True)
    off_time_end = Column(Time, nullable=True)
    off_times_enabled = Column(Boolean, default=False, nullable=False)
    quiet_times_enabled = Column(Boolean, default=True, nullable=False)
    brightness_level = Column(Float, default=BRIGHTNESS_LEVELS['MID'], nullable=False)

    arduinos = relationship("Arduino", back_populates="user", cascade="all, delete-orphan")

class PasswordResetToken(Base):
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
    __tablename__ = 'broadcasts'

    broadcast_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    message = Column(Text, nullable=False)
    target_location = Column(String(255), nullable=True)  
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    admin = relationship("User", backref="broadcasts")

class Arduino(Base):
    __tablename__ = 'arduinos'
    arduino_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    location = Column(String(255), ForeignKey('locations.location'), nullable=False)
    last_poll_time = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    fallback_v2_count = Column(Integer, default=0)
    last_v2_fallback = Column(TIMESTAMP, nullable=True)
    request_interval_minutes = Column(Integer, default=13, nullable=False)

    user = relationship("User", back_populates="arduinos")
    location_data = relationship("Location", back_populates="arduinos")

class Location(Base):
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

class NotificationSubscription(Base):
    __tablename__ = 'notification_subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", backref="subscriptions")


# API Configuration
USE_STORMGLASS = False  
STORMGLASS_API_KEY = os.environ.get('STORMGLASS_API_KEY', '')
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

STORMGLASS_LOCATIONS = {
    "Tel Aviv, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=32.0853&lng=34.7818&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}],
    "Hadera, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=32.4343&lng=34.9197&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}],
    "Ashdod, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=31.7939&lng=34.6328&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}],
    "Haifa, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=32.7940&lng=34.9896&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}],
    "Netanya, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=32.3215&lng=34.8532&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}],
    "Nahariya, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=33.006&lng=35.094&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}],
    "Ashkelon, Israel": [{"url": "https://api.stormglass.io/v2/weather/point?lat=31.6699&lng=34.5738&params=waveHeight,wavePeriod,waveDirection,windSpeed,windDirection&source=sg", "priority": 1, "type": "unified", "api_key": STORMGLASS_API_KEY}]
}

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
}

MULTI_SOURCE_LOCATIONS = {
    "Tel Aviv, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.0853&longitude=34.7818&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Tel Aviv&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ],
    "Hadera, Israel": [
        {"url": "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ],
    "Ashdod, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.7939&longitude=34.6328&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ],
    "Haifa, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.7940&longitude=34.9896&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Haifa&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ],
    "Netanya, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=32.3215&longitude=34.8532&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Netanya&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ],
    "Nahariya, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=33.006&longitude=35.094&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Nahariya&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ],
    "Ashkelon, Israel": [
        {"url": "https://marine-api.open-meteo.com/v1/marine?latitude=31.6699&longitude=34.5738&hourly=wave_height,wave_period,wave_direction", "priority": 1, "type": "wave"},
        {"url": f"http://api.openweathermap.org/data/2.5/weather?q=Ashkelon&appid={OPENWEATHERMAP_API_KEY}", "priority": 2, "type": "wind"}
    ]
}

def get_active_location_config():
    if USE_STORMGLASS:
        return STORMGLASS_LOCATIONS
    return MULTI_SOURCE_LOCATIONS

def add_user_and_lamp(name, email, password_hash, arduino_id, location, theme, units, sport_type='surfing'):
    db = SessionLocal()
    try:
        active_config = get_active_location_config()
        if location not in active_config:
            return False, f"Location '{location}' not supported", None

        api_sources = active_config[location]
        location_record = db.query(Location).filter(Location.location == location).first()
        
        if not location_record:
            wave_source = next((s for s in api_sources if s.get('type') == 'wave'), api_sources[0])
            wind_source = next((s for s in api_sources if s.get('type') == 'wind'), api_sources[-1])
            location_record = Location(location=location, wave_api_url=wave_source['url'], wind_api_url=wind_source['url'])
            db.add(location_record)
            db.flush()

        new_user = User(username=name, email=email, password_hash=password_hash, location=location, theme=theme, preferred_output=units, sport_type=sport_type)
        db.add(new_user)
        db.flush()

        new_arduino = Arduino(arduino_id=arduino_id, user_id=new_user.user_id, location=location)
        db.add(new_arduino)
        db.commit()

        return True, "Success", {'user_id': new_user.user_id, 'username': new_user.username, 'email': new_user.email}

    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig)
        if 'users_email_key' in error_msg: return False, "Email already registered", None
        if 'users_username_key' in error_msg: return False, "Username taken", None
        return False, "Registration failed", None
    except Exception as e:
        db.rollback()
        return False, str(e), None
    finally:
        db.close()

def add_arduino_to_user(user_id, arduino_id, location):
    db = SessionLocal()
    try:
        active_config = get_active_location_config()
        if location not in active_config: return False, "Unsupported location"

        location_record = db.query(Location).filter(Location.location == location).first()
        if not location_record:
            api_sources = active_config[location]
            wave_source = next((s for s in api_sources if s.get('type') == 'wave'), api_sources[0])
            wind_source = next((s for s in api_sources if s.get('type') == 'wind'), api_sources[-1])
            location_record = Location(location=location, wave_api_url=wave_source['url'], wind_api_url=wind_source['url'])
            db.add(location_record)
            db.flush()

        new_arduino = Arduino(arduino_id=arduino_id, user_id=user_id, location=location)
        db.add(new_arduino)
        db.commit()
        return True, "Arduino linked"
    except IntegrityError:
        db.rollback()
        return False, "Arduino ID already registered"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def get_user_lamp_data(email):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user: return None, None, None
        arduinos = db.query(Arduino).filter(Arduino.user_id == user.user_id).all()
        location = db.query(Location).filter(Location.location == user.location).first()
        return user, arduinos, location
    finally:
        db.close()

def update_user_location(user_id, new_location):
    db = SessionLocal()
    try:
        active_config = get_active_location_config()
        if new_location not in active_config: return False, "Unsupported location"

        location_record = db.query(Location).filter(Location.location == new_location).first()
        if not location_record:
            api_sources = active_config[new_location]
            wave_source = next((s for s in api_sources if s.get('type') == 'wave'), api_sources[0])
            wind_source = next((s for s in api_sources if s.get('type') == 'wind'), api_sources[-1])
            location_record = Location(location=new_location, wave_api_url=wave_source['url'], wind_api_url=wind_source['url'])
            db.add(location_record)

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user: return False, "User not found"
        user.location = new_location
        db.commit()
        return True, "Location updated"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def cleanup_expired_password_reset_tokens():
    from datetime import datetime, timezone, timedelta
    db = SessionLocal()
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        deleted_count = db.query(PasswordResetToken).filter(
            (PasswordResetToken.created_at < cutoff_time) |
            (PasswordResetToken.used_at.isnot(None)) |
            PasswordResetToken.is_invalidated
        ).delete(synchronize_session=False)
        db.commit()
        return deleted_count
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == '__main__':
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise