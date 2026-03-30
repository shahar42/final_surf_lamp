from flask_mail import Message
from flask import url_for, current_app
import logging

logger = logging.getLogger(__name__)

def send_reset_email(user_email, username, token):
    # Import mail here to avoid circular imports during initialization
    # Assuming 'mail' is available in the app config or extensions
    from config import mail
    
    # Using 'auth.reset_password_form' as the endpoint will be in auth blueprint
    reset_link = url_for('auth.reset_password_form', token=token, _external=True)
    subject = "Password Reset Request"

    logger.info(f"Attempting to send password reset email to {user_email}")
    logger.info(f"MAIL_SERVER: {current_app.config.get('MAIL_SERVER')}")
    logger.info(f"MAIL_PORT: {current_app.config.get('MAIL_PORT')}")
    logger.info(f"MAIL_USERNAME: {current_app.config.get('MAIL_USERNAME')}")
    logger.info(f"MAIL_DEFAULT_SENDER: {current_app.config.get('MAIL_DEFAULT_SENDER')}")

    msg = Message(subject, sender=("Surf Lamp", current_app.config.get('MAIL_DEFAULT_SENDER')), recipients=[user_email])
    msg.body = f"""Hello {username},

Click this link to reset your password:
{reset_link}

This link expires in 20 minutes.
If you didn't request this, ignore this email.

---
Surf Lamp Team
"""

    try:
        mail.send(msg)
        logger.info(f"✓ Email sent successfully to {user_email}")
        return True
    except Exception as e:
        logger.error(f"✗ Email send failed to {user_email}: {e}")
        logger.exception("Full traceback:")
        return False


def send_waitlist_confirmation(email, first_name, position):
    from config import mail

    msg = Message(
        subject="You're on the Surf Lamp waitlist!",
        sender=("Surf Lamp", current_app.config.get('MAIL_DEFAULT_SENDER')),
        recipients=[email]
    )
    msg.body = f"""Hi {first_name},

You're #{position} on the Surf Lamp waitlist!

We'll notify you as soon as early access opens. Stay tuned.

– The Surf Lamp Team
"""
    msg.html = f"""
<p>Hi {first_name},</p>
<p>You're <strong>#{position}</strong> on the Surf Lamp waitlist!</p>
<p>We'll notify you as soon as early access opens. Stay tuned.</p>
<br>
<p>– The Surf Lamp Team</p>
"""
    try:
        mail.send(msg)
        logger.info(f"✓ Waitlist confirmation sent to {email}")
    except Exception as e:
        logger.error(f"✗ Waitlist confirmation email failed to {email}: {e}")
