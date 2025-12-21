
import sys
import os

# Add the directory containing the module to the Python path
sys.path.append(os.path.join(os.getcwd(), 'tools/manufacturing'))

from qr_generator import QRGenerator

if __name__ == "__main__":
    generator = QRGenerator()
    print("Generating QR code for Arduino ID 5...")
    path = generator.generate_qr_code(5)
    print(f"QR Code generated at: {path}")
