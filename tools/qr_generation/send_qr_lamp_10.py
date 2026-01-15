#!/usr/bin/env python3
"""
Generate and send QR code for Lamp ID 10 via email
"""
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# Add manufacturing tools to path
tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(tools_dir, 'manufacturing'))

from qr_generator import QRGenerator

def send_qr_email(arduino_id, qr_image_path):
    """Send QR code via email using SMTP"""

    # Email configuration (from insights_config.env)
    email_from = "shaharisn1@gmail.com"
    email_password = "jnsm rjbt wnal pijf"
    email_to = "shaharisn1@gmail.com"

    # Create email message
    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = email_to
    msg['Subject'] = f"🏷️ QR Code for Surf Lamp ID {arduino_id}"

    # Email body
    body = f"""Hi Shahar,

Here's the QR code for Surf Lamp Arduino ID {arduino_id}.

Registration URL: https://final-surf-lamp-web.onrender.com/register?id={arduino_id}

The QR code is attached and ready to print.

Configuration:
- Right strip: 1→13 (13 LEDs)
- Middle strip: 35→20 (16 LEDs, reversed)
- Left strip: 39→52 (14 LEDs)

Best,
Surf Lamp System
"""

    msg.attach(MIMEText(body, 'plain'))

    # Attach QR code image
    with open(qr_image_path, 'rb') as fp:
        img = MIMEImage(fp.read())
        img.add_header('Content-Disposition', 'attachment', filename=f'arduino_{arduino_id}_qr.png')
        msg.attach(img)

    # Send email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_from, email_password)
        server.sendmail(email_from, email_to, msg.as_string())
        server.quit()
        print(f"✅ Email sent successfully to {email_to}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

def main():
    arduino_id = 10

    print(f"Generating QR code for Arduino ID {arduino_id}...")

    # Generate QR code
    generator = QRGenerator()
    qr_path = generator.generate_qr_code(arduino_id, size=400, add_label=True)

    print(f"QR code generated: {qr_path}")
    print(f"Sending email...")

    # Send email
    success = send_qr_email(arduino_id, qr_path)

    if success:
        print("✅ Done! Check your email.")
    else:
        print("❌ Email sending failed.")
        print(f"QR code saved locally at: {qr_path}")

if __name__ == "__main__":
    main()
