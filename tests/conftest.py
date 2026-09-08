"""
Shared test fixtures for the Surf Lamp test suite.

Provides:
- Environment setup (SECRET_KEY, no REDIS_URL)
- fakeredis for Redis-dependent tests
- freezegun helpers
- Mock LOCATION_TIMEZONES for timezone-dependent tests
"""

import os
import sys
import pytest

# Ensure test environment variables are set BEFORE any app imports
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.pop('REDIS_URL', None)  # Ensure no real Redis in unit tests

# Add project paths for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, 'web_and_database')
PROCESSOR_DIR = os.path.join(PROJECT_ROOT, 'surf-lamp-processor')

for path in [PROJECT_ROOT, WEB_DIR, PROCESSOR_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def fake_redis():
    """Provide a fakeredis client for tests that need Redis.

    Hard import on purpose: a missing dev dependency must fail loudly,
    not silently skip the Redis tests. Install with:
        python -m pip install -r requirements-dev.txt
    """
    import fakeredis
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_location_timezones(monkeypatch):
    """Provide a mock LOCATION_TIMEZONES dict for timezone tests.

    Includes two locations in different timezones for cross-timezone testing.
    """
    mock_timezones = {
        "Hilton Beach (Tel Aviv)": "Asia/Jerusalem",
        "Gordon Beach (Tel Aviv)": "Asia/Jerusalem",
        "Bat Galim (Haifa)": "Asia/Jerusalem",
        "Waikiki Beach (Honolulu)": "Pacific/Honolulu",
        "Test Beach UTC": "UTC",
    }
    # Patch wherever LOCATION_TIMEZONES is used
    try:
        import data_base
        monkeypatch.setattr(data_base, 'LOCATION_TIMEZONES', mock_timezones)
    except (ImportError, AttributeError):
        pass
    try:
        from utils import helpers
        monkeypatch.setattr(helpers, 'LOCATION_TIMEZONES', mock_timezones)
    except (ImportError, AttributeError):
        pass
    return mock_timezones
