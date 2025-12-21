"""
QR Code Generator for Surf Lamp Manufacturing

Generates QR codes for Arduino ID registration with print-ready formatting.
"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QRGenerator:
    """Generates QR codes for Arduino ID registration"""

    def __init__(self, base_url="https://final-surf-lamp-web.onrender.com"):
        """
        Initialize QR generator with base URL.

        Args:
            base_url (str): Base URL for registration (without /register)
        """
        self.base_url = base_url.rstrip('/')
        self.output_dir = os.path.join(os.path.dirname(__file__), "static", "qr_codes")
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"QR Generator initialized with base URL: {self.base_url}")

    def generate_qr_code(self, arduino_id, size=300, add_label=True):
        """
        Generate a single QR code for an Arduino ID.

        Args:
            arduino_id (int): Arduino ID to encode
            size (int): Size of QR code in pixels
            add_label (bool): Whether to add text label below QR code

        Returns:
            str: Path to generated QR code image
        """
        # Create registration URL
        url = f"{self.base_url}/register?id={arduino_id}"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((size, size))

        if add_label:
            # Add label below QR code
            final_img = self._add_label(qr_img, arduino_id, size)
        else:
            final_img = qr_img

        # Save image
        filename = f"arduino_{arduino_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        final_img.save(filepath)

        logger.info(f"Generated QR code for Arduino ID {arduino_id}: {filepath}")
        return filepath

    def _add_label(self, qr_img, arduino_id, qr_size):
        """
        Add text label below QR code with Arduino ID and URL.

        Args:
            qr_img: PIL Image of QR code
            arduino_id (int): Arduino ID
            qr_size (int): Size of QR code

        Returns:
            PIL.Image: QR code with label
        """
        # Create new image with space for label (increased height for URL)
        label_height = 110
        total_height = qr_size + label_height
        final_img = Image.new('RGB', (qr_size, total_height), 'white')

        # Paste QR code
        final_img.paste(qr_img, (0, 0))

        # Draw label
        draw = ImageDraw.Draw(final_img)

        # Try to use a nice font, fallback to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Text content
        text_id = f"Arduino ID: {arduino_id}"
        text_scan = "Scan to register"
        text_url = f"{self.base_url}/register?id={arduino_id}"

        # Calculate text positions (centered)
        bbox_id = draw.textbbox((0, 0), text_id, font=font_large)
        bbox_scan = draw.textbbox((0, 0), text_scan, font=font_medium)
        bbox_url = draw.textbbox((0, 0), text_url, font=font_small)

        x_id = (qr_size - (bbox_id[2] - bbox_id[0])) // 2
        x_scan = (qr_size - (bbox_scan[2] - bbox_scan[0])) // 2
        x_url = (qr_size - (bbox_url[2] - bbox_url[0])) // 2

        # Draw text (3 lines)
        draw.text((x_id, qr_size + 5), text_id, fill='black', font=font_large)
        draw.text((x_scan, qr_size + 35), text_scan, fill='gray', font=font_medium)
        draw.text((x_url, qr_size + 60), text_url, fill='#4a5568', font=font_small)

        return final_img

    def generate_batch(self, start_id, end_id, size=300):
        """
        Generate multiple QR codes in batch.

        Args:
            start_id (int): Starting Arduino ID
            end_id (int): Ending Arduino ID (inclusive)
            size (int): Size of each QR code

        Returns:
            list: Paths to generated QR code images
        """
        paths = []
        for arduino_id in range(start_id, end_id + 1):
            path = self.generate_qr_code(arduino_id, size=size)
            paths.append(path)

        logger.info(f"Generated {len(paths)} QR codes (IDs {start_id}-{end_id})")
        return paths

    def generate_print_sheet(self, arduino_ids, cols=3, card_size=300):
        """
        Generate a print-ready sheet with multiple QR codes.

        Args:
            arduino_ids (list): List of Arduino IDs to include
            cols (int): Number of columns
            card_size (int): Size of each card in pixels

        Returns:
            str: Path to generated print sheet image
        """
        rows = (len(arduino_ids) + cols - 1) // cols  # Ceiling division
        margin = 40
        spacing = 20

        # Calculate sheet dimensions
        sheet_width = (card_size * cols) + (margin * 2) + (spacing * (cols - 1))
        sheet_height = (card_size * rows) + (margin * 2) + (spacing * (rows - 1))

        # Create sheet
        sheet = Image.new('RGB', (sheet_width, sheet_height), 'white')

        # Generate and place QR codes
        for idx, arduino_id in enumerate(arduino_ids):
            row = idx // cols
            col = idx % cols

            # Generate QR code
            temp_path = self.generate_qr_code(arduino_id, size=card_size - 20, add_label=True)
            qr_img = Image.open(temp_path)

            # Calculate position
            x = margin + (col * (card_size + spacing))
            y = margin + (row * (card_size + spacing))

            # Paste onto sheet
            sheet.paste(qr_img, (x, y))

        # Save sheet
        filename = f"print_sheet_{arduino_ids[0]}-{arduino_ids[-1]}.png"
        filepath = os.path.join(self.output_dir, filename)
        sheet.save(filepath)

        logger.info(f"Generated print sheet with {len(arduino_ids)} QR codes: {filepath}")
        return filepath


if __name__ == "__main__":
    # Quick test
    generator = QRGenerator()

    # Generate single QR code
    print(f"Generating QR code for Arduino ID 1...")
    path = generator.generate_qr_code(1)
    print(f"Saved to: {path}")

    # Generate batch
    print(f"Generating batch QR codes for IDs 1-5...")
    paths = generator.generate_batch(1, 5)
    print(f"Generated {len(paths)} QR codes")
