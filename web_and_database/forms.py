from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, RadioField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Regexp, ValidationError
import re
import bleach
from wtforms import SubmitField
from wtforms.validators import EqualTo

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

class SanitizedStringField(StringField):
    """Custom field that sanitizes HTML content"""
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        if self.data:
            # Remove HTML tags and sanitize
            self.data = bleach.clean(self.data, tags=[], strip=True).strip()

class RegistrationForm(FlaskForm):
    # Name validation - only letters, spaces, hyphens, apostrophes
    name = SanitizedStringField('Name', validators=[
        DataRequired(message="Name is required"),
        Length(min=2, max=50, message="Name must be between 2 and 50 characters"),
        Regexp(r"^[a-zA-Z\s\-']+$", message="Name can only contain letters, spaces, hyphens, and apostrophes")
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
    
    # Lamp ID - positive integer only
    lamp_id = IntegerField('Lamp ID', validators=[
        DataRequired(message="Lamp ID is required"),
        NumberRange(min=1, max=999999, message="Lamp ID must be between 1 and 999999")
    ])
    
    # Arduino ID - positive integer only
    arduino_id = IntegerField('Arduino ID', validators=[
        DataRequired(message="Arduino ID is required"),
        NumberRange(min=1, max=999999, message="Arduino ID must be between 1 and 999999")
    ])
    
    # Location dropdown - must be from predefined list
    location = SelectField('Location', validators=[
        DataRequired(message="Please select a location")
    ])
    
    # Theme selection
    theme = RadioField('Theme', choices=[('light', 'Light'), ('dark', 'Dark')], 
                      validators=[DataRequired(message="Please select a theme")])
    
    # Units selection
    units = RadioField('Units', choices=[('meters', 'Meters'), ('feet', 'Feet')],
                      validators=[DataRequired(message="Please select units")])
    
    def validate_email(self, field):
        """Custom email validation with additional security checks"""
        email = field.data.lower()
        
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
    
    def validate_email(self, field):
        """Sanitize email for login"""
        if field.data:
            field.data = field.data.lower().strip()

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
