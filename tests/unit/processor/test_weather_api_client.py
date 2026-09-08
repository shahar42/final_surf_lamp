"""
Unit tests for surf-lamp-processor/weather_api_client.py

HTTP is mocked with the `responses` library. time.sleep is patched out because
the client's retry delays are 30-120 seconds.
"""

import json

import pytest
import requests
import responses
from freezegun import freeze_time

import weather_api_client
from weather_api_client import fetch_surf_data, fetch_surf_data_with_fallback

from .conftest import FORECAST_URL, FORECAST_URL_NO_UNIT, MARINE_URL, OWM_URL

FROZEN = "2026-01-15 10:30:00"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr(weather_api_client.time, "sleep", lambda s: calls.append(s))
    return calls


@pytest.mark.unit
class TestFallbackOrder:
    @responses.activate
    @freeze_time(FROZEN)
    def test_fallback_tries_priority_order(self, forecast_payload, owm_payload):
        responses.add(responses.GET, FORECAST_URL, status=503)
        responses.add(responses.GET, OWM_URL, json=owm_payload)

        out = fetch_surf_data_with_fallback(None, [FORECAST_URL, OWM_URL])

        assert out["wind_speed_mps"] == 6.7
        assert [c.request.url for c in responses.calls] == [FORECAST_URL, OWM_URL]

    @responses.activate
    @freeze_time(FROZEN)
    def test_first_success_stops_chain(self, forecast_payload):
        responses.add(responses.GET, FORECAST_URL, json=forecast_payload)
        responses.add(responses.GET, OWM_URL, json={"wind": {"speed": 99}})

        out = fetch_surf_data_with_fallback(None, [FORECAST_URL, OWM_URL])

        assert out["wind_speed_mps"] != 99
        assert len(responses.calls) == 1

    @responses.activate
    def test_all_fail_returns_none_not_raise(self):
        responses.add(responses.GET, FORECAST_URL, status=500)
        responses.add(responses.GET, OWM_URL, status=500)
        assert fetch_surf_data_with_fallback(None, [FORECAST_URL, OWM_URL]) is None

    def test_no_endpoints_returns_none(self):
        assert fetch_surf_data_with_fallback(None, []) is None


@pytest.mark.unit
class TestSingleFetch:
    @responses.activate
    @freeze_time(FROZEN)
    def test_success_returns_standardized(self, marine_payload):
        responses.add(responses.GET, MARINE_URL, json=marine_payload)
        out = fetch_surf_data(None, MARINE_URL)
        assert out["wave_height_m"] == marine_payload["hourly"]["wave_height"][10]

    def test_open_meteo_wind_without_ms_unit_is_refused_before_any_request(self):
        """Without &wind_speed_unit=ms Open-Meteo returns km/h, ~3.6x too high.
        The client must refuse the URL rather than poison every lamp at the beach."""
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(responses.GET, FORECAST_URL_NO_UNIT, json={})
            assert fetch_surf_data(None, FORECAST_URL_NO_UNIT) is None
            assert len(rsps.calls) == 0

    @responses.activate
    def test_non_200_counts_as_failure(self):
        responses.add(responses.GET, MARINE_URL, status=404)
        assert fetch_surf_data(None, MARINE_URL) is None

    @responses.activate
    def test_malformed_json_counts_as_failure(self):
        responses.add(responses.GET, MARINE_URL, body="<html>not json</html>", status=200)
        assert fetch_surf_data(None, MARINE_URL) is None

    @responses.activate
    def test_timeout_retries_then_fails(self, no_sleep):
        responses.add(responses.GET, MARINE_URL, body=requests.exceptions.Timeout())
        responses.add(responses.GET, MARINE_URL, body=requests.exceptions.Timeout())
        responses.add(responses.GET, MARINE_URL, body=requests.exceptions.Timeout())

        assert fetch_surf_data(None, MARINE_URL) is None
        assert len(responses.calls) == 3
        assert no_sleep == [30, 60]  # exponential backoff between the three attempts

    @responses.activate
    @freeze_time(FROZEN)
    def test_timeout_then_success(self, marine_payload, no_sleep):
        responses.add(responses.GET, MARINE_URL, body=requests.exceptions.Timeout())
        responses.add(responses.GET, MARINE_URL, json=marine_payload)

        out = fetch_surf_data(None, MARINE_URL)
        assert out is not None
        assert no_sleep == [30]

    @responses.activate
    @freeze_time(FROZEN)
    def test_rate_limit_429_retries_with_backoff(self, marine_payload, no_sleep):
        responses.add(responses.GET, MARINE_URL, status=429)
        responses.add(responses.GET, MARINE_URL, json=marine_payload)

        out = fetch_surf_data(None, MARINE_URL)
        assert out is not None
        assert no_sleep == [60]

    @responses.activate
    def test_api_key_sent_as_bearer(self):
        responses.add(responses.GET, OWM_URL, json={"wind": {"speed": 1, "deg": 2}})
        fetch_surf_data("secret", OWM_URL)
        assert responses.calls[0].request.headers["Authorization"] == "Bearer secret"

    @responses.activate
    def test_blank_api_key_not_sent(self):
        responses.add(responses.GET, OWM_URL, json={"wind": {"speed": 1, "deg": 2}})
        fetch_surf_data("  ", OWM_URL)
        assert "Authorization" not in responses.calls[0].request.headers

    @responses.activate
    def test_user_agent_identifies_the_processor(self):
        responses.add(responses.GET, OWM_URL, json={"wind": {"speed": 1, "deg": 2}})
        fetch_surf_data(None, OWM_URL)
        assert responses.calls[0].request.headers["User-Agent"].startswith("SurfLamp-Agent")
