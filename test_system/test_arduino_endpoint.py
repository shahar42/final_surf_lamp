"""
Integration test for Arduino data endpoint - the critical bridge in pull-based architecture

Tests:
1. Data transformation from database to Arduino-ready format
2. User-specific thresholds injection
3. Quiet hours timezone logic
4. Unit conversions (m → cm, proper wind speed)
5. Fallback behavior with missing data
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime, timezone
import json

# Set environment variables BEFORE importing app
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing'
os.environ['REDIS_URL'] = 'redis://localhost:6379'

# Add web_and_database to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
web_db_path = os.path.join(parent_dir, 'web_and_database')
sys.path.insert(0, web_db_path)

# Mock redis before importing Flask-Limiter
mock_redis = MagicMock()
mock_redis.__version__ = '5.0.0'
sys.modules['redis'] = mock_redis

from app import app
import pytz

@pytest.fixture
def client():
    """Create Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('app.SessionLocal')
def test_arduino_endpoint_complete_data(mock_session_local, client):
    """Test endpoint with complete surf data"""
    print("\n🧪 Test 1: Arduino endpoint with complete data")

    # Create mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Create mock ORM objects
    mock_lamp = MagicMock()
    mock_lamp.lamp_id = 1
    mock_lamp.user_id = 42
    mock_lamp.arduino_id = 4433

    mock_conditions = MagicMock()
    mock_conditions.wave_height_m = 1.2
    mock_conditions.wave_period_s = 6.5
    mock_conditions.wind_speed_mps = 8.3
    mock_conditions.wind_direction_deg = 315
    mock_conditions.last_updated = datetime(2025, 10, 13, 12, 30, 0, tzinfo=timezone.utc)

    mock_user = MagicMock()
    mock_user.user_id = 42
    mock_user.location = 'Hadera, Israel'
    mock_user.wave_threshold_m = 1.5
    mock_user.wind_threshold_knots = 25.0
    mock_user.theme = 'day'

    # Mock the query chain
    mock_query = MagicMock()
    mock_query.select_from.return_value = mock_query
    mock_query.outerjoin.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = (mock_lamp, mock_conditions, mock_user)

    mock_db.query.return_value = mock_query

    # Make request
    response = client.get('/api/arduino/4433/data')

    # Assertions
    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify data transformations
    assert data['wave_height_cm'] == 120  # 1.2m → 120cm
    assert data['wave_period_s'] == 6.5
    assert data['wind_speed_mps'] == 8  # Rounded to int
    assert data['wind_direction_deg'] == 315

    # Verify user thresholds
    assert data['wave_threshold_cm'] == 150  # 1.5m → 150cm
    assert data['wind_speed_threshold_knots'] == 25

    # Verify metadata
    assert data['data_available'] == True
    assert 'last_updated' in data
    assert data['led_theme'] == 'day'

    # Verify database session was closed
    mock_db.close.assert_called_once()

    print(f"✅ Complete data test passed: {json.dumps(data, indent=2)}")

@patch('app.SessionLocal')
def test_arduino_endpoint_missing_data(mock_session_local, client):
    """Test endpoint fallback behavior with no data"""
    print("\n🧪 Test 2: Arduino endpoint with missing data (safe defaults)")

    # Create mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Create mock ORM objects - NO CONDITIONS
    mock_lamp = MagicMock()
    mock_lamp.lamp_id = 1
    mock_lamp.arduino_id = 4433

    mock_user = MagicMock()
    mock_user.location = 'Tel Aviv, Israel'
    mock_user.wave_threshold_m = 1.0
    mock_user.wind_threshold_knots = 22.0
    mock_user.theme = 'day'

    # Mock the query chain - return None for conditions
    mock_query = MagicMock()
    mock_query.select_from.return_value = mock_query
    mock_query.outerjoin.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = (mock_lamp, None, mock_user)  # None conditions

    mock_db.query.return_value = mock_query

    response = client.get('/api/arduino/4433/data')

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify safe defaults
    assert data['wave_height_cm'] == 0
    assert data['wave_period_s'] == 0.0
    assert data['wind_speed_mps'] == 0
    assert data['wind_direction_deg'] == 0
    assert data['data_available'] == False

    # Verify thresholds still present
    assert data['wave_threshold_cm'] == 100
    assert data['wind_speed_threshold_knots'] == 22

    mock_db.close.assert_called_once()

    print(f"✅ Safe defaults test passed: data_available={data['data_available']}")

@patch('app.SessionLocal')
@patch('app.is_quiet_hours')
def test_quiet_hours_detection(mock_quiet_hours, mock_session_local, client):
    """Test quiet hours flag during nighttime (10 PM - 6 AM)"""
    print("\n🧪 Test 3: Quiet hours detection (timezone-aware)")

    # Mock quiet hours to return True
    mock_quiet_hours.return_value = True

    # Create mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Create mock ORM objects
    mock_lamp = MagicMock()
    mock_lamp.lamp_id = 1
    mock_lamp.arduino_id = 4433

    mock_conditions = MagicMock()
    mock_conditions.wave_height_m = 2.0
    mock_conditions.wave_period_s = 7.0
    mock_conditions.wind_speed_mps = 10.0
    mock_conditions.wind_direction_deg = 270
    mock_conditions.last_updated = datetime(2025, 10, 13, 22, 30, 0, tzinfo=timezone.utc)

    mock_user = MagicMock()
    mock_user.location = 'Hadera, Israel'
    mock_user.wave_threshold_m = 1.0
    mock_user.wind_threshold_knots = 22.0
    mock_user.theme = 'day'

    # Mock the query chain
    mock_query = MagicMock()
    mock_query.select_from.return_value = mock_query
    mock_query.outerjoin.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = (mock_lamp, mock_conditions, mock_user)

    mock_db.query.return_value = mock_query

    response = client.get('/api/arduino/4433/data')
    data = json.loads(response.data)

    # Verify quiet hours flag is set
    assert data['quiet_hours_active'] == True

    # Verify is_quiet_hours was called with correct location
    mock_quiet_hours.assert_called_once_with('Hadera, Israel')

    mock_db.close.assert_called_once()

    print(f"✅ Quiet hours test passed: quiet_hours_active={data['quiet_hours_active']}")

@patch('app.SessionLocal')
def test_arduino_endpoint_nonexistent_device(mock_session_local, client):
    """Test endpoint with Arduino ID that doesn't exist"""
    print("\n🧪 Test 4: Nonexistent Arduino device")

    # Create mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Mock the query chain - return None (lamp not found)
    mock_query = MagicMock()
    mock_query.select_from.return_value = mock_query
    mock_query.outerjoin.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None  # Arduino not found

    mock_db.query.return_value = mock_query

    response = client.get('/api/arduino/99999/data')

    # Should return 404
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

    mock_db.close.assert_called_once()

    print(f"✅ Nonexistent device test passed: status={response.status_code}")

@patch('app.SessionLocal')
def test_unit_conversions_precision(mock_session_local, client):
    """Test precise unit conversions for Arduino"""
    print("\n🧪 Test 5: Unit conversion precision")

    # Create mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Create mock ORM objects with decimal values
    mock_lamp = MagicMock()
    mock_lamp.lamp_id = 1
    mock_lamp.arduino_id = 4433

    mock_conditions = MagicMock()
    mock_conditions.wave_height_m = 0.42    # Should become 42cm
    mock_conditions.wave_period_s = 4.7
    mock_conditions.wind_speed_mps = 6.83   # Should be rounded to 7
    mock_conditions.wind_direction_deg = 127
    mock_conditions.last_updated = datetime.now(timezone.utc)

    mock_user = MagicMock()
    mock_user.location = 'Tel Aviv, Israel'
    mock_user.wave_threshold_m = 0.75  # 75cm
    mock_user.wind_threshold_knots = 15.5
    mock_user.theme = 'day'

    # Mock the query chain
    mock_query = MagicMock()
    mock_query.select_from.return_value = mock_query
    mock_query.outerjoin.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = (mock_lamp, mock_conditions, mock_user)

    mock_db.query.return_value = mock_query

    response = client.get('/api/arduino/4433/data')
    data = json.loads(response.data)

    # Verify conversions
    assert data['wave_height_cm'] == 42  # 0.42m → 42cm
    assert data['wave_threshold_cm'] == 75  # 0.75m → 75cm
    assert data['wind_speed_mps'] == 7  # Rounded from 6.83
    assert data['wind_speed_threshold_knots'] == 16  # Rounded from 15.5

    mock_db.close.assert_called_once()

    print(f"✅ Unit conversion test passed:")
    print(f"   Wave: 0.42m → {data['wave_height_cm']}cm")
    print(f"   Wind: 6.83mps → {data['wind_speed_mps']}mps")

@patch('app.SessionLocal')
def test_arduino_endpoint_null_condition_fields(mock_session_local, client):
    """Test endpoint handles None values in condition fields gracefully"""
    print("\n🧪 Test 6: Null/None field handling (partial API failures)")

    # Create mock database session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # SCENARIO: Conditions object exists but all sensor fields are None
    # This happens when partial API failures occur or incomplete data writes
    mock_lamp = MagicMock()
    mock_lamp.lamp_id = 1
    mock_lamp.arduino_id = 4433

    mock_user = MagicMock()
    mock_user.location = 'Tel Aviv, Israel'
    mock_user.wave_threshold_m = 1.0
    mock_user.wind_threshold_knots = 22.0
    mock_user.theme = 'day'

    # Conditions object exists but ALL sensor fields are None
    mock_conditions = MagicMock()
    mock_conditions.wave_height_m = None
    mock_conditions.wave_period_s = None
    mock_conditions.wind_speed_mps = None
    mock_conditions.wind_direction_deg = None
    mock_conditions.last_updated = datetime.now(timezone.utc)

    # Mock the query chain
    mock_query = MagicMock()
    mock_query.select_from.return_value = mock_query
    mock_query.outerjoin.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = (mock_lamp, mock_conditions, mock_user)

    mock_db.query.return_value = mock_query

    response = client.get('/api/arduino/4433/data')

    # Should not crash (no 500 error)
    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify safe defaults from 'or 0' fallbacks
    assert data['wave_height_cm'] == 0
    assert data['wave_period_s'] == 0.0
    assert data['wind_speed_mps'] == 0
    assert data['wind_direction_deg'] == 0

    # data_available should be True (conditions object exists, unlike test 2)
    assert data['data_available'] == True

    # Verify thresholds still present
    assert data['wave_threshold_cm'] == 100
    assert data['wind_speed_threshold_knots'] == 22

    mock_db.close.assert_called_once()

    print(f"✅ Null field handling test passed:")
    print(f"   All sensor values correctly defaulted to 0")
    print(f"   data_available={data['data_available']} (conditions object exists)")

if __name__ == '__main__':
    # Run with pytest
    pytest.main([__file__, '-v', '-s'])
