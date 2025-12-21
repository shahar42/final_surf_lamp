"""Generate 1000 fake lamps with realistic data distribution"""

# TODO: Import Faker, SQLAlchemy models
# TODO: Import LOCATION_DISTRIBUTION from config

def generate_user(user_id, location):
    """Generate realistic user with Faker"""
    # TODO: fake.user_name(), fake.email(), random thresholds
    pass

def generate_lamp(lamp_id, user_id, arduino_id):
    """Link user to lamp with unique arduino_id (10001-11000)"""
    pass

def generate_conditions(lamp_id):
    """Realistic wave/wind data"""
    # TODO: Random wave_height_m (0.2-3.5), wind_speed_mps (0-15), etc.
    pass

def seed_database(engine, total_lamps=1000):
    """Bulk insert all data in single transaction"""
    # TODO: Build lists of users, lamps, conditions
    # TODO: Use SQLAlchemy Core bulk insert (fast)
    # TODO: Print summary
    pass

if __name__ == "__main__":
    # TODO: Create engine from TEST_DATABASE_URL
    # TODO: Call seed_database()
    pass
