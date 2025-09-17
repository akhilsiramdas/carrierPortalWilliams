"""
TFST Carrier Portal - Configuration Settings
Multi-environment configuration for Dev/Staging/Prod
"""
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base configuration settings loaded from environment variables."""
    # Flask Configuration
    # IMPORTANT: This SECRET_KEY is crucial for session security.
    # It should be a long, random string.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Salesforce Configuration for OAuth Flow (User Login)
    # These are obtained from your Salesforce Connected App settings.
    SALESFORCE_CLIENT_ID = os.environ.get('SALESFORCE_CLIENT_ID')
    SALESFORCE_CLIENT_SECRET = os.environ.get('SALESFORCE_CLIENT_SECRET')
    SALESFORCE_REDIRECT_URI = os.environ.get('SALESFORCE_REDIRECT_URI')

    # Salesforce Configuration for System-level API access (Server-to-Server)
    # Credentials for a dedicated API user in Salesforce.
    SALESFORCE_USERNAME = os.environ.get('SALESFORCE_USERNAME')
    SALESFORCE_PASSWORD = os.environ.get('SALESFORCE_PASSWORD')
    SALESFORCE_SECURITY_TOKEN = os.environ.get('SALESFORCE_SECURITY_TOKEN')

    # The base URL for Salesforce login. This is overridden by environment-specific
    # configs (e.g., DevelopmentConfig points to test.salesforce.com).
    SALESFORCE_LOGIN_URL = os.environ.get('SALESFORCE_LOGIN_URL', 'https://login.salesforce.com')

    # Firebase Configuration
    # These are obtained from your Firebase project's service account credentials.
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
    # The private key is often multi-line; ensure it's correctly formatted in your .env file
    # e.g., FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
    FIREBASE_AUTH_URI = os.environ.get('FIREBASE_AUTH_URI')
    FIREBASE_TOKEN_URI = os.environ.get('FIREBASE_TOKEN_URI')
    
    # AWS S3 Configuration (for CSV processing)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_REGION = os.environ.get('AWS_S3_REGION')
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_PERMANENT = True
    
    # Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'csv'}
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Override database for local development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://tfst_user:tfst_pass@localhost/tfst_carrier_dev'
    
    # Salesforce Sandbox URL for development
    SALESFORCE_LOGIN_URL = 'https://test.salesforce.com'

class StagingConfig(Config):
    """Staging configuration"""
    DEBUG = False
    TESTING = False
    
    # Use staging Salesforce sandbox
    SALESFORCE_LOGIN_URL = 'https://test.salesforce.com'
    SESSION_COOKIE_SECURE = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production Salesforce URL
    SALESFORCE_LOGIN_URL = 'https://login.salesforce.com'
    SESSION_COOKIE_SECURE = True
    
    # Production logging
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF protection in testing
    WTF_CSRF_ENABLED = False

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name):
    """Get configuration class by name"""
    return config_map.get(config_name, config_map['default'])