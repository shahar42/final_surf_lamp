from functools import wraps
from flask import flash, redirect, url_for, session
from data_base import SessionLocal, User

def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.

    If the user is not logged in (i.e., 'user_email' not in session), it flashes
    an error message and redirects them to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login')) # Updated to use auth.login
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to ensure a user is admin before accessing a route.

    Checks both login status and is_admin flag. Non-admin users are
    redirected to dashboard with error message.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login')) # Updated to use auth.login

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == session['user_email']).first()
            if not user or not user.is_admin:
                flash('Admin access required.', 'error')
                return redirect(url_for('dashboard.dashboard')) # Updated to use dashboard.dashboard
        finally:
            db.close()

        return f(*args, **kwargs)
    return decorated_function
