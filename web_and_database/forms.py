from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, RadioField, IntegerField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Regexp, ValidationError, EqualTo
import re
import bleach

class SanitizedStringField(StringField):
    """Custom field that sanitizes HTML content"""
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        if self.data:
            # Remove HTML tags and sanitize
            self.data = bleach.clean(self.data, tags=[], strip=True).strip()

class ForgotPasswordForm(FlaskForm):
    email = SanitizedStringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, max=128, message="Password must be between 8 and 128 characters")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('new_password', message="Passwords must match")
    ])
    submit = SubmitField('Reset Password')

class RegistrationForm(FlaskForm):
    # Name validation - letters, numbers, spaces, hyphens, apostrophes
    name = SanitizedStringField('Name', validators=[
        DataRequired(message="Name is required"),
        Length(min=2, max=50, message="Name must be between 2 and 50 characters"),
        Regexp(r"^[a-zA-Z0-9\s\-']+$", message="Name can contain letters, numbers, spaces, hyphens, and apostrophes")
    ])
    
    # Email with comprehensive validation
    email = SanitizedStringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address"),
        Length(max=255, message="Email must be less than 255 characters")
    ])
    
    # Strong password requirements
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, max=128, message="Password must be between 8 and 128 characters")
    ])

    # Arduino ID - hidden field populated from QR code URL parameter
    arduino_id = HiddenField('Arduino ID', validators=[
        DataRequired(message="Arduino ID is required"),
        NumberRange(min=1, max=999999, message="Arduino ID must be between 1 and 999999")
    ])
    
    # Location dropdown - must be from predefined list
    location = SelectField('Location', validators=[
        DataRequired(message="Please select a location")
    ])

    # Sport selection dropdown
    sport_type = SelectField('Sport Type', choices=[
        ('surfing', 'Surfing'),
        ('windsurfing', 'Windsurfing'),
        ('kitesurfing', 'Kitesurfing'),
        ('wingsurfing', 'Wing Surfing'),
        ('sup', 'Stand Up Paddle (SUP)')
    ], validators=[DataRequired(message="Please select your sport")])

    # Units selection
    units = RadioField('Units', choices=[('meters', 'Meters'), ('feet', 'Feet')],
                      validators=[DataRequired(message="Please select units")])
    
    def validate_email(self, field):
        """Custom email validation with additional security checks"""
        # Strip whitespace but preserve case (case-insensitive comparison happens at login)
        field.data = field.data.strip()
        email = field.data.lower()  # Use lowercase only for validation checks

        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.{2,}',  # Multiple dots
            r'^\.|\.$',  # Starts or ends with dot
            r'@.*@',  # Multiple @ symbols
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, email):
                raise ValidationError("Invalid email format")

        # Check domain length
        if '@' in email:
            domain = email.split('@')[1]
            if len(domain) > 253:
                raise ValidationError("Email domain is too long")

class LoginForm(FlaskForm):
    # Email validation for login
    email = SanitizedStringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address"),
        Length(max=255, message="Email must be less than 255 characters")
    ])

    # Password field for login (less strict validation than registration)
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(max=128, message="Password is too long")
    ])

    remember_me = BooleanField('Remember Me')

    def validate_email(self, field):
        """Sanitize email for login"""
        if field.data:
            field.data = field.data.strip()  # Only strip whitespace, preserve case

def validate_location_choice(location, valid_locations):
    """Validate that location is in the allowed list"""
    return location in valid_locations

def sanitize_input(input_string):
    """General purpose input sanitization"""
    if not input_string:
        return ""
    
    # Remove HTML tags
    sanitized = bleach.clean(input_string, tags=[], strip=True)
    
    # Remove null bytes and control characters (except newline and tab)
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\t')
    
    # Limit length to prevent memory issues
    return sanitized[:1000].strip()
