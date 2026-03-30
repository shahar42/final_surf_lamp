#!/usr/bin/env python3
"""
Send QR code print sheet via email
"""
import sys
import os

# Add web_and_database to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
web_db_path = os.path.join(parent_dir, 'web_and_database')
sys.path.insert(0, web_db_path)

from flask import Flask
from flask_mail import Message
from config import configure_app, mail

def send_qr_sheet(recipient_email, attachment_path):
    """Send QR code sheet via email"""

    # Create minimal Flask app
    app = Flask(__name__)

    # Configure app with mail settings
    configure_app(app)

    with app.app_context():
        msg = Message(
            subject="Surf Lamp QR Codes - Arduino IDs 6, 7, 8",
            sender=("Surf Lamp", app.config.get('MAIL_DEFAULT_SENDER')),
            recipients=[recipient_email]
        )

        msg.body = """Hi Shahar,

Here's your printable QR code sheet for Arduino IDs 6, 7, and 8.

Each QR code links to the registration page with the Arduino ID pre-filled.

Best,
Surf Lamp System
"""

        # Attach the print sheet
        with open(attachment_path, 'rb') as fp:
            msg.attach(
                filename="surf_lamp_qr_codes_6-8.png",
                content_type="image/png",
                data=fp.read()
            )

        try:
            mail.send(msg)
            print(f"✓ Email sent successfully to {recipient_email}")
            return True
        except Exception as e:
            print(f"✗ Email send failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    qr_sheet_path = "/home/shahar42/Git_Surf_Lamp_Agent/tools/manufacturing/static/qr_codes/print_sheet_6-8.png"
    recipient = "shaharisn1@gmail.com"

    print(f"Sending QR code sheet to {recipient}...")
    send_qr_sheet(recipient, qr_sheet_path)
