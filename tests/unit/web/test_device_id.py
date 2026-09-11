"""
Unit tests for web_and_database/utils/device_id.py

A lamp IS its MAC. This module only normalizes and formats, it never derives
anything, so there is no second implementation to drift from and no chance
of two lamps colliding. What these tests pin is that every way a MAC can be
written lands on ONE stored form, and that legacy numeric lamp IDs survive
untouched so no device in the field needs a visit.
"""

import pytest

from utils.device_id import (
    DEVICE_ID_MAX_LENGTH,
    InvalidDeviceIdentifier,
    format_device_id,
    is_legacy_numeric_id,
    is_mac_form,
    normalize_device_id,
)

MAC_WRITTEN_EVERY_WAY = [
    "A4:CF:12:34:56:78",
    "a4:cf:12:34:56:78",
    "A4-CF-12-34-56-78",
    "A4CF12345678",
    "a4cf12345678",
    "  A4:CF:12:34:56:78  ",
    "A4 CF 12 34 56 78",
    "a4cf.1234.5678",
]
STORED = "a4cf12345678"


@pytest.mark.unit
class TestNormalize:
    @pytest.mark.parametrize("written", MAC_WRITTEN_EVERY_WAY)
    def test_every_way_of_writing_a_mac_lands_on_one_stored_form(self, written):
        assert normalize_device_id(written) == STORED

    def test_stored_form_fits_the_column(self):
        assert len(STORED) == DEVICE_ID_MAX_LENGTH

    @pytest.mark.parametrize("legacy,expected", [
        ("8", "8"), ("14", "14"), (14, "14"), ("007", "7"), ("99999999", "99999999"),
    ])
    def test_legacy_numeric_ids_survive(self, legacy, expected):
        """Lamps in the field predate MACs; their IDs must still resolve."""
        assert normalize_device_id(legacy) == expected

    @pytest.mark.parametrize("bad", [
        "", "   ", None,
        "A4:CF:12:34:56",        # 5 octets
        "A4:CF:12:34:56:78:9A",  # 7 octets
        "A4:CF:12:34:56:ZZ",     # not hex
        "hello world",
        "0",                     # ids start at 1
        "-5",
        "12.5",
    ])
    def test_rejects_anything_else(self, bad):
        with pytest.raises(InvalidDeviceIdentifier):
            normalize_device_id(bad)

    def test_error_names_where_to_find_the_address(self):
        with pytest.raises(InvalidDeviceIdentifier, match="WiFi setup page"):
            normalize_device_id("")
        with pytest.raises(InvalidDeviceIdentifier, match="A4:CF:12:34:56:78"):
            normalize_device_id("nonsense")

    def test_normalizing_twice_changes_nothing(self):
        assert normalize_device_id(normalize_device_id("A4:CF:12:34:56:78")) == STORED
        assert normalize_device_id(normalize_device_id("14")) == "14"

    def test_different_macs_never_share_an_id(self):
        """The whole point of storing the MAC: no fold, so no collisions.
        These two differ only in the vendor octets, which a 24-bit fold of the
        device bytes would have discarded."""
        a = normalize_device_id("A4:CF:12:34:56:78")
        b = normalize_device_id("FF:EE:DD:34:56:78")
        assert a != b


@pytest.mark.unit
class TestFormatForDisplay:
    def test_mac_gets_its_colons_back(self):
        assert format_device_id(STORED) == "A4:CF:12:34:56:78"

    def test_round_trip_display_to_stored(self):
        assert normalize_device_id(format_device_id(STORED)) == STORED

    def test_legacy_id_shown_as_is(self):
        assert format_device_id("14") == "14"

    def test_empty_is_blank_not_an_error(self):
        """Used in templates, so it must never raise on a missing value."""
        assert format_device_id(None) == ""
        assert format_device_id("") == ""


@pytest.mark.unit
class TestClassification:
    @pytest.mark.parametrize("value,expected", [
        ("A4:CF:12:34:56:78", True), ("a4cf12345678", True),
        ("14", False), ("", False), (None, False),
    ])
    def test_is_mac_form(self, value, expected):
        assert is_mac_form(value) is expected

    @pytest.mark.parametrize("value,expected", [
        ("14", True), ("8", True), ("a4cf12345678", False), ("", False), (None, False),
    ])
    def test_is_legacy_numeric_id(self, value, expected):
        assert is_legacy_numeric_id(value) is expected

    def test_twelve_decimal_digits_read_as_a_mac(self):
        """Documented ambiguity: 12 decimal digits are also valid hex. No
        legacy lamp ID has 12 digits (they are small), so MAC wins."""
        assert is_mac_form("123456789012") is True
        assert normalize_device_id("123456789012") == "123456789012"
