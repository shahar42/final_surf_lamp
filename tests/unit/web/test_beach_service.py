"""
Unit tests for web_and_database/locations/beach_service.py

URL generation is what the background processor actually fetches. A wrong
query parameter here silently produces wrong surf data for every lamp at
that beach, so each parameter the processor depends on is asserted.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from locations.beach_service import (
    generate_wave_api_url,
    generate_wind_api_url,
    generate_wind_api_url_openweathermap,
    get_api_urls_for_beach,
    get_beach_coordinates,
    is_valid_beach,
)

LAT, LNG = 32.4425, 34.8683  # Sdot Yam


def _query(url):
    parsed = urlparse(url)
    return parsed.netloc, parsed.path, parse_qs(parsed.query)


@pytest.mark.unit
class TestWaveUrl:
    def test_wave_url_targets_marine_api_with_coords(self):
        host, path, q = _query(generate_wave_api_url(LAT, LNG))
        assert host == "marine-api.open-meteo.com"
        assert path == "/v1/marine"
        assert q["latitude"] == [str(LAT)]
        assert q["longitude"] == [str(LNG)]

    def test_wave_url_requests_height_and_period(self):
        _, _, q = _query(generate_wave_api_url(LAT, LNG))
        assert set(q["hourly"][0].split(",")) == {"wave_height", "wave_period"}

    def test_wave_url_uses_utc(self):
        """Regression for 469c752: hourly index must be computed in UTC."""
        _, _, q = _query(generate_wave_api_url(LAT, LNG))
        assert q["timezone"] == ["UTC"]


@pytest.mark.unit
class TestWindUrl:
    def test_wind_url_targets_forecast_api_with_coords(self):
        host, path, q = _query(generate_wind_api_url(LAT, LNG))
        assert host == "api.open-meteo.com"
        assert path == "/v1/forecast"
        assert q["latitude"] == [str(LAT)]
        assert q["longitude"] == [str(LNG)]

    def test_wind_url_requests_speed_and_direction_in_mps(self):
        """The processor validates wind_speed_unit=ms; km/h would be ~3.6x too high."""
        _, _, q = _query(generate_wind_api_url(LAT, LNG))
        assert set(q["hourly"][0].split(",")) == {"wind_speed_10m", "wind_direction_10m"}
        assert q["wind_speed_unit"] == ["ms"]

    def test_wind_url_uses_utc(self):
        _, _, q = _query(generate_wind_api_url(LAT, LNG))
        assert q["timezone"] == ["UTC"]


@pytest.mark.unit
class TestOpenWeatherMapFallback:
    def test_owm_url_none_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)
        assert generate_wind_api_url_openweathermap(LAT, LNG) is None

    def test_owm_url_with_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key-123")
        host, path, q = _query(generate_wind_api_url_openweathermap(LAT, LNG))
        assert host == "api.openweathermap.org"
        assert path == "/data/2.5/weather"
        assert q["lat"] == [str(LAT)]
        assert q["lon"] == [str(LNG)]
        assert q["appid"] == ["test-key-123"]


@pytest.mark.unit
class TestBeachLookups:
    def test_is_valid_beach(self):
        assert is_valid_beach("Sdot Yam") is True
        assert is_valid_beach("sdot yam") is True
        assert is_valid_beach("Atlantis") is False

    def test_get_beach_coordinates(self):
        assert get_beach_coordinates("Sdot Yam") == (LAT, LNG)
        assert get_beach_coordinates("Atlantis") is None

    def test_get_api_urls_returns_wave_then_wind(self):
        wave, wind = get_api_urls_for_beach("Sdot Yam")
        assert wave == generate_wave_api_url(LAT, LNG)
        assert wind == generate_wind_api_url(LAT, LNG)

    def test_get_api_urls_unknown_beach_none(self):
        assert get_api_urls_for_beach("Atlantis") is None
