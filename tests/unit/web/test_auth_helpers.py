"""
Unit tests for the pure helpers in web_and_database/blueprints/auth.py

_validate_arduino_id_from_qr is the gate every registration passes through:
the QR on the box carries ?id=N and this decides whether N is plausible.
"""

import pytest

from blueprints.auth import _validate_arduino_id_from_qr

MAX_ID = 99999999  # widest legacy lamp ID


@pytest.mark.unit
class TestQrArduinoId:
    def test_accepts_legacy_small_id(self):
        assert _validate_arduino_id_from_qr("14") == (14, None)

    def test_accepts_max_legacy(self):
        """This parameter only ever carries a legacy numeric lamp ID now."""
        assert _validate_arduino_id_from_qr(str(MAX_ID)) == (MAX_ID, None)

    def test_accepts_int_input(self):
        assert _validate_arduino_id_from_qr(6689108) == (6689108, None)

    @pytest.mark.parametrize("bad", ["0", "-1", str(MAX_ID + 1), "123456789"])
    def test_rejects_out_of_range(self, bad):
        value, error = _validate_arduino_id_from_qr(bad)
        assert value is None
        assert error

    @pytest.mark.parametrize("bad", ["abc", "12.5", "0x10"])
    def test_rejects_non_numeric(self, bad):
        value, error = _validate_arduino_id_from_qr(bad)
        assert value is None
        assert error

    @pytest.mark.parametrize("empty", ["", None])
    def test_absent_parameter_is_not_an_error(self, empty):
        """No ?id= is the normal case now: the user pastes the lamp's MAC on
        the form instead, so registration must not be blocked here."""
        assert _validate_arduino_id_from_qr(empty) == (None, None)

    def test_error_message_points_user_to_the_box(self):
        _, error = _validate_arduino_id_from_qr("0")
        assert "QR" in error
