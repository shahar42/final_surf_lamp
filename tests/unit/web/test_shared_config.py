"""
Unit tests for shared_config.py (repo root).

MULTI_SOURCE_LOCATIONS is built once at import from beaches.py, so tests that
need a different environment (OpenWeatherMap key present or absent) reload
the module under monkeypatched env and restore it afterwards.
"""

import importlib

import pytest

import shared_config
from locations.beaches import get_all_beach_names


@pytest.fixture
def reload_shared_config(monkeypatch):
    """Reload shared_config with the given env, then restore the original module state."""
    def _reload(**env):
        for k, v in env.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)
        return importlib.reload(shared_config)

    yield _reload
    # Restore whatever the real environment produces so later tests see production shape.
    monkeypatch.undo()
    importlib.reload(shared_config)


@pytest.mark.unit
class TestLocationSources:
    def test_beaches_py_is_the_primary_source(self):
        """Every beach gets an entry; nothing comes from the deprecated JSON."""
        assert set(shared_config.MULTI_SOURCE_LOCATIONS) == set(get_all_beach_names())

    def test_every_location_has_wave_and_wind_source(self):
        for name in get_all_beach_names():
            sources = shared_config.get_api_sources_for_location(name)
            assert len(sources["wave"]) == 1, name
            assert len(sources["wind"]) >= 1, name

    def test_wind_sources_only_open_meteo_without_key(self, reload_shared_config):
        cfg = reload_shared_config(OPENWEATHERMAP_API_KEY=None)
        wind = cfg.get_api_sources_for_location("Sdot Yam")["wind"]
        assert len(wind) == 1
        assert "api.open-meteo.com" in wind[0]

    def test_wind_sources_ordered_open_meteo_then_owm(self, reload_shared_config):
        """Regression for f80464d: OWM is the priority-2 fallback, never first."""
        cfg = reload_shared_config(OPENWEATHERMAP_API_KEY="k")
        wind = cfg.get_api_sources_for_location("Sdot Yam")["wind"]
        assert len(wind) == 2
        assert "api.open-meteo.com" in wind[0]
        assert "api.openweathermap.org" in wind[1]
        assert "appid=k" in wind[1]

    def test_wave_sources_never_include_owm(self, reload_shared_config):
        cfg = reload_shared_config(OPENWEATHERMAP_API_KEY="k")
        for name in get_all_beach_names():
            wave = cfg.get_api_sources_for_location(name)["wave"]
            assert all("openweathermap" not in u for u in wave), name

    def test_unknown_location_returns_empty_sources(self):
        assert shared_config.get_api_sources_for_location("Atlantis") == {"wave": [], "wind": []}

    def test_wave_calculation_method(self):
        assert shared_config.get_wave_calculation_method("Sdot Yam") == "api"
        # No wave source at all -> the processor derives waves from wind.
        assert shared_config.get_wave_calculation_method("Atlantis") == "formula"


@pytest.mark.unit
class TestConstants:
    def test_interval_sql_helpers_embed_the_constants(self):
        assert shared_config.get_online_interval_sql() == f"INTERVAL '{shared_config.LAMP_ONLINE_THRESHOLD_SECONDS} seconds'"
        assert shared_config.get_stale_interval_sql() == f"INTERVAL '{shared_config.LAMP_STALE_THRESHOLD_SECONDS} seconds'"

    def test_thresholds_are_ordered(self):
        assert shared_config.LAMP_ONLINE_THRESHOLD_SECONDS < shared_config.LAMP_STALE_THRESHOLD_SECONDS
        assert shared_config.MIN_LOCATION_API_CALL_INTERVAL_SECONDS <= shared_config.PROCESSOR_UPDATE_INTERVAL_SECONDS

    def test_brightness_levels_are_multipliers_in_unit_range(self):
        for name, value in shared_config.BRIGHTNESS_LEVELS.items():
            assert 0 < value <= 1.0, name
