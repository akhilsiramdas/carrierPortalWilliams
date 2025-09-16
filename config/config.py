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
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Salesforce Configuration
    SALESFORCE_USERNAME = os.environ.get('SALESFORCE_USERNAME', 'vhine@tmsforce.com')
    SALESFORCE_PASSWORD = os.environ.get('SALESFORCE_PASSWORD', 'Florid@4321')
    SALESFORCE_SECURITY_TOKEN = os.environ.get('SALESFORCE_SECURITY_TOKEN', '')
    SALESFORCE_CLIENT_ID = os.environ.get('SALESFORCE_CLIENT_ID', '3MVG9i1HRpGLXp.oSHzgfjG318M9msPigpnY1xVNaJMo1Tgf9xpK_4ko3n.qdsamLauza.a.womYELGZvCm1q')
    SALESFORCE_CLIENT_SECRET = os.environ.get('SALESFORCE_CLIENT_SECRET', '565BB8198C9D43E17046E5A37017B26CC13C60E958F8225933A120799903A3C0')
    SALESFORCE_LOGIN_URL = os.environ.get('SALESFORCE_LOGIN_URL', 'https://login.salesforce.com')
    SALESFORCE_REDIRECT_URI = os.environ.get('SALESFORCE_REDIRECT_URI', 'http://localhost:5000/auth/callback')
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'ftl-mobileapp')
    FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID', '4b6927357df18555c42290d66d1ac0e459c7f79e')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY', '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQChpdFmcCu+9Bzl\n699u4U5uKHGc9veAY9zltSC3rfGOzc5hQCC+xpKELXutuv9YT0SNxu9uPjjxRmKV\n6VjhasvPY8VuxZEfvveSvIFDS8G+11WSj7suj7iM6ipDyg7xYuJTbtoOnxoc1udq\nzEPvZTSf+IKBtkGGsE7GhrJ8mgOaQi3h+NHMm40ffqm3Hdo8hu/wN0CGZvNM54B1\njEcZL7Muu5zmbjuC0T8MP3aSCws/9HbKrn5bv2k/DOFvPTJIYlDdxIks3ojtZtX4\nhod82cMDie77EqEv1DIZYS/Oacsi2e9wLFUzSNlfLCEx/Do6HFEz5r6nYFuhAGVe\n54TrchkZAgMBAAECggEADSaOpOp76fAK0yW1AAdHuIHaea5EhRHFbHv81RSgnJaK\nXge34kKzXsTN1VzA3fACSr/Oxhrnylvd31ukMHUzbtmAvA9J9tmJY0r/VSM6TYql\nL+Q459knZsdneCuzEC4+7WdiSWLmM/HD0pYa8hnmBcb+ObaYbsW0fZrYYHdYfa8Y\nJCNULUEYbpnjTuDbzGDY6gEwQV6qnQc/D/vRtl6eSX98wGBoLBMnk0pzmqfu2AdY\nE9ndK7lYE4V9FkSFr3WYgCO7uwRxVlY6OaU7sW+xG9+xou3y49pAEVvTLBUk0CeY\n0AjlU5KXFYcJkuU1PB6UAiQZ9xmQFR8fzmzEAdrLxQKBgQDWXPABFv5xdEbM1VIN\nnhYACXG/XP25P0zdkg01vCxHJtb5lWKlS7bH7Gt1Mc5cf+vYBB8oSll5KXqQA/jY\nFFHFXG/QpKAC893qi+CItQGRUK7ReiJg97jW5iV5Mz7eD7FaN1tWSQZlHdPfZEZE\nFdWpX6uiaZHv1dtEDodMOzwJOwKBgQDBC6Vcb+YbH4sPqT4O+vN50ts6Ep+pHEmR\nDEx9mJmhIT1n3VJNcwrceob2W/xmBnZxAgmMof6imDF5fcFq7fMAax7rEmxQCE/2\nfW6BcgHYUMlnvKg0eyUjnhZ551H/0YCYkZP/1j3H+MWxwwOQQQ/dRGeZX/e4ofhi\nNDITA8hhuwKBgCeTAtAAsbq6T7PTEhHnhII/PBurDEBd2k/xfbTU54u/NOLg3FRN\n1RG1qOT66/ERwLWhlSr4BuqiaLkbsp4Zqjr4ZMAtFElXQjnh1vMGD6MHNS8BEEW8\nlgg+dt6YQlv2o7RXEeqtEpwqVIoiVgKN0WMygVo7iTCw14kJ8Zp2ORAvAoGATazj\n8pfL3OoKSFju8ZQkV8ZyE6HewGrzZvut43N9jYoUbTBup1885Y4ftA07N8ot6jbJ\npN6h2MaoUZw6MU5hUq/HlwqormNJ2YKK7mbzOxj2kVklzUgnn3dCz/Y11lt0BO++\nv1hzL313/pjbXDXxrjSSAvLMeGwjx0/9Pg1tmXUCgYEAjodNluUJNajcJ1Guc0Pw\ntQ2qPIb90H1Di6iWkshHgwB4WRxQBX/DlPlryr+E3wcLzQul41NJOAFp7ieuwhBm\n6jY3sovXDnWi7X7IsUCphFvEchVNtsCMN3UT02SnnNO6Swqhzzuden9j9O0X3ELP\nsJFp7h2H24TLt2Bjie/zkKU=\n-----END PRIVATE KEY-----\n')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL', 'firebase-adminsdk-ndct7@ftl-mobileapp.iam.gserviceaccount.com')
    FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID', '105458234057160065431')
    FIREBASE_AUTH_URI = os.environ.get('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth')
    FIREBASE_TOKEN_URI = os.environ.get('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token')
    
    # AWS S3 Configuration (for CSV processing)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-east-1')
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
    
    # Session Configuration - Simplified for OAuth
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Must be False for localhost HTTP
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_PATH = '/'
    SESSION_PERMANENT = True
    
    # Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'csv'}
    
    # Redis Configuration (for caching if needed)
    REDIS_URL = os.environ.get('REDIS_URL')
    
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
    
    # Enhanced security for production
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    
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