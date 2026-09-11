"""
Device identity: turning what the user pastes into the Arduino ID the lamp
uses for every request.

The lamp derives its ID at boot from the ESP32 eFuse MAC (firmware Config.h,
getArduinoId): the three device-unique NIC bytes folded into a 24-bit integer.
The user sees that MAC on the lamp's WiFi setup page and pastes it into the
registration form; this module performs the SAME fold so the server lands on
the SAME number the lamp will poll with.

Firmware reference (Config.h):
    uint64_t mac = ESP.getEfuseMac();          // octet 0 in the low byte
    id = (mac >> 24) & 0xFFFFFF;               // octets 3,4,5 -> id
    if (id == 0) id = 1;

With the MAC printed as m0:m1:m2:m3:m4:m5 that is
    id = m3 | (m4 << 8) | (m5 << 16)
which tests/unit/firmware/test_arduino_id.cpp pins on the firmware side and
tests/unit/web/test_device_id.py pins here with the same vectors.
"""

import re

MIN_ARDUINO_ID = 1
MAX_ARDUINO_ID = 0xFFFFFF  # 16777215, 24 bits

_MAC_SEPARATORS = re.compile(r"[:\-\s.]")
_HEX12 = re.compile(r"^[0-9A-F]{12}$")


class InvalidDeviceIdentifier(ValueError):
    """The pasted value is neither a MAC address nor an Arduino ID."""


def normalize_mac(value) -> str:
    """Return the MAC as 'AA:BB:CC:DD:EE:FF', or raise InvalidDeviceIdentifier.

    Accepts the common ways a MAC gets copied: colon, dash, dot or space
    separated, or 12 bare hex digits, any case, surrounding whitespace.
    """
    if value is None:
        raise InvalidDeviceIdentifier("MAC address is required")
    raw = _MAC_SEPARATORS.sub("", str(value)).strip().upper()
    if not _HEX12.match(raw):
        raise InvalidDeviceIdentifier("MAC address must be 6 pairs of hex digits, e.g. A4:CF:12:34:56:78")
    return ":".join(raw[i:i + 2] for i in range(0, 12, 2))


def arduino_id_from_mac(value) -> int:
    """Fold a MAC into the 24-bit Arduino ID exactly like the firmware does."""
    octets = [int(part, 16) for part in normalize_mac(value).split(":")]
    device_id = octets[3] | (octets[4] << 8) | (octets[5] << 16)
    return device_id if device_id != 0 else 1  # firmware reserves 0 as "unset"


def looks_like_mac(value) -> bool:
    if value is None:
        return False
    return bool(_HEX12.match(_MAC_SEPARATORS.sub("", str(value)).strip().upper()))


def parse_device_identifier(value) -> int:
    """Accept either a pasted MAC address or a numeric Arduino ID (legacy QR
    cards) and return the Arduino ID. Raises InvalidDeviceIdentifier."""
    if value is None or str(value).strip() == "":
        raise InvalidDeviceIdentifier("Enter the MAC address shown on your lamp's WiFi setup page")
    text = str(value).strip()
    if looks_like_mac(text):
        return arduino_id_from_mac(text)
    if text.isdigit():
        device_id = int(text)
        if MIN_ARDUINO_ID <= device_id <= MAX_ARDUINO_ID:
            return device_id
        raise InvalidDeviceIdentifier(f"Arduino ID must be between {MIN_ARDUINO_ID} and {MAX_ARDUINO_ID}")
    raise InvalidDeviceIdentifier("Enter the MAC address shown on your lamp's WiFi setup page, e.g. A4:CF:12:34:56:78")
