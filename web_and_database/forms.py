'''
handles constraints on all user input (registration new password login)

author: shahar nitzan
'''

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, RadioField, IntegerField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Regexp, ValidationError, EqualTo, Optional
from wtforms.widgets import HiddenInput
import re
import bleach
from security_config import SecurityConfig

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
        Length(min=SecurityConfig.PASSWORD_MIN_LENGTH, max=SecurityConfig.PASSWORD_MAX_LENGTH, message=f"Password must be between {SecurityConfig.PASSWORD_MIN_LENGTH} and {SecurityConfig.PASSWORD_MAX_LENGTH} characters")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('new_password', message="Passwords must match")
    ])
    submit = SubmitField('Reset Password')

class RegistrationForm(FlaskForm):
    # Set by validate_mac_address: the Arduino ID the lamp will poll with,
    # whether it came from a pasted MAC or a legacy QR card's ?id=.
    resolved_arduino_id = None

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
        Length(max=SecurityConfig.MAX_EMAIL_LENGTH, message=f"Email must be less than {SecurityConfig.MAX_EMAIL_LENGTH} characters")
    ])
    
    # Strong password requirements
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=SecurityConfig.PASSWORD_MIN_LENGTH, max=SecurityConfig.PASSWORD_MAX_LENGTH, message=f"Password must be between {SecurityConfig.PASSWORD_MIN_LENGTH} and {SecurityConfig.PASSWORD_MAX_LENGTH} characters")
    ])

    # Device identity. Exactly one of these is used:
    # - mac_address: what the user pastes from the lamp's WiFi setup page
    #   (the normal flow). The Arduino ID is derived from it server-side with
    #   utils.device_id.arduino_id_from_mac, mirroring the firmware.
    # - arduino_id: hidden, pre-filled from a legacy QR card's ?id= parameter.
    # NOTE: no Optional() here. Optional() raises StopValidation on an empty
    # field, which would skip validate_mac_address below and leave the form
    # with no device identity at all. Emptiness is handled in that validator.
    mac_address = SanitizedStringField('Lamp MAC address', validators=[
        Length(max=32, message="MAC address is too long")
    ])
    arduino_id = IntegerField('Arduino ID', widget=HiddenInput(), validators=[
        Optional(),
        NumberRange(min=1, max=16777215, message="Arduino ID must be between 1 and 16777215")
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
    
    def validate_mac_address(self, field):
        """A MAC is required unless a legacy QR card pre-filled arduino_id.
        On success, resolved_arduino_id holds the ID the lamp will poll with."""
        from utils.device_id import InvalidDeviceIdentifier, arduino_id_from_mac
        self.resolved_arduino_id = None
        if field.data:
            try:
                self.resolved_arduino_id = arduino_id_from_mac(field.data)
            except InvalidDeviceIdentifier as e:
                raise ValidationError(str(e))
        elif self.arduino_id.data:
            self.resolved_arduino_id = int(self.arduino_id.data)
        else:
            raise ValidationError("Enter the MAC address shown on your lamp's WiFi setup page")

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
        Length(max=SecurityConfig.MAX_EMAIL_LENGTH, message=f"Email must be less than {SecurityConfig.MAX_EMAIL_LENGTH} characters")
    ])

    # Password field for login (less strict validation than registration)
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(max=SecurityConfig.PASSWORD_MAX_LENGTH, message="Password is too long")
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
    return sanitized[:SecurityConfig.MAX_INPUT_LENGTH].strip()
