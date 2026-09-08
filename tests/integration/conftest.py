"""
Integration fixtures: the real Flask app, a file-backed SQLite database
(via the DATABASE_URL set in tests/conftest.py), and a fakeredis client
injected into redis_manager. No network, no Postgres, no real Redis.

The app is created once per session. Every test starts with empty tables
and empty in-process caches.
"""

import os
from datetime import datetime, time, timezone

import pytest
from sqlalchemy.orm import sessionmaker

LAMP_UA = {"User-Agent": "ESP32HTTPClient/1.0"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (test)"}
PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="session")
def flask_app():
    # The app factory reads REDIS_URL for the rate limiter's storage. Point it
    # at in-memory storage for the one moment the app is built, then drop the
    # variable again so redis_manager keeps seeing "no Redis configured".
    os.environ["REDIS_URL"] = "memory://"
    try:
        import app as app_module
    finally:
        os.environ.pop("REDIS_URL", None)

    flask_app = app_module.app
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,        # individual tests re-enable to test CSRF itself
        SESSION_COOKIE_SECURE=False,   # test client speaks http
    )

    from config import limiter
    limiter.enabled = False            # individual tests re-enable to test limits

    import data_base
    data_base.Base.metadata.create_all(bind=data_base.engine)
    yield flask_app
    data_base.Base.metadata.drop_all(bind=data_base.engine)


@pytest.fixture
def db_session(flask_app):
    """Session bound to the app engine; objects stay usable after commit."""
    import data_base
    Session = sessionmaker(bind=data_base.engine, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clean_state(flask_app, fake_redis):
    """Empty every table and every in-process cache before each test, and
    make redis_manager hand out the fakeredis client."""
    import data_base
    import redis_manager
    from utils import helpers, location_cache, rate_limit

    with data_base.engine.begin() as conn:
        for table in reversed(data_base.Base.metadata.sorted_tables):
            conn.execute(table.delete())

    location_cache._db_location_cache.clear()
    helpers._sunset_cache.clear()
    helpers._coordinates_cache.clear()
    rate_limit.location_changes.clear()
    redis_manager._db_write_history_fallback.clear()
    redis_manager.redis_client = fake_redis

    yield

    redis_manager.redis_client = None


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


# ---------------------------------------------------------------- factories

@pytest.fixture
def make_location(db_session):
    from data_base import Location

    def _make(name="Sdot Yam", wave_height_m=1.2, wave_period_s=8.0, wind_speed_mps=5.0,
              wind_direction_deg=180, consecutive_identical_updates=0, last_updated=None):
        loc = Location(
            location=name,
            wave_api_url="https://marine-api.open-meteo.com/test",
            wind_api_url="https://api.open-meteo.com/test",
            wave_height_m=wave_height_m,
            wave_period_s=wave_period_s,
            wind_speed_mps=wind_speed_mps,
            wind_direction_deg=wind_direction_deg,
            consecutive_identical_updates=consecutive_identical_updates,
            last_updated=last_updated or datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(loc)
        db_session.commit()
        return loc

    return _make


@pytest.fixture
def make_user(db_session, flask_app):
    from config import bcrypt
    from data_base import User

    counter = {"n": 0}

    def _make(email=None, location="Sdot Yam", password=PASSWORD, **fields):
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        with flask_app.app_context():
            password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        defaults = dict(
            username=fields.pop("username", f"user{counter['n']}"),
            email=email,
            password_hash=password_hash,
            location=location,
            theme="classic_surf",
            preferred_output="meters",
            sport_type="surfing",
            wave_threshold_m=1.0,
            wave_threshold_max_m=3.0,
            wind_threshold_knots=15.0,
            wind_threshold_max_knots=40.0,
            brightness_level=1.0,
            quiet_times_enabled=False,
            off_times_enabled=False,
        )
        defaults.update(fields)
        user = User(**defaults)
        db_session.add(user)
        db_session.commit()
        return user

    return _make


@pytest.fixture
def make_arduino(db_session):
    from data_base import Arduino

    def _make(arduino_id, user, location="Sdot Yam", **fields):
        ard = Arduino(arduino_id=arduino_id, user_id=user.user_id, location=location, **fields)
        db_session.add(ard)
        db_session.commit()
        return ard

    return _make


@pytest.fixture
def lamp(make_location, make_user, make_arduino):
    """One beach, one owner, one lamp with id 14. Returns (location, user, arduino)."""
    loc = make_location()
    user = make_user(location=loc.location)
    ard = make_arduino(14, user, loc.location)
    return loc, user, ard


@pytest.fixture
def login(client):
    """Put a user into the session the way auth._set_user_session does."""
    def _login(user):
        with client.session_transaction() as s:
            s["user_email"] = user.email
            s["user_id"] = user.user_id
            s["username"] = user.username
        return client
    return _login


def decode_v3(payload: bytes):
    """Decode a 26-byte V3 response the way the firmware does."""
    import message_wrapper
    handler = message_wrapper.MessageHandler()
    parsed = handler.parse(list(payload))
    assert parsed is not None, "V3 payload failed CRC/length validation"
    return parsed.surf, parsed.settings


def flashes(client):
    """Read pending flash messages from the session without rendering a page."""
    with client.session_transaction() as s:
        return [msg for _category, msg in s.get("_flashes", [])]


ALL_DAY = dict(off_times_enabled=True, off_time_start=time(0, 0), off_time_end=time(23, 59))
