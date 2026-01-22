"""
WagerWise Application Package
Initializes SQLAlchemy and other extensions for the Flask application
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ============================================================================
# Initialize Extensions
# ============================================================================

# SQLAlchemy ORM (Database)
db = SQLAlchemy()

# Flask-Migrate (Database Migrations)
migrate = Migrate()

# Flask-JWT-Extended (JWT Authentication)
jwt = JWTManager()

# Flask-CORS (Cross-Origin Resource Sharing)
cors = CORS()

# Flask-Limiter (Rate Limiting)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    'db',
    'migrate',
    'jwt',
    'cors',
    'limiter'
]
