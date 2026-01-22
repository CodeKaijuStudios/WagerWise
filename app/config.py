"""
WagerWise Application Configuration
Environment-specific configuration classes for different deployment scenarios
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Base Configuration
    Default settings applied to all environments
    """
    
    # ========================================================================
    # Flask Configuration
    # ========================================================================
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # ========================================================================
    # Database Configuration (SQLAlchemy)
    # ========================================================================
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/wagerwise'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Connection pooling for better performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # ========================================================================
    # Redis Cache Configuration
    # ========================================================================
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # ========================================================================
    # JWT Authentication Configuration
    # ========================================================================
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # ========================================================================
    # RapidAPI - Sportsbook API Configuration
    # ========================================================================
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'sportsbook-api2.p.rapidapi.com')
    SPORTSBOOK_API_TIMEOUT = 10  # seconds
    SPORTSBOOK_API_BASE_URL = 'https://sportsbook-api2.p.rapidapi.com'
    
    # ========================================================================
    # Stripe Payment Configuration
    # ========================================================================
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_API_VERSION = '2023-10-16'
    
    # ========================================================================
    # Subscription Configuration
    # ========================================================================
    SUBSCRIPTION_PRICE = 150  # $150/month
    SUBSCRIPTION_CURRENCY = 'usd'
    FREE_ANALYSIS_LIMIT = 1  # Free users get 1 analysis
    FREE_TRIAL_DAYS = 7
    
    # ========================================================================
    # Cache TTL (Time To Live) Configuration - in seconds
    # ========================================================================
    CACHE_TTL_ODDS = int(os.getenv('CACHE_TTL_ODDS', 10))  # 10 seconds
    CACHE_TTL_EVENTS = int(os.getenv('CACHE_TTL_EVENTS', 60))  # 1 minute
    CACHE_TTL_ARBITRAGE = int(os.getenv('CACHE_TTL_ARBITRAGE', 30))  # 30 seconds
    CACHE_TTL_SESSION = int(os.getenv('CACHE_TTL_SESSION', 3600))  # 1 hour
    CACHE_TTL_USER_DATA = int(os.getenv('CACHE_TTL_USER_DATA', 1800))  # 30 minutes
    
    # ========================================================================
    # API Rate Limiting Configuration
    # ========================================================================
    API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '100 per hour')
    API_CALLS_PER_MINUTE = 60
    API_CALLS_PER_HOUR = 1000
    RATE_LIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    
    # ========================================================================
    # Logging Configuration
    # ========================================================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/wagerwise.log'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # ========================================================================
    # Application Environment
    # ========================================================================
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # ========================================================================
    # CORS (Cross-Origin Resource Sharing) Configuration
    # ========================================================================
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_SUPPORTS_CREDENTIALS = True
    
    # ========================================================================
    # Security Configuration
    # ========================================================================
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = None
    
    # ========================================================================
    # Data Validation & Request Configuration
    # ========================================================================
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    # ========================================================================
    # Email Configuration (for notifications)
    # ========================================================================
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@wagerwise.com')
    
    # ========================================================================
    # Analysis Engine Configuration
    # ========================================================================
    MIN_BET_CONFIDENCE = 0.65  # Minimum confidence score for recommendations
    MIN_ARBITRAGE_PROFIT = 1.5  # Minimum arbitrage profit %
    MAX_ODDS_AGE_MINUTES = 5  # Don't use odds older than 5 minutes
    MAX_ANALYSIS_EVENTS = 10  # Maximum events in single analysis request
    
    # ========================================================================
    # Pagination Configuration
    # ========================================================================
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100
    
    # ========================================================================
    # API Response Configuration
    # ========================================================================
    JSON_AS_ASCII = False
    RESTFUL_JSON = {'separators': (',', ': ')}


class DevelopmentConfig(Config):
    """
    Development Configuration
    Used for local development with debug enabled
    """
    
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    
    # Disable HTTPS requirement in development
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    
    # More verbose logging
    LOG_LEVEL = 'DEBUG'
    
    # Allow all CORS origins in development
    CORS_ORIGINS = ['*']


class ProductionConfig(Config):
    """
    Production Configuration
    Used for live deployment with security enforced
    """
    
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    
    # Enforce HTTPS in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
    # Stricter security settings
    REMEMBER_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Production database pool settings for higher concurrency
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 40,
        'connect_args': {
            'connect_timeout': 10,
        }
    }
    
    # Restrict CORS origins to specified domains only
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://wagerwise.com').split(',')
    CORS_SUPPORTS_CREDENTIALS = True
    
    # JSON minification in production
    JSON_AS_ASCII = False
    
    # Less verbose logging
    LOG_LEVEL = 'INFO'


class TestingConfig(Config):
    """
    Testing Configuration
    Used for running automated tests
    """
    
    DEBUG = True
    TESTING = True
    
    # Use in-memory SQLite for tests (no database setup needed)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Disable rate limiting in tests for faster execution
    RATELIMIT_ENABLED = False
    
    # Use simple JWT for tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Disable mail server in tests
    MAIL_SUPPRESS_SEND = True
    
    # Use synchronous Redis in tests (or mock)
    REDIS_URL = 'redis://localhost:6379/2'


# ============================================================================
# Configuration Dictionary
# ============================================================================

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# ============================================================================
# Configuration Helper Functions
# ============================================================================

def get_config(config_name=None):
    """
    Get configuration object by name
    
    Args:
        config_name (str): Configuration name 
                          ('development', 'production', 'testing', or None for env variable)
    
    Returns:
        Config: Configuration class instance
        
    Examples:
        >>> dev_config = get_config('development')
        >>> prod_config = get_config('production')
        >>> auto_config = get_config()  # Uses FLASK_ENV
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])


def get_current_config():
    """
    Get current configuration from Flask app context
    
    Returns:
        dict: Current app.config
        
    Examples:
        >>> from flask import current_app
        >>> current_app = get_current_config()
    """
    from flask import current_app
    return current_app.config
