from flask import Flask, send_file, jsonify
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func

app = Flask(__name__)

# Database setup
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    DB_USER = os.environ.get('DB_USER')
    DB_PASS = os.environ.get('DB_PASS')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_NAME = os.environ.get('DB_NAME')

    if all([DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME]):
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'
        user_id = Column(Integer, primary_key=True)
        username = Column(String(50))
        email = Column(String(100))
        location = Column(String(100))
        theme = Column(String(50))
        wave_threshold_m = Column(Float)
        wind_threshold_knots = Column(Integer)

    class Arduino(Base):
        __tablename__ = 'arduinos'
        arduino_id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users.user_id'))
        location = Column(String(255), ForeignKey('locations.location'))

    class Location(Base):
        __tablename__ = 'locations'
        location = Column(String(255), primary_key=True)
        wave_height_m = Column(Float)
        wave_period_s = Column(Float)
        wind_speed_mps = Column(Float)
        wind_direction_deg = Column(Integer)
        last_updated = Column(TIMESTAMP)

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/manifest.json')
def manifest():
    return send_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_file('sw.js', mimetype='application/javascript')

@app.route('/icon-192.png')
def icon192():
    return send_file('icon-192.png')

@app.route('/icon-512.png')
def icon512():
    return send_file('icon-512.png')

@app.route('/icon-maskable-192.png')
def icon_maskable_192():
    return send_file('icon-maskable-192.png')

@app.route('/icon-maskable-512.png')
def icon_maskable_512():
    return send_file('icon-maskable-512.png')

@app.route('/icon-1024.png')
def icon1024():
    return send_file('icon-1024.png')

@app.route('/icon-maskable-1024.png')
def icon_maskable_1024():
    return send_file('icon-maskable-1024.png')

@app.route('/favicon.ico')
def favicon():
    return send_file('favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/locations')
def get_locations():
    """Get all unique locations with active lamps that have current condition data"""
    if not DATABASE_URL:
        return jsonify({'error': 'Database not configured'}), 500

    session = Session()
    try:
        # Return locations that have both an Arduino assigned AND valid data
        locations = session.query(Location.location).distinct()\
            .join(Arduino, Location.location == Arduino.location)\
            .filter(Location.wave_height_m.isnot(None))\
            .all()
        return jsonify({'locations': [loc[0] for loc in locations]})
    finally:
        session.close()

@app.route('/api/lamp-by-location/<location>')
def get_lamp_by_location(location):
    """Get lamp data for a specific location"""
    if not DATABASE_URL:
        return jsonify({'error': 'Database not configured'}), 500

    session = Session()
    try:
        # Find ANY user at this location who has an Arduino (to get thresholds/theme)
        result = session.query(User, Arduino, Location)\
            .join(Arduino, User.user_id == Arduino.user_id)\
            .join(Location, Arduino.location == Location.location)\
            .filter(Location.location == location)\
            .first()

        if not result:
            return jsonify({'data_available': False, 'message': 'No lamp found for this location'}), 404

        user, arduino, loc_data = result

        # Return data in Arduino API format
        return jsonify({
            'data_available': True,
            'arduino_id': arduino.arduino_id,
            'wave_height_cm': int(loc_data.wave_height_m * 100) if loc_data.wave_height_m else 0,
            'wave_period_s': float(loc_data.wave_period_s) if loc_data.wave_period_s else 0.0,
            'wind_speed_mps': int(loc_data.wind_speed_mps) if loc_data.wind_speed_mps else 0,
            'wind_direction_deg': loc_data.wind_direction_deg,
            'wave_threshold_cm': int(user.wave_threshold_m * 100) if user.wave_threshold_m else 100,
            'wind_speed_threshold_knots': user.wind_threshold_knots or 15,
            'led_theme': user.theme or 'classic_surf',
            'quiet_hours_active': False,
            'last_updated': loc_data.last_updated.isoformat() if loc_data.last_updated else None
        })
    finally:
        session.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
