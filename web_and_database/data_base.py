import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
import datetime

# --- Database Setup ---
# Get the database URL from environment variables. This is crucial for deployment on Render.
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/surfboard_lamp')

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models (based on your provided schema) ---

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
    arduino_id = Column(Integer, unique=True, nullable=False)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="lamp")
    usage_configs = relationship("UsageLamps", back_populates="lamp", cascade="all, delete-orphan")

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
    
    lamp = relationship("Lamp", back_populates="usage_configs")
    website = relationship("DailyUsage", back_populates="lamp_configs")


# --- Database Interaction Function ---

def add_user_and_lamp(name, email, password_hash, lamp_id, arduino_id, location, theme, units):
    """
    Creates a new user, registers their lamp, and links it to the correct 
    data source based on location.
    Returns (True, "Success") on success, (False, "Error message") on failure.
    """
    db = SessionLocal()
    
    # Define which locations map to which website/API provider.
    LOCATIONS_WEBSITE_1 = [
        "Bondi Beach, Australia",
        "Pipeline, Hawaii, USA",
        "Jeffreys Bay, South Africa",
    ]
    
    target_website_url = "https://api.website2.com/surf"
    if location in LOCATIONS_WEBSITE_1:
        target_website_url = "https://api.website1.com/surf"

    try:
        # 1. Get or create the DailyUsage record for the target website
        website = db.query(DailyUsage).filter(DailyUsage.website_url == target_website_url).first()
        if not website:
            website = DailyUsage(website_url=target_website_url)
            db.add(website)
            db.flush()

        # 2. Create the new User
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

        # 3. Create the new Lamp and link it to the user
        new_lamp = Lamp(
            lamp_id=lamp_id,
            user_id=new_user.user_id,
            arduino_id=arduino_id
        )
        db.add(new_lamp)
        
        # 4. Link the Lamp to the Website via UsageLamps
        usage_lamp_link = UsageLamps(
            usage_id=website.usage_id,
            lamp_id=new_lamp.lamp_id,
            api_key=os.environ.get('DEFAULT_API_KEY', 'your_api_key_here'), # Get key from environment
            http_endpoint=f"{target_website_url}/{location.replace(' ', '_').lower()}"
        )
        db.add(usage_lamp_link)

        # 5. Commit the entire transaction
        db.commit()
        return True, "User and lamp registered successfully."

    except IntegrityError as e:
        db.rollback()
        return False, "An account with this email, username, lamp ID, or Arduino ID already exists."
    except Exception as e:
        db.rollback()
        return False, "An unexpected error occurred during registration."
    finally:
        db.close()

# --- Main execution block to create tables ---
if __name__ == '__main__':
    print("Creating database tables based on the defined schema...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
