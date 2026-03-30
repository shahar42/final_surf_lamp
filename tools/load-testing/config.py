"""Test configuration - database URL, pool settings, test parameters"""

# Test DB on port 5433 (prod uses 5432)
TEST_DATABASE_URL = "postgresql://test_user:test_pass@localhost:5433/surf_lamp_test"

# Pool configs to test
POOL_CONFIGS = {
    'default': {'pool_size': 5, 'max_overflow': 10},
    'optimized': {'pool_size': 20, 'max_overflow': 30, 'pool_pre_ping': True}
}

# Test parameters
TOTAL_LAMPS = 1000
RAMP_UP_TIME_SEC = 1800  # 30 min
TEST_DURATION_SEC = 21600  # 6 hours
SPAWN_RATE = TOTAL_LAMPS / RAMP_UP_TIME_SEC

# Location distribution (realistic)
LOCATION_DISTRIBUTION = {
    "Tel Aviv, Israel": 150,
    "Haifa, Israel": 120,
    "Netanya, Israel": 100,
    # ... 15 total locations = 1000 lamps
}
