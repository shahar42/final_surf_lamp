#!/usr/bin/env python3
"""
Generate and send QR code for Arduino ID 9
"""
import sys
import os

# Add web_and_database to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
web_db_path = os.path.join(parent_dir, 'web_and_database')
sys.path.insert(0, web_db_path)

# Add manufacturing tools to path
sys.path.append(os.path.join(parent_dir, 'tools/manufacturing'))

from flask import Flask
from flask_mail import Message
from config import configure_app, mail
from qr_generator import QRGenerator

def send_qr_code(recipient_email, arduino_id):
    """Generate and send QR code via email"""
    
    # 1. Generate QR Code
    generator = QRGenerator()
    print(f"Generating QR code for Arduino ID {arduino_id}...")
    qr_path = generator.generate_qr_code(arduino_id)
    print(f"QR Code generated at: {qr_path}")

    # 2. Setup Flask Mail
    app = Flask(__name__)
    configure_app(app)

    # 3. Send Email
    with app.app_context():
        msg = Message(
            subject=f"Surf Lamp QR Code - Arduino ID {arduino_id}",
            sender=("Surf Lamp", app.config.get('MAIL_DEFAULT_SENDER')),
            recipients=[recipient_email]
        )

        msg.body = f"""Hi Shahar,

Here is the QR code for Arduino ID {arduino_id}.

Scan this code to register the device.

Best,
Surf Lamp System
"""

        # Attach the QR code
        with open(qr_path, 'rb') as fp:
            msg.attach(
                filename=f"arduino_{arduino_id}.png",
                content_type="image/png",
                data=fp.read()
            )

        try:
            print(f"Sending email to {recipient_email}...")
            mail.send(msg)
            print(f"✓ Email sent successfully to {recipient_email}")
            return True
        except Exception as e:
            print(f"✗ Email send failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    recipient = "shaharisn1@gmail.com"
    arduino_id = 9
    send_qr_code(recipient, arduino_id)
