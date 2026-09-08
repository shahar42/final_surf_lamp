"""
Unit tests for web_and_database/forms.py

Forms are exercised inside a throwaway Flask request context with CSRF off,
so no database, Redis, or the real app factory is involved.
"""

import pytest
from flask import Flask
from werkzeug.datastructures import MultiDict

from forms import LoginForm, RegistrationForm, SanitizedStringField, sanitize_input, validate_location_choice
from security_config import SecurityConfig

MAX_ID = 16777215  # 2^24 - 1, MAC-derived Arduino IDs
BEACHES = ["Sdot Yam", "Hilton Beach (Tel Aviv)"]


@pytest.fixture
def ctx():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "forms-test"
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_request_context(method="POST"):
        yield


def registration(**overrides):
    data = {
        "name": "Surf Fan",
        "email": "fan@example.com",
        "password": "correct-horse-battery",
        "arduino_id": "14",
        "location": "Sdot Yam",
        "sport_type": "surfing",
        "units": "meters",
    }
    data.update(overrides)
    form = RegistrationForm(formdata=MultiDict(data))
    form.location.choices = [(b, b) for b in BEACHES]
    return form


@pytest.mark.unit
class TestRegistrationArduinoId:
    def test_accepts_legacy_small_id(self, ctx):
        form = registration(arduino_id="14")
        assert form.validate(), form.errors
        assert form.arduino_id.data == 14

    def test_accepts_max_24bit_id(self, ctx):
        """MAC-derived IDs go up to 2^24 - 1 (see 9790cc8)."""
        form = registration(arduino_id=str(MAX_ID))
        assert form.validate(), form.errors

    @pytest.mark.parametrize("bad", ["0", "-1", str(MAX_ID + 1), "abc", ""])
    def test_rejects_out_of_range_or_non_numeric(self, ctx, bad):
        form = registration(arduino_id=bad)
        assert not form.validate()
        assert "arduino_id" in form.errors


@pytest.mark.unit
class TestRegistrationOtherFields:
    def test_password_length_bounds_from_security_config(self, ctx):
        too_short = "a" * (SecurityConfig.PASSWORD_MIN_LENGTH - 1)
        too_long = "a" * (SecurityConfig.PASSWORD_MAX_LENGTH + 1)
        assert not registration(password=too_short).validate()
        assert not registration(password=too_long).validate()
        assert registration(password="a" * SecurityConfig.PASSWORD_MIN_LENGTH).validate()

    def test_location_must_be_a_known_choice(self, ctx):
        form = registration(location="Atlantis")
        assert not form.validate()
        assert "location" in form.errors

    def test_sport_type_must_be_a_known_choice(self, ctx):
        assert not registration(sport_type="skiing").validate()

    def test_units_must_be_meters_or_feet(self, ctx):
        assert not registration(units="furlongs").validate()

    def test_name_rejects_html_and_symbols(self, ctx):
        # Sanitizer strips the tags first, leaving 'alert(1)' which fails the regexp on '(' ')'.
        assert not registration(name="<script>alert(1)</script>").validate()

    def test_name_allows_hyphen_and_apostrophe(self, ctx):
        assert registration(name="O'Neil-Smith").validate()


@pytest.mark.unit
class TestEmailValidation:
    def test_email_whitespace_stripped_case_preserved(self, ctx):
        """Case is preserved on purpose; the case-insensitive compare happens at login."""
        form = registration(email="  Fan@Example.com  ")
        assert form.validate(), form.errors
        assert form.email.data == "Fan@Example.com"

    @pytest.mark.parametrize("bad", ["a..b@example.com", ".a@example.com", "a@b@example.com"])
    def test_suspicious_email_patterns_rejected(self, ctx, bad):
        assert not registration(email=bad).validate()

    def test_login_form_strips_email_whitespace(self, ctx):
        form = LoginForm(formdata=MultiDict({"email": " fan@example.com ", "password": "x"}))
        assert form.validate(), form.errors
        assert form.email.data == "fan@example.com"


@pytest.mark.unit
class TestSanitization:
    def test_sanitize_input_strips_tags_keeps_text(self):
        assert sanitize_input("<b>hello</b> <script>x</script>") == "hello x"

    def test_sanitize_input_removes_control_chars_keeps_newline_tab(self):
        """No raw control character may survive; newline and tab are the only
        exceptions. (bleach may substitute U+FFFD for some control bytes before
        the filter runs, so the assertion is on what remains, not on equality.)"""
        out = sanitize_input("a\x00b\x07c\x1bd\ne\tf")
        assert all(ord(ch) >= 32 or ch in "\n\t" for ch in out)
        assert "\n" in out and "\t" in out
        assert out.startswith("a") and out.endswith("f")

    def test_sanitize_input_caps_length(self):
        out = sanitize_input("x" * (SecurityConfig.MAX_INPUT_LENGTH + 50))
        assert len(out) == SecurityConfig.MAX_INPUT_LENGTH

    def test_sanitize_input_empty(self):
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""

    def test_sanitized_field_trims_and_strips_html(self, ctx):
        form = registration(name="  <i>Surf</i> Fan  ")
        assert form.name.data == "Surf Fan"

    def test_validate_location_choice(self):
        assert validate_location_choice("Sdot Yam", BEACHES) is True
        assert validate_location_choice("Atlantis", BEACHES) is False
