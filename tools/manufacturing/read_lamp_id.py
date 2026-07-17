"""
Read Lamp ID from Serial + Generate QR Code

New manufacturing flow for MAC-derived Arduino IDs:
the ID is no longer chosen by the programmer - it is burned into the ESP32's
eFuse MAC and printed on the serial log at boot. This script listens on the
serial port, captures the "Arduino ID: <N> (decimal)" boot line, and
generates the registration QR code for that ID.

Usage:
    python read_lamp_id.py                      # auto-detect port, read ID, generate QR
    python read_lamp_id.py --port /dev/ttyUSB0  # explicit port
    python read_lamp_id.py --no-qr              # just print the ID

Requires: pyserial (pip install pyserial)
"""

import argparse
import re
import sys

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial is required: pip install pyserial")
    sys.exit(1)

from qr_generator import QRGenerator

BAUD_RATE = 115200
READ_TIMEOUT_SEC = 60  # lamp prints its ID within seconds of reset
ID_PATTERN = re.compile(r"Arduino ID:\s*(\d+)\s*\(decimal\)")


def find_serial_port():
    """Auto-detect the ESP32 serial port (USB serial adapters only)."""
    candidates = [
        p.device for p in serial.tools.list_ports.comports()
        if "USB" in p.device or "ACM" in p.device or "usbserial" in p.device.lower()
    ]
    if not candidates:
        return None
    if len(candidates) > 1:
        print(f"Multiple serial ports found: {candidates}")
        print(f"Using {candidates[0]} (pass --port to override)")
    return candidates[0]


def read_arduino_id(port, timeout_sec=READ_TIMEOUT_SEC):
    """
    Read the MAC-derived Arduino ID from the lamp's serial boot log.

    Opening the port toggles DTR/RTS, which resets the ESP32, so the boot
    log (including the ID line) replays automatically.

    Returns:
        int: the Arduino ID, or None if not seen within timeout.
    """
    print(f"Listening on {port} @ {BAUD_RATE} (waiting for lamp boot log)...")
    with serial.Serial(port, BAUD_RATE, timeout=timeout_sec) as ser:
        deadline_lines = 2000  # safety cap on lines scanned
        for _ in range(deadline_lines):
            raw = ser.readline()
            if not raw:  # timeout hit with no data
                return None
            line = raw.decode("utf-8", errors="replace").strip()
            match = ID_PATTERN.search(line)
            if match:
                return int(match.group(1))
    return None


def main():
    parser = argparse.ArgumentParser(description="Read lamp ID from serial and generate registration QR")
    parser.add_argument("--port", help="Serial port (default: auto-detect)")
    parser.add_argument("--no-qr", action="store_true", help="Only print the ID, skip QR generation")
    args = parser.parse_args()

    port = args.port or find_serial_port()
    if not port:
        print("No serial port found. Is the lamp connected via USB?")
        sys.exit(1)

    arduino_id = read_arduino_id(port)
    if arduino_id is None:
        print("Did not see the Arduino ID line on serial. Press the lamp's reset button and retry.")
        sys.exit(1)

    print(f"Arduino ID: {arduino_id}")

    if not args.no_qr:
        generator = QRGenerator()
        path = generator.generate_qr_code(arduino_id)
        print(f"QR code saved to: {path}")


if __name__ == "__main__":
    main()
