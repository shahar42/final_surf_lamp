#!/usr/bin/env python3
"""
Send the Surf Lamp Architecture Report to Raz
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
    attachment_path: str
):
    email_from = os.getenv('ALERT_EMAIL_USER', '')
    email_password = os.getenv('ALERT_EMAIL_PASSWORD', '')

    if not email_from or not email_password:
        print("❌ Error: Email credentials (ALERT_EMAIL_USER/PASSWORD) not configured")
        return False

    if not os.path.exists(attachment_path):
        print(f"❌ Error: Attachment file not found: {attachment_path}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        filename = os.path.basename(attachment_path)
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)

        print(f"📧 Connecting to Gmail SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_from, email_password)
        server.sendmail(email_from, to_email, msg.as_string())
        server.quit()

        print(f"✅ Email sent successfully to {to_email}!")
        return True

    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False

if __name__ == "__main__":
    TO_EMAIL = "nitzanraz@gmail.com"
    SUBJECT = "Surf Lamp System - Architecture & Code Review"
    BODY = """Hi Raz,

Attached is the comprehensive architecture and code review report for the Surf Lamp system.
It covers the end-to-end data flow, API endpoints, binary protocol, and database schema.

Best regards,
Gemini (on behalf of Shahar)
"""
    ATTACHMENT = "report_for_raz.md"

    send_email_with_attachment(TO_EMAIL, SUBJECT, BODY, ATTACHMENT)
