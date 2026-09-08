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
import time
import pytest

# Production (Render) runs in UTC. Pin the test process to UTC too, so code
# that mixes naive datetime.now() with .astimezone() (sunset_calculator) and
# freezegun's frozen clock agree on every developer machine and in CI.
os.environ['TZ'] = 'UTC'
if hasattr(time, 'tzset'):
    time.tzset()

# Ensure test environment variables are set BEFORE any app imports
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.pop('REDIS_URL', None)  # Ensure no real Redis in unit tests
# background_processor.py exits at import without DATABASE_URL and builds an
# engine from it with pool_size/max_overflow, which SQLite's in-memory pool
# rejects. A file-backed SQLite URL in the temp dir accepts them and never
# reaches a real database.
import tempfile
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + os.path.join(tempfile.gettempdir(), 'surf_lamp_unit_tests.db'))

# Several modules call load_dotenv() at import. A developer's local .env could
# re-inject a real REDIS_URL/DATABASE_URL into the test process, so the loader
# is neutered for the whole test session. Tests set env explicitly instead.
try:
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False
except ImportError:
    pass

# Add project paths for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, 'web_and_database')
PROCESSOR_DIR = os.path.join(PROJECT_ROOT, 'surf-lamp-processor')
CPP_WRAPPER_DIR = os.path.join(PROJECT_ROOT, 'cpp_message_wrapper')

for path in [PROJECT_ROOT, WEB_DIR, PROCESSOR_DIR, CPP_WRAPPER_DIR]:
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
