#!/usr/bin/env python3
"""
Send negotiation strategy email with attachment
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def send_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    attachment_path: str,
    from_email: str = None,
    password: str = None
):
    """
    Send email via Gmail SMTP with attachment

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Plain text email body
        attachment_path: Path to file to attach
        from_email: Sender Gmail address (or use EMAIL_FROM env var)
        password: Gmail App Password (or use EMAIL_PASSWORD env var)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Get credentials from args or environment
    email_from = from_email or os.getenv('EMAIL_FROM', '')
    email_password = password or os.getenv('EMAIL_PASSWORD', '')

    if not email_from or not email_password:
        print("❌ Error: Email credentials not configured")
        print("\nYou need to set EMAIL_FROM and EMAIL_PASSWORD environment variables:")
        print("  export EMAIL_FROM='your.email@gmail.com'")
        print("  export EMAIL_PASSWORD='your-app-password'")
        print("\nOr pass them as arguments to this function.")
        print("\n📝 Note: Use Gmail App Password, not regular password:")
        print("  1. Enable 2FA on your Gmail account")
        print("  2. Go to: Google Account → Security → 2-Step Verification → App passwords")
        print("  3. Generate app password for 'Mail' on 'Other device'")
        return False

    if not os.path.exists(attachment_path):
        print(f"❌ Error: Attachment file not found: {attachment_path}")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach file
        filename = os.path.basename(attachment_path)
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)

        # Connect to Gmail SMTP
        print(f"📧 Connecting to Gmail SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade to secure connection

        print(f"🔐 Authenticating...")
        server.login(email_from, email_password)

        print(f"📤 Sending email to {to_email}...")
        server.sendmail(email_from, to_email, msg.as_string())
        server.quit()

        print(f"✅ Email sent successfully!")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Attachment: {filename} ({os.path.getsize(attachment_path)} bytes)")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed!")
        print("   - Verify you're using Gmail App Password (not regular password)")
        print("   - Ensure 2FA is enabled on your Gmail account")
        print("   - Check EMAIL_FROM matches your Gmail address")
        return False

    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False


if __name__ == "__main__":
    # Configuration
    TO_EMAIL = "yehonatan1566@gmail.com"
    SUBJECT = "Surf Lamp Business Negotiation Strategy"
    BODY = """Hi,

Attached is the exported conversation containing strategic advice for negotiating your equity stake and compensation in the Surf Lamp business.

Key topics covered:
- Leverage assessment (what you control vs what they control)
- Market rate calculations for your 4 months of technical work
- Negotiation scripts and tactical responses
- Security measures (Render password, GitHub access)
- Nuclear options if negotiation fails
- IP ownership clarification

This is confidential strategic advice. Review carefully before your conversation.

Best regards,
Claude (via Shahar's request)

---
Sent: {timestamp}
""".format(timestamp=datetime.now().isoformat())

    ATTACHMENT = "2026-01-12-game_plam.txt"

    # Send email
    success = send_email_with_attachment(
        to_email=TO_EMAIL,
        subject=SUBJECT,
        body=BODY,
        attachment_path=ATTACHMENT
    )

    if not success:
        print("\n💡 Quick setup:")
        print("   export EMAIL_FROM='youremail@gmail.com'")
        print("   export EMAIL_PASSWORD='your-16-char-app-password'")
        print("   python3 send_negotiation_email.py")
        exit(1)
