"""
Unit tests for surf-lamp-processor/surf_data_transformer.py

The transformer turns each upstream API payload into the one dict shape the
rest of the system understands. The hourly-index logic is the part with real
history: 469c752 fixed a local-vs-UTC mismatch that served the wrong hour.
"""

import pytest
from freezegun import freeze_time

from surf_data_transformer import (
    apply_conversions,
    calculate_wave_from_wind,
    extract_field_value,
    get_current_hour_index,
    normalize_low_values,
    standardize_surf_data,
)
from endpoint_configs import WAVE_CALCULATIONS

from .conftest import FORECAST_URL, ISRAMAR_URL, MARINE_URL, OWM_URL

# Fixtures cover 2026-01-15 00:00..23:00 UTC. 10:30 UTC -> index 10.
FROZEN = "2026-01-15 10:30:00"
IDX = 10


@pytest.mark.unit
class TestExtractFieldValue:
    def test_nested_dict_and_list_path(self):
        data = {"a": {"b": [10, {"c": 42}]}}
        assert extract_field_value(data, ["a", "b", 1, "c"]) == 42
        assert extract_field_value(data, ["a", "b", 0]) == 10

    def test_missing_key_returns_none(self):
        assert extract_field_value({"a": {}}, ["a", "b"]) is None

    def test_index_out_of_range_returns_none(self):
        assert extract_field_value({"a": [1]}, ["a", 5]) is None

    def test_type_mismatch_returns_none(self):
        assert extract_field_value({"a": 5}, ["a", "b"]) is None
        assert extract_field_value({"a": [1, 2]}, ["a", "x"]) is None

    def test_empty_path_returns_root(self):
        assert extract_field_value({"a": 1}, []) == {"a": 1}


@pytest.mark.unit
class TestCurrentHourIndex:
    @freeze_time(FROZEN)
    def test_current_hour_index_utc(self, marine_payload):
        """Regression for 469c752: the match is on the UTC hour, not server local time."""
        assert get_current_hour_index(marine_payload["hourly"]["time"]) == IDX

    @freeze_time("2026-01-15 10:59:59")
    def test_minutes_are_ignored(self, marine_payload):
        assert get_current_hour_index(marine_payload["hourly"]["time"]) == IDX

    @freeze_time("2026-01-16 03:00:00")
    def test_current_hour_index_missing_hour_falls_back_to_zero(self, marine_payload):
        """Payload for the wrong day -> index 0 rather than an exception."""
        assert get_current_hour_index(marine_payload["hourly"]["time"]) == 0

    def test_empty_array_falls_back_to_zero(self):
        assert get_current_hour_index([]) == 0

    def test_garbage_falls_back_to_zero(self):
        assert get_current_hour_index([None, 5]) == 0


@pytest.mark.unit
class TestConversions:
    def test_apply_conversion_function(self):
        conv = {"temperature_c": lambda k: k - 273.15}
        assert apply_conversions(293.15, conv, "temperature_c") == pytest.approx(20.0)

    def test_no_conversion_for_field_passes_through(self):
        assert apply_conversions(7, {"other": lambda x: 0}, "wind") == 7

    def test_none_value_or_none_conversions(self):
        assert apply_conversions(None, {}, "x") is None
        assert apply_conversions(5, None, "x") == 5

    def test_conversion_error_returns_original(self):
        assert apply_conversions("abc", {"x": lambda v: v - 1}, "x") == "abc"


@pytest.mark.unit
class TestWaveFromWind:
    CFG = WAVE_CALCULATIONS["formula"]

    def test_formula_matches_configured_coefficients(self):
        result = calculate_wave_from_wind(10.0, self.CFG)
        assert result["wave_height_m"] == pytest.approx(self.CFG["height_coefficient"] * 10.0)
        assert result["wave_period_s"] == pytest.approx(self.CFG["period_coefficient"] * 10.0 ** self.CFG["period_exponent"])

    def test_height_is_linear_in_wind(self):
        h1 = calculate_wave_from_wind(5.0, self.CFG)["wave_height_m"]
        h2 = calculate_wave_from_wind(10.0, self.CFG)["wave_height_m"]
        assert h2 == pytest.approx(2 * h1)

    @pytest.mark.parametrize("wind", [None, 0, -3])
    def test_no_wind_returns_empty(self, wind):
        assert calculate_wave_from_wind(wind, self.CFG) == {}

    def test_bad_config_returns_empty(self):
        assert calculate_wave_from_wind(5.0, {}) == {}


@pytest.mark.unit
class TestNormalizeLowValues:
    def test_tiny_values_rounded_up_so_lamp_never_sees_zero(self):
        d = {"wave_height_m": 0.05, "wave_period_s": 0.05, "wind_speed_mps": 0.05}
        normalize_low_values(d)
        assert d == {"wave_height_m": 0.1, "wave_period_s": 1.0, "wind_speed_mps": 0.1}

    def test_zero_and_normal_values_untouched(self):
        d = {"wave_height_m": 0.0, "wave_period_s": 8.0, "wind_speed_mps": 0.1}
        normalize_low_values(d)
        assert d == {"wave_height_m": 0.0, "wave_period_s": 8.0, "wind_speed_mps": 0.1}

    def test_missing_keys_ignored(self):
        d = {"other": 1}
        normalize_low_values(d)
        assert d == {"other": 1}


@pytest.mark.unit
class TestStandardize:
    @freeze_time(FROZEN)
    def test_open_meteo_marine_standardizes_current_hour(self, marine_payload):
        out = standardize_surf_data(marine_payload, MARINE_URL)
        assert out["wave_height_m"] == marine_payload["hourly"]["wave_height"][IDX]
        assert out["wave_period_s"] == marine_payload["hourly"]["wave_period"][IDX]
        assert out["wave_direction_deg"] == marine_payload["hourly"]["wave_direction"][IDX]
        assert out["source_endpoint"] == MARINE_URL
        assert "timestamp" in out
        assert "wind_speed_mps" not in out  # marine API says nothing about wind

    @freeze_time(FROZEN)
    def test_open_meteo_forecast_wind_standardizes_current_hour(self, forecast_payload):
        out = standardize_surf_data(forecast_payload, FORECAST_URL)
        assert out["wind_speed_mps"] == forecast_payload["hourly"]["wind_speed_10m"][IDX]
        assert out["wind_direction_deg"] == forecast_payload["hourly"]["wind_direction_10m"][IDX]
        assert "wave_height_m" not in out

    def test_openweathermap_wind_standardizes(self, owm_payload):
        """New fallback source (f80464d): current-conditions shape, no hourly array."""
        out = standardize_surf_data(owm_payload, OWM_URL)
        assert out["wind_speed_mps"] == 6.7
        assert out["wind_direction_deg"] == 245
        assert out["temperature_c"] == pytest.approx(20.0)
        assert "wave_height_m" not in out

    def test_isramar_custom_extraction(self, isramar_payload):
        out = standardize_surf_data(isramar_payload, ISRAMAR_URL)
        assert out["wave_height_m"] == 0.41
        assert out["wave_period_s"] == 3.5

    def test_isramar_without_parameters_yields_none_metadata_free(self):
        out = standardize_surf_data({"datetime": "x"}, ISRAMAR_URL)
        assert out == {}  # nothing extracted -> no timestamp/source added

    def test_unknown_endpoint_returns_none(self):
        assert standardize_surf_data({"a": 1}, "https://unknown-weather.example/x") is None

    @freeze_time(FROZEN)
    def test_missing_field_is_omitted_not_zeroed(self, marine_payload):
        """Only fields actually present are returned; the processor decides fallbacks."""
        del marine_payload["hourly"]["wave_period"]
        out = standardize_surf_data(marine_payload, MARINE_URL)
        assert "wave_height_m" in out
        assert "wave_period_s" not in out

    @freeze_time(FROZEN)
    def test_formula_method_derives_waves_from_wind(self, forecast_payload):
        out = standardize_surf_data(forecast_payload, FORECAST_URL, wave_calculation_method="formula")
        wind = forecast_payload["hourly"]["wind_speed_10m"][IDX]
        cfg = WAVE_CALCULATIONS["formula"]
        assert out["wave_height_m"] == pytest.approx(cfg["height_coefficient"] * wind)
        assert out["wave_period_s"] == pytest.approx(cfg["period_coefficient"] * wind ** cfg["period_exponent"])

    @freeze_time(FROZEN)
    def test_formula_method_does_not_override_api_waves(self, marine_payload):
        out = standardize_surf_data(marine_payload, MARINE_URL, wave_calculation_method="formula")
        assert out["wave_height_m"] == marine_payload["hourly"]["wave_height"][IDX]

    @freeze_time(FROZEN)
    def test_low_values_normalized_in_output(self, marine_payload):
        marine_payload["hourly"]["wave_height"][IDX] = 0.03
        out = standardize_surf_data(marine_payload, MARINE_URL)
        assert out["wave_height_m"] == 0.1
