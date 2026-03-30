import sys
import os

# Add the directory containing the module to the Python path
sys.path.append(os.path.join(os.getcwd(), 'tools/manufacturing'))

from qr_generator import QRGenerator

if __name__ == "__main__":
    generator = QRGenerator()
    print("Generating print sheet for Arduino IDs 6, 7, 8...")
    path = generator.generate_print_sheet([6, 7, 8], cols=3, card_size=300)
    print(f"Print sheet generated at: {path}")
