"""
Processor integration fixtures: the real background_processor module wired
to the shared SQLite test database, with the weather fetch replaced by a
recorder so no HTTP happens.

background_processor builds its engine from DATABASE_URL at import; the
top-level conftest points that at a file-backed SQLite DB, so the processor
and the web app read and write the same tables here.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

import background_processor
import data_base

WAVE = {"wave_height_m": 1.4, "wave_period_s": 7.0}
WIND = {"wind_speed_mps": 6.0, "wind_direction_deg": 250}


@pytest.fixture(scope="session", autouse=True)
def processor_tables():
    data_base.Base.metadata.create_all(bind=background_processor.engine)
    yield
    data_base.Base.metadata.drop_all(bind=background_processor.engine)


@pytest.fixture(autouse=True)
def clean_tables():
    with background_processor.engine.begin() as conn:
        for table in reversed(data_base.Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture
def session():
    Session = sessionmaker(bind=background_processor.engine, expire_on_commit=False)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def seed(session):
    """seed(location_names, with_rows=True) -> creates arduinos (and, unless
    with_rows=False, a locations row with 'old' readings) for each name."""
    def _seed(names, with_rows=True, old_values=None, last_value_change=None):
        old_values = old_values or {"wave_height_m": 0.5, "wave_period_s": 5.0, "wind_speed_mps": 2.0, "wind_direction_deg": 90}
        user = data_base.User(username="proc", email="proc@example.com", password_hash="x", location=names[0],
                              theme="classic_surf", preferred_output="meters", sport_type="surfing")
        session.add(user)
        session.flush()
        for i, name in enumerate(names):
            if with_rows:
                session.add(data_base.Location(
                    location=name, wave_api_url="w", wind_api_url="x",
                    consecutive_identical_updates=0,
                    last_value_change=last_value_change or datetime(2026, 1, 1),
                    **old_values,
                ))
            session.add(data_base.Arduino(arduino_id=100 + i, user_id=user.user_id, location=name))
        session.commit()
    return _seed


class FetchRecorder:
    """Stand-in for weather_api_client.fetch_surf_data_with_fallback.

    Decides wave vs wind by URL and returns canned data, or None for URLs in
    `fail`. Records every call so tests can count fetches per cycle."""

    def __init__(self, wave=WAVE, wind=WIND):
        self.wave = dict(wave)
        self.wind = dict(wind)
        self.fail = set()      # substrings of URLs that should fail
        self.calls = []        # list of endpoint lists

    def __call__(self, api_key, endpoints, wave_calculation_method="api"):
        self.calls.append(list(endpoints))
        for url in endpoints:
            if any(f in url for f in self.fail):
                continue
            if "marine-api" in url:
                return dict(self.wave)
            if "wind_speed_10m" in url or "openweathermap" in url:
                return dict(self.wind)
        return None

    @property
    def wave_calls(self):
        return [c for c in self.calls if any("marine-api" in u for u in c)]

    @property
    def wind_calls(self):
        return [c for c in self.calls if any("wind_speed_10m" in u or "openweathermap" in u for u in c)]


@pytest.fixture
def fetch(monkeypatch):
    rec = FetchRecorder()
    monkeypatch.setattr(background_processor, "fetch_surf_data_with_fallback", rec)
    return rec


def location_row(session, name):
    session.expire_all()
    return session.query(data_base.Location).filter_by(location=name).one()
