"""
Unit tests for web_and_database/models/query_result.py

ArduinoQueryResult is the object every device endpoint builds its response
from. Its None-to-zero defaults are what stops a brand-new location (no
readings yet) from crashing the V1/V2/V3 handlers.
"""

from types import SimpleNamespace

import pytest

from config import STALE_DATA_THRESHOLD
from models.query_result import ArduinoQueryResult


def make_qr(**loc):
    location = SimpleNamespace(
        wave_height_m=loc.get("wave_height_m"),
        wave_period_s=loc.get("wave_period_s"),
        wind_speed_mps=loc.get("wind_speed_mps"),
        wind_direction_deg=loc.get("wind_direction_deg"),
        consecutive_identical_updates=loc.get("consecutive_identical_updates"),
    )
    return ArduinoQueryResult(
        arduino=SimpleNamespace(arduino_id=14),
        location=location,
        user=SimpleNamespace(location="Sdot Yam"),
    )


@pytest.mark.unit
class TestQueryResult:
    def test_properties_default_none_to_zero(self):
        qr = make_qr()
        assert qr.wave_height_m == 0.0
        assert qr.wave_period_s == 0.0
        assert qr.wind_speed_mps == 0.0
        assert qr.wind_direction_deg == 0

    def test_properties_pass_real_values_through(self):
        qr = make_qr(wave_height_m=1.5, wave_period_s=8.0, wind_speed_mps=4.2, wind_direction_deg=270)
        assert (qr.wave_height_m, qr.wave_period_s, qr.wind_speed_mps, qr.wind_direction_deg) == (1.5, 8.0, 4.2, 270)

    def test_identity_properties(self):
        qr = make_qr()
        assert qr.arduino_id == 14
        assert qr.user_location == "Sdot Yam"

    def test_is_stale_is_strictly_greater_than_threshold(self):
        assert make_qr(consecutive_identical_updates=STALE_DATA_THRESHOLD).is_stale is False
        assert make_qr(consecutive_identical_updates=STALE_DATA_THRESHOLD + 1).is_stale is True
        assert make_qr(consecutive_identical_updates=None).is_stale is False

    @pytest.mark.parametrize("missing", ["arduino", "location", "user"])
    def test_missing_component_raises(self, missing):
        parts = dict(arduino=SimpleNamespace(), location=SimpleNamespace(), user=SimpleNamespace())
        parts[missing] = None
        with pytest.raises(ValueError):
            ArduinoQueryResult(**parts)
