"""
Device identity: the lamp IS its MAC address.

A lamp's identifier is its factory MAC, stored as 12 bare lowercase hex
digits ("a4cf12345678") and shown to people with colons
("A4:CF:12:34:56:78"). The lamp sends that same string in its request URL,
the user pastes the same address during registration, and the dashboard
shows it back. Nothing is computed from it anywhere, so there is no second
implementation that can drift and no chance of two lamps colliding.

Legacy lamps registered before this change keep their small programmer
assigned numbers ("8", "14") as their identifier. Those are stored as the
decimal string and still route, so no lamp in the field needs a visit.
"""

import re

# 12 hex digits, no separators, lowercase. The stored and on-the-wire form.
_CANONICAL = re.compile(r"^[0-9a-f]{12}$")
_SEPARATORS = re.compile(r"[:\-\s.]")
_HEX12 = re.compile(r"^[0-9A-Fa-f]{12}$")
_LEGACY_NUMERIC = re.compile(r"^[0-9]{1,8}$")

# Widest identifier we store: 12 hex digits. The column is sized for this.
DEVICE_ID_MAX_LENGTH = 12


class InvalidDeviceIdentifier(ValueError):
    """The value is neither a MAC address nor a legacy numeric lamp ID."""


def _strip(value) -> str:
    return _SEPARATORS.sub("", str(value)).strip()


def is_mac_form(value) -> bool:
    """True if the value is 12 hex digits once separators are removed."""
    if value is None:
        return False
    return bool(_HEX12.match(_strip(value)))


def normalize_device_id(value) -> str:
    """Return the stored form of a device identifier, or raise.

    Accepts a MAC written any of the usual ways (colons, dashes, dots,
    spaces, bare, any case) and returns 12 lowercase hex digits. Accepts a
    legacy numeric lamp ID and returns it as a plain decimal string.
    """
    if value is None or str(value).strip() == "":
        raise InvalidDeviceIdentifier(
            "Enter the MAC address shown on your lamp's WiFi setup page"
        )

    text = str(value).strip()

    if is_mac_form(text):
        return _strip(text).lower()

    # Legacy lamps: a small decimal ID burned into pre-MAC firmware.
    if _LEGACY_NUMERIC.match(text):
        number = int(text)
        if number >= 1:
            return str(number)  # drop any leading zeros
        raise InvalidDeviceIdentifier("Lamp ID must be 1 or greater")

    raise InvalidDeviceIdentifier(
        "Enter the MAC address shown on your lamp's WiFi setup page, "
        "e.g. A4:CF:12:34:56:78"
    )


def format_device_id(device_id) -> str:
    """Return the human-readable form shown on screen.

    MACs get their colons back; legacy numeric IDs are shown as-is.
    """
    if device_id is None:
        return ""
    text = str(device_id)
    if _CANONICAL.match(text):
        upper = text.upper()
        return ":".join(upper[i:i + 2] for i in range(0, 12, 2))
    return text


def is_legacy_numeric_id(device_id) -> bool:
    """True for a pre-MAC lamp whose identifier is a programmer-assigned number."""
    return bool(_LEGACY_NUMERIC.match(str(device_id or "")))
