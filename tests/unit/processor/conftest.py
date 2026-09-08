"""Shared fixtures for processor unit tests: loads the API samples once."""

import json
import os

import pytest

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "fixtures", "api_responses")

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine?latitude=32.4425&longitude=34.8683&hourly=wave_height,wave_period&timezone=UTC"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast?latitude=32.4425&longitude=34.8683&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=UTC"
FORECAST_URL_NO_UNIT = FORECAST_URL.replace("&wind_speed_unit=ms", "")
OWM_URL = "https://api.openweathermap.org/data/2.5/weather?lat=32.4425&lon=34.8683&appid=test"
ISRAMAR_URL = "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json"


def _load(name):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def marine_payload():
    return _load("open_meteo_marine.json")


@pytest.fixture
def forecast_payload():
    return _load("open_meteo_forecast.json")


@pytest.fixture
def owm_payload():
    return _load("openweathermap_weather.json")


@pytest.fixture
def isramar_payload():
    return _load("isramar_station.json")
