"""
The V3 wire format is defined in a C++ header that exists twice:

  my_lib/esp_Server_encoding.hpp                                  (server, via message_wrapper)
  arduino_code/lamp_refractored/lamp_template/esp_Server_encoding.hpp   (firmware)

They must stay identical apart from one known rename (the firmware calls the
surf packet class SurfDataPacket, the server calls it SurfData). If they
drift, every round-trip test in this directory can still pass while real
lamps decode garbage, because the server tests only ever see the server copy.
"""

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER_HEADER = os.path.join(ROOT, "my_lib", "esp_Server_encoding.hpp")
FIRMWARE_HEADER = os.path.join(ROOT, "arduino_code", "lamp_refractored", "lamp_template", "esp_Server_encoding.hpp")

KNOWN_RENAME = ("SurfDataPacket", "SurfData")


def normalise(text: str) -> str:
    text = re.sub(r"\bSurfDataPacket\b", "SurfData", text)
    # ignore trailing whitespace differences only
    return "\n".join(line.rstrip() for line in text.splitlines())


@pytest.mark.unit
class TestHeadersInSync:
    def test_both_headers_exist(self):
        assert os.path.exists(SERVER_HEADER), SERVER_HEADER
        assert os.path.exists(FIRMWARE_HEADER), FIRMWARE_HEADER

    def test_headers_identical_apart_from_known_rename(self):
        with open(SERVER_HEADER, encoding="utf-8") as f:
            server = normalise(f.read())
        with open(FIRMWARE_HEADER, encoding="utf-8") as f:
            firmware = normalise(f.read())
        assert server == firmware, (
            "my_lib/esp_Server_encoding.hpp and the firmware copy have drifted. "
            "Update both, or the lamp will decode a different layout than the server encodes."
        )

    def test_bit_layout_constants_present_in_both(self):
        """Guards against a refactor that keeps the files equal but drops the layout."""
        expected = {
            "PERIOD_OFF = 0", "HEIGHT_OFF = 6", "WAVE_THRESHOLD_OFF = 16", "SPEED_OFF = 26",
            "WIND_THRESHOLD_OFF = 36", "DIRECTION_OFF = 43", "STALE_DATA = 53",
            "DATA_AVAILABLE = 54", "QUIET_HOURS = 55", "OFF_HOURS = 56",
            "LED_THEME = 0", "BRIGHTNESS = 3", "FETCH_INTERVAL = 10", "LATITUDE = 30",
            "LONGITUDE = 0", "TZ_OFFSET = 22", "POLYNOMIAL = 0x07",
        }
        for path in (SERVER_HEADER, FIRMWARE_HEADER):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            missing = {c for c in expected if c not in text}
            assert not missing, f"{path}: missing {missing}"
