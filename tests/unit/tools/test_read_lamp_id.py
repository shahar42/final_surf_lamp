"""
Unit tests for tools/manufacturing/read_lamp_id.py

This is the only step in the new manufacturing flow that ties a physical
lamp to its QR card. If the serial parser misreads the ID, the customer
registers a lamp that does not exist and the real one can never be claimed.
"""

from types import SimpleNamespace

import pytest

import read_lamp_id

BOOT_LOG = [
    b"\xff\xfe garbage from reset\r\n",
    b"rst:0x1 (POWERON_RESET),boot:0x13\r\n",
    b"\xf0\x9f\x94\xa2 Displaying Arduino ID in binary...\r\n",   # UTF-8 emoji prefix
    b"   Arduino ID: 6689108 (decimal)\r\n",
    b"   Binary: 0110011...\r\n",
]


class FakeSerial:
    """Minimal pyserial stand-in: iterates canned lines, then times out (b'')."""

    opened = []

    def __init__(self, port, baud, timeout=None):
        FakeSerial.opened.append((port, baud, timeout))
        self._lines = list(FakeSerial.lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def readline(self):
        return self._lines.pop(0) if self._lines else b""


@pytest.fixture
def fake_serial(monkeypatch):
    FakeSerial.opened.clear()
    FakeSerial.lines = BOOT_LOG
    monkeypatch.setattr(read_lamp_id.serial, "Serial", FakeSerial)
    return FakeSerial


@pytest.mark.unit
class TestIdPattern:
    @pytest.mark.parametrize("line,expected", [
        ("   Arduino ID: 6689108 (decimal)", 6689108),
        ("Arduino ID: 14 (decimal)", 14),
        ("Arduino ID:16777215 (decimal)", 16777215),
        ("xx Arduino ID: 7   (decimal) yy", 7),
    ])
    def test_id_regex_matches_boot_line(self, line, expected):
        m = read_lamp_id.ID_PATTERN.search(line)
        assert m and int(m.group(1)) == expected

    @pytest.mark.parametrize("line", [
        "Device ID: 6689108",                 # jitter info line, different label
        "Arduino ID: 0x66 (hex)",
        "Applying startup jitter: 8000 ms (ID=6689108)",
        "Arduino ID: (decimal)",
    ])
    def test_id_regex_ignores_other_lines(self, line):
        assert read_lamp_id.ID_PATTERN.search(line) is None


@pytest.mark.unit
class TestReadArduinoId:
    def test_reads_id_from_boot_log(self, fake_serial):
        assert read_lamp_id.read_arduino_id("/dev/ttyUSB0") == 6689108

    def test_opens_port_at_115200(self, fake_serial):
        read_lamp_id.read_arduino_id("/dev/ttyUSB0", timeout_sec=7)
        assert fake_serial.opened == [("/dev/ttyUSB0", 115200, 7)]

    def test_tolerates_undecodable_bytes_before_the_id(self, fake_serial):
        fake_serial.lines = [b"\x80\x81\x82\r\n", b"Arduino ID: 42 (decimal)\r\n"]
        assert read_lamp_id.read_arduino_id("/dev/ttyUSB0") == 42

    def test_returns_none_on_timeout_without_id(self, fake_serial):
        fake_serial.lines = [b"booting...\r\n", b"WiFi connected\r\n"]
        assert read_lamp_id.read_arduino_id("/dev/ttyUSB0") is None

    def test_returns_none_when_port_silent(self, fake_serial):
        fake_serial.lines = []
        assert read_lamp_id.read_arduino_id("/dev/ttyUSB0") is None


@pytest.mark.unit
class TestPortAutodetect:
    def test_port_autodetect_filters_usb_acm(self, monkeypatch):
        ports = [SimpleNamespace(device="/dev/ttyS0"), SimpleNamespace(device="/dev/ttyUSB0"), SimpleNamespace(device="/dev/ttyACM1")]
        monkeypatch.setattr(read_lamp_id.serial.tools.list_ports, "comports", lambda: ports)
        assert read_lamp_id.find_serial_port() == "/dev/ttyUSB0"

    def test_port_autodetect_macos_usbserial(self, monkeypatch):
        ports = [SimpleNamespace(device="/dev/cu.Bluetooth-Incoming-Port"), SimpleNamespace(device="/dev/cu.usbserial-0001")]
        monkeypatch.setattr(read_lamp_id.serial.tools.list_ports, "comports", lambda: ports)
        assert read_lamp_id.find_serial_port() == "/dev/cu.usbserial-0001"

    def test_port_autodetect_none_when_nothing_plugged(self, monkeypatch):
        monkeypatch.setattr(read_lamp_id.serial.tools.list_ports, "comports", lambda: [SimpleNamespace(device="/dev/ttyS0")])
        assert read_lamp_id.find_serial_port() is None
