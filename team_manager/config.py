import os

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database (SQLite)
    DATABASE_URL = os.environ.get('DATABASE_URL', 'staff_command.db')
    
    # File Uploads
    UPLOAD_FOLDER_CONTRACTS = os.environ.get('UPLOAD_FOLDER_CONTRACTS', 'static/uploads/contracts')
    UPLOAD_FOLDER_PROFILES = os.environ.get('UPLOAD_FOLDER_PROFILES', 'static/uploads/profiles')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 10 * 1024 * 1024)) # Default 10MB
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
    
    # Feature Flags
    ENABLE_SEARCH = os.environ.get('ENABLE_SEARCH', 'true').lower() == 'true'

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

# Dictionary to map environment names to config classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
