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
    CSRF_SESSION_KEY = os.environ.get('CSRF_SESSION_KEY', 'super-secret-csrf-key')
    
    # Rate Limiting Settings
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "1000 per hour"
    
    # Rate limits by endpoint
    RATE_LIMITS = {
        'login': "5 per minute, 20 per hour",
        'register': "3 per minute, 10 per hour", 
        'general': "100 per minute"
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
    'Content-Security-Policy': "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
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