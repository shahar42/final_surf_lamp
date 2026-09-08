"""
CRC-8 checks for the V3 protocol.

The C++ CRC8 class (poly 0x07, init 0x00, no reflection, no xor-out) is the
plain CRC-8 also known as CRC-8/SMBUS. A pure-Python reference is kept here
and cross-checked against the extension on standard vectors and random
64-bit values, so a change to the C++ implementation is caught even though
both the encoder and the decoder would otherwise "agree" with each other.
"""

import random

import pytest

import message_wrapper

POLY = 0x07


def crc8_reference(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def extension_crc_of_u64(value: int) -> int:
    """The extension exposes CRC only through SurfData/SettingsData; SurfData
    hashes its 8 big-endian bytes, which is exactly crc8_reference(value.to_bytes(8,'big'))."""
    return message_wrapper.SurfData(value).calculate_crc()


@pytest.mark.unit
class TestReference:
    def test_known_check_value(self):
        """Standard CRC-8 check: '123456789' -> 0xF4."""
        assert crc8_reference(b"123456789") == 0xF4

    def test_empty_is_zero(self):
        assert crc8_reference(b"") == 0x00

    def test_single_byte_vectors(self):
        assert crc8_reference(b"\x00") == 0x00
        # 0x01: seven plain shifts reach 0x80, the eighth shifts it out and xors the polynomial.
        assert crc8_reference(b"\x01") == 0x07

    def test_extension_agrees_on_single_byte_inputs(self):
        """Exhaustive: every possible last byte of an otherwise-zero word."""
        for b in range(256):
            assert extension_crc_of_u64(b) == crc8_reference(bytes(7) + bytes([b]))


@pytest.mark.unit
class TestExtensionMatchesReference:
    def test_zero_value(self):
        assert extension_crc_of_u64(0) == crc8_reference(bytes(8))

    def test_all_ones(self):
        v = 0xFFFFFFFFFFFFFFFF
        assert extension_crc_of_u64(v) == crc8_reference(v.to_bytes(8, "big"))

    def test_random_u64_values(self):
        rng = random.Random(1234)
        for _ in range(500):
            v = rng.getrandbits(64)
            assert extension_crc_of_u64(v) == crc8_reference(v.to_bytes(8, "big")), hex(v)

    def test_settings_crc_covers_both_words_big_endian(self):
        d1, d2 = 0x0123456789ABCDEF, 0xFEDCBA9876543210
        expected = crc8_reference(d1.to_bytes(8, "big") + d2.to_bytes(8, "big"))
        assert message_wrapper.SettingsData(d1, d2).calculate_crc() == expected

    def test_validate_crc_agrees_with_calculate(self):
        v = 0xDEADBEEFCAFEBABE
        s = message_wrapper.SurfData(v)
        assert s.validate_crc(s.calculate_crc()) is True
        assert s.validate_crc(s.calculate_crc() ^ 0x01) is False
