'''
handles all user authinication
register, login, and password reset

author: shahar nitzan
'''

import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from sqlalchemy import func
from flask_limiter.util import get_remote_address

from config import bcrypt, limiter, SURF_LOCATIONS
from security_config import SecurityConfig
from forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from data_base import SessionLocal, User, PasswordResetToken, add_user_and_lamp
from utils.mail import send_reset_email

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__)


def _validate_arduino_id_from_qr(arduino_id_param):
    """Extract and validate Arduino ID from QR code parameter.

    Returns:
        tuple: (arduino_id_int, error_message) or (None, error_message) if invalid
    """
    if not arduino_id_param:
        return None, 'QR code required to register. Please scan the QR code on the card in your Surf Lamp box.'

    try:
        arduino_id_int = int(arduino_id_param)
        if 1 <= arduino_id_int <= 999999:
            return arduino_id_int, None
        return None, 'Invalid QR code. Please scan the QR code from your Surf Lamp box.'
    except (ValueError, TypeError):
        logger.warning(f"Invalid Arduino ID in URL parameter: {arduino_id_param}")
        return None, 'Invalid QR code. Please scan the QR code from your Surf Lamp box.'


def _set_user_session(user, remember_me=False):
    """Set session variables after successful login.

    Args:
        user: User object with email, user_id, username
        remember_me: If True, enables persistent session (30 days)
    """
    session.permanent = remember_me
    session['user_email'] = user.email
    session['user_id'] = user.user_id
    session['username'] = user.username

    if remember_me:
        logger.info(f"🔒 Remember me enabled for user: {user.username} (30 days)")
    else:
        logger.info(f"⏱️ Session-only login for user: {user.username}")


@bp.route("/register", methods=['GET', 'POST'])
@limiter.limit(lambda: SecurityConfig.RATE_LIMITS['auth_register'])
def register():
    """
    Handles user registration.
    QR code with Arduino ID in URL parameter is REQUIRED.
    """
    if 'user_email' in session:
        return redirect(url_for('dashboard.dashboard'))

    form = RegistrationForm()
    form.location.choices = [(loc, loc) for loc in SURF_LOCATIONS]

    # Arduino ID from QR code URL parameter is REQUIRED
    if request.method == 'GET':
        arduino_id_param = request.args.get('id', '')
        arduino_id_int, error_msg = _validate_arduino_id_from_qr(arduino_id_param)

        if error_msg:
            flash(error_msg, 'error')
            return render_template('register.html', form=form, locations=SURF_LOCATIONS, qr_required=True)

        form.arduino_id.data = arduino_id_int
        logger.info(f"Pre-filled Arduino ID from QR code: {arduino_id_int}")

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        arduino_id = form.arduino_id.data
        location = form.location.data
        sport_type = form.sport_type.data
        theme = 'day'
        units = form.units.data

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        success, message, user_data = add_user_and_lamp(
            name=name,
            email=email,
            password_hash=hashed_password,
            arduino_id=int(arduino_id),
            location=location,
            theme=theme,
            units=units,
            sport_type=sport_type
        )

        if success and user_data:
            # Auto-login: set session variables
            session['user_email'] = user_data['email']
            session['user_id'] = user_data['user_id']
            session['username'] = user_data['username']
            logger.info(f"✅ Auto-login after registration: {user_data['username']} ({user_data['email']})")
            flash(message, 'success_short')
            flash('For WiFi setup, open Quick Actions', 'info')
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash(message, 'error')
            return render_template('register.html', form=form, locations=SURF_LOCATIONS)
    else:
        if request.method == 'POST':
            # Check if Arduino ID is missing (shouldn't happen with QR code flow)
            if not form.arduino_id.data:
                flash('QR code required to register. Please scan the QR code on the card in your Surf Lamp box.', 'error')
                return render_template('register.html', form=form, locations=SURF_LOCATIONS, qr_required=True)

            for field_name, errors in form.errors.items():
                for error in errors:
                    flash(f"{field_name.replace('_', ' ').title()}: {error}", 'error')

    return render_template('register.html', form=form, locations=SURF_LOCATIONS)

@bp.route("/login", methods=['GET', 'POST'])
@limiter.limit(lambda: SecurityConfig.RATE_LIMITS['auth_login'])
def login():
    """
    Handles user login.
    """
    if 'user_email' in session:
        return redirect(url_for('dashboard.dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        logger.info(f"🔐 Login attempt for email: {email}")

        db = SessionLocal()
        try:
            user = db.query(User).filter(func.lower(User.email) == email.lower()).first()

            if not user:
                logger.warning(f"❌ Login failed - email not found: {email}")
                flash('Invalid email or password. Please try again.', 'error')
                return redirect(url_for('auth.login'))

            if bcrypt.check_password_hash(user.password_hash, password):
                logger.info(f"✅ Login successful for user: {user.username} ({user.email})")
                _set_user_session(user, form.remember_me.data)
                return redirect(url_for('dashboard.dashboard'))
            else:
                logger.warning(f"❌ Login failed - invalid password for email: {email}")
                flash('Invalid email or password. Please try again.', 'error')
                return redirect(url_for('auth.login'))
        finally:
            db.close()

    return render_template('login.html', form=form)

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@bp.route("/forgot-password", methods=['GET', 'POST'])
@limiter.limit(lambda: SecurityConfig.RATE_LIMITS['auth_forgot_password'])
def forgot_password():
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower()
        
        flash('If an account exists with that email, a reset link has been sent.', 'success')
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user:
                token = secrets.token_urlsafe(48)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expiration = datetime.now(timezone.utc) + timedelta(minutes=20)
                
                db.query(PasswordResetToken).filter(
                    PasswordResetToken.user_id == user.user_id,
                    PasswordResetToken.used_at.is_(None)
                ).update({"is_invalidated": True})
                
                reset_token = PasswordResetToken(
                    user_id=user.user_id,
                    token_hash=token_hash,
                    expiration_time=expiration
                )
                db.add(reset_token)
                db.commit()
                
                send_reset_email(user.email, user.username, token)
        finally:
            db.close()
            
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', form=form)

@bp.route("/reset-password/<token>", methods=['GET', 'POST'])
@limiter.limit(lambda: SecurityConfig.RATE_LIMITS['auth_reset_password'])
def reset_password_form(token):
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        db = SessionLocal()
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            reset_token = db.query(PasswordResetToken).filter(
                PasswordResetToken.token_hash == token_hash
            ).first()
            
            if not reset_token or not reset_token.is_valid():
                flash('Invalid or expired reset link.', 'error')
                return redirect(url_for('auth.forgot_password'))
            
            user = db.query(User).get(reset_token.user_id)
            user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            
            reset_token.used_at = datetime.now(timezone.utc)
            db.commit()
            
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception:
            db.rollback()
            flash('An error occurred. Please try again.', 'error')
        finally:
            db.close()
    
    return render_template('reset_password.html', form=form, token=token)
