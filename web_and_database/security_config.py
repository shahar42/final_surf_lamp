"""
Security Configuration for Surf Lamp Application

This file contains security-related configurations and documentation
for the Flask application's security features.
"""

import os

class SecurityConfig:
    """Security configuration settings"""
    
    # CSRF Protection
    CSRF_ENABLED = True
    CSRF_SESSION_KEY = os.environ.get('CSRF_SESSION_KEY')
    if not CSRF_SESSION_KEY:
        import secrets
        CSRF_SESSION_KEY = secrets.token_hex(32)
        print("WARNING: CSRF_SESSION_KEY not found. using generated key.")
    
    # Rate Limiting Settings
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "1000 per hour"

    # Rate limits by endpoint - SINGLE SOURCE OF TRUTH
    RATE_LIMITS = {
        # Authentication endpoints
        'auth_register': "10/minute",
        'auth_login': "10/minute",
        'auth_forgot_password': "5 per hour",
        'auth_reset_password': "3 per 15 minutes",

        # User settings endpoints
        'user_update_location': "10/minute",
        'user_update_threshold': "30/minute",
        'user_update_wind_threshold': "30/minute",
        'user_update_off_times': "30/minute",
        'user_update_led_theme': "30/minute",
        'user_update_brightness': "30/minute",
        'user_update_unit_preference': "30/minute",
        'user_toggle_quiet_hours': "30/minute",

        # Landing page
        'landing_waitlist_submit': "3 per hour",

        # Admin endpoints
        'admin_create_broadcast': "10 per hour",

        # Reporting
        'report_error': "5 per hour"
    }
    
    # Password Requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True  
    PASSWORD_REQUIRE_NUMBER = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Input Validation
    MAX_INPUT_LENGTH = 1000
    MAX_BROADCAST_MESSAGE_LENGTH = 500
    MAX_EMAIL_LENGTH = 255
    ALLOWED_TAGS = []  # No HTML tags allowed
    
    # Database Security
    DB_QUERY_TIMEOUT = 30  # seconds
    MAX_DB_CONNECTIONS = 20
    
    # Logging
    SECURITY_LOG_LEVEL = 'INFO'
    LOG_FAILED_LOGINS = True
    LOG_RATE_LIMIT_VIOLATIONS = True

# Security Headers Configuration
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:;"
    )
}

def apply_security_headers(app):
    """Apply security headers to all responses"""
    @app.after_request
    def set_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

# Input Sanitization Rules
SANITIZATION_RULES = {
    'remove_html': True,
    'remove_javascript': True,
    'remove_sql_keywords': ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', 'UNION'],
    'max_length': 1000,
    'allowed_chars_name': r'^[a-zA-Z\s\-\']+$',
    'allowed_chars_id': r'^\d+$'
}

# Validation Messages
VALIDATION_MESSAGES = {
    'required': 'This field is required.',
    'email': 'Please enter a valid email address.',
    'password_weak': 'Password must contain at least one uppercase letter, lowercase letter, number, and special character.',
    'invalid_id': 'ID must be a positive number.',
    'invalid_location': 'Please select a valid location.',
    'generic_error': 'Invalid input provided.'
}