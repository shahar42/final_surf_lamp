"""
Integration tests for background_processor.process_all_lamps against SQLite.

Covers the per-cycle contract: one wave fetch per active location, one
shared wind fetch per cycle (current Israel-only behaviour), staleness
counting, and how failures of one location or one source affect the rest.
"""

from datetime import datetime

import pytest

import background_processor

from .conftest import WAVE, WIND, location_row


@pytest.mark.integration
class TestFetchPlan:
    def test_one_wave_fetch_per_active_location(self, seed, fetch):
        seed(["Sdot Yam", "Hilton Beach (Tel Aviv)", "Bat Galim (Haifa)"])
        assert background_processor.process_all_lamps() is True
        assert len(fetch.wave_calls) == 3

    def test_shared_wind_fetched_once_per_cycle(self, seed, fetch):
        """Temporary Israel-only behaviour (f80464d): wind comes from Sdot Yam's
        sources once per cycle and is reused for every location. Delete this
        test when per-location wind fetching is restored."""
        seed(["Sdot Yam", "Hilton Beach (Tel Aviv)", "Bat Galim (Haifa)"])
        background_processor.process_all_lamps()
        assert len(fetch.wind_calls) == 1

    def test_location_without_arduinos_not_fetched(self, seed, fetch, session):
        import data_base
        seed(["Sdot Yam"])
        session.add(data_base.Location(location="Hilton Beach (Tel Aviv)", wave_api_url="w", wind_api_url="x"))
        session.commit()
        background_processor.process_all_lamps()
        assert len(fetch.wave_calls) == 1

    def test_no_active_locations_returns_false(self, fetch):
        assert background_processor.process_all_lamps() is False
        assert fetch.calls == []


@pytest.mark.integration
class TestDataWrittenToLocations:
    def test_readings_written_to_location_row(self, seed, fetch, session):
        seed(["Sdot Yam"])
        background_processor.process_all_lamps()
        row = location_row(session, "Sdot Yam")
        assert row.wave_height_m == WAVE["wave_height_m"]
        assert row.wave_period_s == WAVE["wave_period_s"]
        assert row.wind_speed_mps == WIND["wind_speed_mps"]
        assert row.wind_direction_deg == WIND["wind_direction_deg"]

    def test_changed_data_resets_counter_and_updates_last_value_change(self, seed, fetch, session):
        old = datetime(2026, 1, 1)
        seed(["Sdot Yam"], last_value_change=old)
        row = location_row(session, "Sdot Yam")
        row.consecutive_identical_updates = 4
        session.commit()

        background_processor.process_all_lamps()

        row = location_row(session, "Sdot Yam")
        assert row.consecutive_identical_updates == 0
        assert row.last_value_change > old

    def test_identical_data_increments_counter_keeps_last_value_change(self, seed, fetch, session):
        old = datetime(2026, 1, 1)
        seed(["Sdot Yam"], old_values={**WAVE, **WIND}, last_value_change=old)

        background_processor.process_all_lamps()
        background_processor.process_all_lamps()

        row = location_row(session, "Sdot Yam")
        assert row.consecutive_identical_updates == 2
        assert row.last_value_change == old

    def test_upsert_creates_missing_location_row_with_urls(self, seed, fetch, session):
        """An arduino can point at a beach with no locations row yet (fresh
        registration race); the processor must create it from beaches.py."""
        seed(["Sdot Yam"], with_rows=False)
        assert background_processor.process_all_lamps() is True
        row = location_row(session, "Sdot Yam")
        assert "marine-api.open-meteo.com" in row.wave_api_url
        assert "api.open-meteo.com" in row.wind_api_url
        assert row.wave_height_m == WAVE["wave_height_m"]


@pytest.mark.integration
class TestFailures:
    def test_wave_fetch_failure_skips_location_not_cycle(self, seed, fetch, session):
        seed(["Sdot Yam", "Hilton Beach (Tel Aviv)"])
        # Hilton's marine URL carries its own coordinates; fail only that one.
        from shared_config import get_api_sources_for_location
        hilton_wave = get_api_sources_for_location("Hilton Beach (Tel Aviv)")["wave"][0]
        fetch.fail.add(hilton_wave.split("?")[1])

        assert background_processor.process_all_lamps() is True

        assert location_row(session, "Sdot Yam").wave_height_m == WAVE["wave_height_m"]
        assert location_row(session, "Hilton Beach (Tel Aviv)").wave_height_m == 0.5  # untouched

    def test_wind_failure_still_updates_wave(self, seed, fetch, session):
        seed(["Sdot Yam"])
        fetch.fail.update({"wind_speed_10m", "openweathermap"})
        assert background_processor.process_all_lamps() is True
        assert location_row(session, "Sdot Yam").wave_height_m == WAVE["wave_height_m"]

    def test_wind_failure_zeroes_wind_fields_current_behaviour(self, seed, fetch, session):
        """Pinned, not endorsed: when every wind source fails the upsert writes
        wind_speed_mps = 0 rather than keeping the previous reading. Lamps then
        show calm wind during an API outage. Changing this is a product decision."""
        seed(["Sdot Yam"])
        fetch.fail.update({"wind_speed_10m", "openweathermap"})
        background_processor.process_all_lamps()
        row = location_row(session, "Sdot Yam")
        assert row.wind_speed_mps == 0.0
        assert row.wind_direction_deg == 0

    def test_cycle_returns_false_on_db_error(self, seed, fetch, monkeypatch):
        from sqlalchemy import create_engine
        seed(["Sdot Yam"])
        broken = create_engine("sqlite:////nonexistent-dir/never.db")
        monkeypatch.setattr(background_processor, "engine", broken)
        assert background_processor.process_all_lamps() is False
        assert fetch.calls == []


@pytest.mark.integration
class TestWindFallbackEndToEnd:
    def test_wind_falls_back_to_openweathermap_when_open_meteo_fails(self, seed, session, monkeypatch):
        """Real fetch_surf_data_with_fallback + mocked HTTP: Open-Meteo wind 503,
        OpenWeatherMap answers, lamps get OWM wind."""
        import json
        import responses
        import weather_api_client
        from tests.unit.processor.conftest import _load

        seed(["Sdot Yam"])
        monkeypatch.setattr(weather_api_client.time, "sleep", lambda s: None)

        from shared_config import get_api_sources_for_location
        real = get_api_sources_for_location("Sdot Yam")
        owm_url = "https://api.openweathermap.org/data/2.5/weather?lat=32.4425&lon=34.8683&appid=test"
        monkeypatch.setattr(background_processor, "get_api_sources_for_location",
                            lambda name: {"wave": real["wave"], "wind": [real["wind"][0], owm_url]})

        marine = _load("open_meteo_marine.json")
        owm = _load("openweathermap_weather.json")

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, real["wave"][0], json=marine)
            rsps.add(responses.GET, real["wind"][0], status=503)
            rsps.add(responses.GET, owm_url, json=owm)
            assert background_processor.process_all_lamps() is True

        row = location_row(session, "Sdot Yam")
        assert row.wind_speed_mps == owm["wind"]["speed"]
        assert row.wind_direction_deg == owm["wind"]["deg"]
        assert row.wave_height_m > 0
