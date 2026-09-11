"""
Unit tests for web_and_database/utils/device_id.py

This module must fold a MAC into the SAME 24-bit Arduino ID the firmware
derives at boot (Config.h getArduinoId). If the two ever disagree, a user
registers an ID no lamp will ever poll with, and the lamp looks dead
forever. The MAC_VECTORS below are the same cases the native firmware test
runs (tests/unit/firmware/Makefile passes them to test_arduino_id).
"""

import pytest

from utils.device_id import (
    MAX_ARDUINO_ID,
    InvalidDeviceIdentifier,
    arduino_id_from_mac,
    looks_like_mac,
    normalize_mac,
    parse_device_identifier,
)

# (mac as printed, expected arduino id)
# Firmware: id = (efuseMac >> 24) & 0xFFFFFF, where efuseMac holds octet 0 in
# the low byte. With the MAC printed m0:m1:m2:m3:m4:m5 that is
# m3 | m4<<8 | m5<<16.
MAC_VECTORS = [
    ("00:11:22:33:44:55", 0x554433),
    ("A4:CF:12:34:56:78", 0x785634),
    ("FF:FF:FF:FF:FF:FF", MAX_ARDUINO_ID),
    ("AA:BB:CC:00:00:01", 0x010000),
]


@pytest.mark.unit
class TestFirmwareParity:
    """The committed vectors drive BOTH folds: the Makefile feeds each row to
    the native test_arduino_id binary, and these tests check the same rows
    against the Python fold. Regenerate with gen_mac_vectors.py."""

    @staticmethod
    def _vectors():
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "unit", "firmware", "fixtures", "mac_vectors.txt",
        )
        with open(path) as f:
            return [line.split() for line in f if line.strip() and not line.startswith("#")]

    def test_committed_vectors_match_the_python_fold(self):
        for mac, _u64, expected in self._vectors():
            assert arduino_id_from_mac(mac) == int(expected), mac

    def test_efuse_u64_column_reflects_the_esp32_byte_order(self):
        """ESP.getEfuseMac() reads the 6-byte MAC array as a little-endian
        uint64, so printed octet 0 sits in the LOW byte. The firmware then
        takes (mac >> 24) & 0xFFFFFF."""
        for mac, u64_hex, expected in self._vectors():
            octets = [int(p, 16) for p in mac.split(":")]
            u64 = sum(octet << (8 * i) for i, octet in enumerate(octets))
            assert u64 == int(u64_hex, 16), mac
            folded = (u64 >> 24) & 0xFFFFFF
            assert (folded or 1) == int(expected), mac

    def test_vectors_cover_the_edges(self):
        ids = {int(expected) for _mac, _u64, expected in self._vectors()}
        assert 1 in ids, "missing the zero-NIC bump case"
        assert MAX_ARDUINO_ID in ids, "missing the all-ones case"


@pytest.mark.unit
class TestNormalizeMac:
    @pytest.mark.parametrize("written", [
        "A4:CF:12:34:56:78",
        "a4:cf:12:34:56:78",
        "A4-CF-12-34-56-78",
        "A4CF12345678",
        "a4cf12345678",
        "  A4:CF:12:34:56:78  ",
        "A4 CF 12 34 56 78",
        "a4cf.1234.5678",
    ])
    def test_accepts_every_common_way_a_mac_gets_copied(self, written):
        assert normalize_mac(written) == "A4:CF:12:34:56:78"

    @pytest.mark.parametrize("bad", [
        "", "   ", None,
        "A4:CF:12:34:56",          # 5 octets
        "A4:CF:12:34:56:78:9A",    # 7 octets
        "A4:CF:12:34:56:ZZ",       # not hex
        "hello world",
        "1234567890123",           # 13 digits
    ])
    def test_rejects_anything_that_is_not_a_mac(self, bad):
        with pytest.raises(InvalidDeviceIdentifier):
            normalize_mac(bad)

    def test_error_message_shows_the_expected_shape(self):
        with pytest.raises(InvalidDeviceIdentifier, match="A4:CF:12:34:56:78"):
            normalize_mac("nope")


@pytest.mark.unit
class TestArduinoIdFromMac:
    @pytest.mark.parametrize("mac,expected", MAC_VECTORS)
    def test_matches_the_firmware_fold(self, mac, expected):
        assert arduino_id_from_mac(mac) == expected

    def test_only_the_last_three_octets_matter(self):
        """The first three octets are the vendor OUI; the firmware discards them."""
        assert arduino_id_from_mac("00:00:00:34:56:78") == arduino_id_from_mac("A4:CF:12:34:56:78")

    def test_separator_style_does_not_change_the_id(self):
        for written in ("A4:CF:12:34:56:78", "a4cf12345678", "A4-CF-12-34-56-78"):
            assert arduino_id_from_mac(written) == 0x785634

    def test_result_always_fits_24_bits(self):
        for mac, _ in MAC_VECTORS:
            assert 1 <= arduino_id_from_mac(mac) <= MAX_ARDUINO_ID

    def test_zero_nic_bytes_become_one(self):
        """Firmware reserves id 0 as 'unset' and bumps it to 1; so must we."""
        assert arduino_id_from_mac("A4:CF:12:00:00:00") == 1


@pytest.mark.unit
class TestLooksLikeMac:
    @pytest.mark.parametrize("value,expected", [
        ("A4:CF:12:34:56:78", True),
        ("a4cf12345678", True),
        ("14", False),
        ("16777215", False),
        ("", False),
        (None, False),
        (14, False),
    ])
    def test_classification(self, value, expected):
        assert looks_like_mac(value) is expected

    def test_twelve_digit_decimal_is_read_as_a_mac(self):
        """Documented ambiguity: 12 decimal digits are valid hex too. No real
        Arduino ID reaches 12 digits (max is 8), so MAC wins."""
        assert looks_like_mac("123456789012") is True


@pytest.mark.unit
class TestParseDeviceIdentifier:
    @pytest.mark.parametrize("mac,expected", MAC_VECTORS)
    def test_mac_input_resolves_to_the_firmware_id(self, mac, expected):
        assert parse_device_identifier(mac) == expected

    @pytest.mark.parametrize("legacy", ["14", "6689108", str(MAX_ARDUINO_ID), 14])
    def test_legacy_numeric_id_passes_through(self, legacy):
        assert parse_device_identifier(legacy) == int(legacy)

    @pytest.mark.parametrize("bad", ["0", "-1", str(MAX_ARDUINO_ID + 1)])
    def test_numeric_id_out_of_range_rejected(self, bad):
        with pytest.raises(InvalidDeviceIdentifier):
            parse_device_identifier(bad)

    @pytest.mark.parametrize("bad", ["", "   ", None, "abc", "A4:CF:12:34:56"])
    def test_garbage_rejected_with_a_message_naming_the_wifi_page(self, bad):
        with pytest.raises(InvalidDeviceIdentifier):
            parse_device_identifier(bad)

    def test_empty_error_points_at_the_wifi_setup_page(self):
        with pytest.raises(InvalidDeviceIdentifier, match="WiFi setup page"):
            parse_device_identifier("")
