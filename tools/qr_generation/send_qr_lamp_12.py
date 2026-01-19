#!/usr/bin/env python3
"""
Generate QR code for Lamp ID 12
"""
import os
import sys

# Add manufacturing tools to path
tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(tools_dir, 'manufacturing'))

from qr_generator import QRGenerator

def main():
    arduino_id = 12

    print(f"Generating QR code for Arduino ID {arduino_id}...")

    # Generate QR code
    generator = QRGenerator()
    qr_path = generator.generate_qr_code(arduino_id, size=400, add_label=True)

    print(f"✅ QR code generated: {qr_path}")
    print(f"\nConfiguration for Arduino ID {arduino_id}:")
    print(f"- Right strip (wave height): 1→8 (8 LEDs)")
    print(f"- Middle strip (wind speed): 20→12 (9 LEDs, reversed)")
    print(f"- Left strip (wave period): 23→30 (8 LEDs)")
    print(f"\nRegistration URL: https://final-surf-lamp-web.onrender.com/register?id={arduino_id}")

    return qr_path

if __name__ == "__main__":
    main()
