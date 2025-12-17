import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from sqlalchemy import func
from flask_limiter.util import get_remote_address

from config import bcrypt, limiter, SURF_LOCATIONS
from forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from data_base import SessionLocal, User, PasswordResetToken, add_user_and_lamp
from utils.mail import send_reset_email

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__)

@bp.route("/register", methods=['GET', 'POST'])
@limiter.limit("10/minute") 
def register():
    """
    Handles user registration.
    """
    if 'user_email' in session:
        return redirect(url_for('dashboard.dashboard'))

    form = RegistrationForm()
    form.location.choices = [(loc, loc) for loc in SURF_LOCATIONS]

    # Pre-fill Arduino ID from QR code URL parameter
    if request.method == 'GET':
        arduino_id_param = request.args.get('id', '')
        if arduino_id_param:
            try:
                arduino_id_int = int(arduino_id_param)
                if 1 <= arduino_id_int <= 999999:
                    form.arduino_id.data = arduino_id_int
                    logger.info(f"Pre-filled Arduino ID from QR code: {arduino_id_int}")
            except (ValueError, TypeError):
                logger.warning(f"Invalid Arduino ID in URL parameter: {arduino_id_param}")

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

        success, message = add_user_and_lamp(
            name=name,
            email=email,
            password_hash=hashed_password,
            arduino_id=int(arduino_id),
            location=location,
            theme=theme,
            units=units,
            sport_type=sport_type
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
            return render_template('register.html', form=form, locations=SURF_LOCATIONS)
    else:
        if request.method == 'POST':
            for field_name, errors in form.errors.items():
                for error in errors:
                    flash(f"{field_name.replace('_', ' ').title()}: {error}", 'error')

    return render_template('register.html', form=form, locations=SURF_LOCATIONS)

@bp.route("/login", methods=['GET', 'POST'])
@limiter.limit("10/minute")
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
                session['user_email'] = user.email
                session['user_id'] = user.user_id
                session['username'] = user.username

                if form.remember_me.data:
                    session.permanent = True
                    logger.info(f"🔒 Remember me enabled for user: {user.username}")

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
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@bp.route("/forgot-password", methods=['GET', 'POST'])
@limiter.limit("5 per hour")
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
@limiter.limit("3 per 15 minutes")
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

@bp.route("/test-reset-db")
def test_reset_db():
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.email == 'shaharisn1@gmail.com').first()
        if not user:
            db.close()
            return "❌ User not found"
        
        username = user.username
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expiration = datetime.now(timezone.utc) + timedelta(minutes=20)
        
        reset_token = PasswordResetToken(
            user_id=user.user_id,
            token_hash=token_hash,
            expiration_time=expiration
        )
        db.add(reset_token)
        db.commit()
        db.close()
        
        return f"✅ Database test passed! Token created for user {username}"
        
    except Exception as e:
        return f"❌ Database test failed: {e}"
