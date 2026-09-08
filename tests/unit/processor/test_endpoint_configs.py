"""Unit tests for surf-lamp-processor/endpoint_configs.py"""

import pytest

from endpoint_configs import (
    FIELD_MAPPINGS,
    WAVE_CALCULATIONS,
    extract_isramar_data,
    get_endpoint_config,
    get_wave_calculation_config,
    list_supported_endpoints,
)

from .conftest import FORECAST_URL, ISRAMAR_URL, MARINE_URL, OWM_URL

META_KEYS = {"fallbacks", "conversions", "custom_extraction"}


@pytest.mark.unit
class TestEndpointMatching:
    @pytest.mark.parametrize("url,key", [
        (MARINE_URL, "marine-api.open-meteo.com"),
        (FORECAST_URL, "api.open-meteo.com"),
        (OWM_URL, "openweathermap.org"),
        (ISRAMAR_URL, "isramar.ocean.org.il"),
    ])
    def test_get_endpoint_config_matches_by_host(self, url, key):
        assert get_endpoint_config(url) is FIELD_MAPPINGS[key]

    def test_marine_and_forecast_do_not_collide(self):
        """'api.open-meteo.com' is a substring of neither marine host nor vice versa."""
        assert get_endpoint_config(MARINE_URL) is not get_endpoint_config(FORECAST_URL)

    def test_unknown_host_returns_none(self):
        assert get_endpoint_config("https://weather.example.com/v1") is None

    def test_list_supported_endpoints(self):
        assert set(list_supported_endpoints()) == set(FIELD_MAPPINGS)


@pytest.mark.unit
class TestMappingShape:
    def test_every_config_has_fallbacks_key(self):
        for host, cfg in FIELD_MAPPINGS.items():
            assert "fallbacks" in cfg, host

    def test_field_paths_are_lists(self):
        for host, cfg in FIELD_MAPPINGS.items():
            for field, path in cfg.items():
                if field in META_KEYS:
                    continue
                assert isinstance(path, list) and path, f"{host}.{field}"

    def test_open_meteo_hourly_paths_end_with_index_placeholder(self):
        """The transformer replaces the trailing int with the current-hour index."""
        for host in ("marine-api.open-meteo.com", "api.open-meteo.com"):
            for field, path in FIELD_MAPPINGS[host].items():
                if field in META_KEYS:
                    continue
                assert path[0] == "hourly" and isinstance(path[2], int), f"{host}.{field}"


@pytest.mark.unit
class TestWaveCalculation:
    def test_known_methods(self):
        assert get_wave_calculation_config("api") is WAVE_CALCULATIONS["api"]
        assert get_wave_calculation_config("formula") is WAVE_CALCULATIONS["formula"]

    def test_unknown_method_defaults_to_api(self):
        assert get_wave_calculation_config("magic") is WAVE_CALCULATIONS["api"]

    def test_formula_has_coefficients(self):
        f = WAVE_CALCULATIONS["formula"]
        assert f["height_coefficient"] > 0 and f["period_coefficient"] > 0 and 0 < f["period_exponent"] < 1


@pytest.mark.unit
class TestIsramarExtractor:
    def test_extracts_height_and_period(self):
        data = {"parameters": [
            {"name": "Significant wave height", "units": "m", "values": [0.41]},
            {"name": "Peak wave period", "units": "s", "values": [3.5]},
        ]}
        assert extract_isramar_data(data) == {"wave_height_m": 0.41, "wave_period_s": 3.5}

    def test_missing_parameters_returns_empty(self):
        assert extract_isramar_data({}) == {}

    def test_empty_values_skipped(self):
        data = {"parameters": [{"name": "Significant wave height", "values": []}]}
        assert extract_isramar_data(data) == {}

    def test_unrelated_parameters_ignored(self):
        data = {"parameters": [{"name": "Sea temperature", "values": [21.0]}]}
        assert extract_isramar_data(data) == {}
