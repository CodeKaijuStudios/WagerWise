"""
WagerWise Flask Application Entry Point
Main entry point for the Flask application with all configurations and initializations
"""

import os
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name='development'):
    """
    Application Factory Pattern
    Creates and configures the Flask application instance
    
    Args:
        config_name (str): Configuration environment ('development', 'production', 'testing')
    
    Returns:
        Flask: Configured Flask application instance
    """
    
    app = Flask(__name__)
    
    # Load configuration based on environment
    from app.config import config
    config_obj = config.get(config_name, config['development'])
    app.config.from_object(config_obj)
    
    logger.info(f"Creating Flask app with config: {config_name}")
    
    # ========================================================================
    # INITIALIZE EXTENSIONS
    # ========================================================================
    
    # Database (SQLAlchemy)
    from app import db
    db.init_app(app)
    logger.info("✓ Database initialized")
    
    # Database Migrations (Alembic)
    from flask_migrate import Migrate
    Migrate(app, db)
    logger.info("✓ Database migrations initialized")
    
    # JWT Authentication
    from flask_jwt_extended import JWTManager
    jwt = JWTManager(app)
    logger.info("✓ JWT authentication initialized")
    
    # CORS (Cross-Origin Resource Sharing)
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    logger.info("✓ CORS enabled")
    
    # Rate Limiter
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    )
    logger.info("✓ Rate limiter initialized")
    
    # ========================================================================
    # INITIALIZE EXTERNAL SERVICES
    # ========================================================================
    
    # Redis Client (for caching)
    import redis
    try:
        redis_client = redis.from_url(
            app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        )
        # Test connection
        redis_client.ping()
        logger.info("✓ Redis client initialized and connected")
    except Exception as e:
        logger.warning(f"⚠ Redis connection failed: {str(e)}")
        redis_client = None
    
    # Sportsbook API Client (RapidAPI)
    from app.external_apis.sportsbook import SportsBookAPIClient
    try:
        sportsbook_client = SportsBookAPIClient(
            api_key=app.config.get('RAPIDAPI_KEY'),
            api_host=app.config.get('RAPIDAPI_HOST'),
            redis_client=redis_client
        )
        logger.info("✓ Sportsbook API client initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Sportsbook API client: {str(e)}")
        sportsbook_client = None
    
    # Odds Aggregator
    from app.external_apis.aggregator import OddsAggregator
    try:
        odds_aggregator = OddsAggregator(
            sportsbook_client=sportsbook_client,
            redis_client=redis_client
        )
        logger.info("✓ Odds aggregator initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize odds aggregator: {str(e)}")
        odds_aggregator = None
    
    # Attach services to app context
    app.sportsbook_client = sportsbook_client
    app.odds_aggregator = odds_aggregator
    app.redis_client = redis_client
    
    # ========================================================================
    # REGISTER BLUEPRINTS (API Routes)
    # ========================================================================
    
    try:
        from app.auth.routes import auth_bp
        app.register_blueprint(auth_bp)
        logger.info("✓ Auth blueprint registered")
    except ImportError as e:
        logger.warning(f"⚠ Could not import auth blueprint: {str(e)}")
    
    try:
        from app.api.odds.routes import odds_bp
        app.register_blueprint(odds_bp)
        logger.info("✓ Odds API blueprint registered")
    except ImportError as e:
        logger.warning(f"⚠ Could not import odds blueprint: {str(e)}")
    
    try:
        from app.api.analysis.routes import analysis_bp
        app.register_blueprint(analysis_bp)
        logger.info("✓ Analysis API blueprint registered")
    except ImportError as e:
        logger.warning(f"⚠ Could not import analysis blueprint: {str(e)}")
    
    try:
        from app.api.history.routes import history_bp
        app.register_blueprint(history_bp)
        logger.info("✓ History API blueprint registered")
    except ImportError as e:
        logger.warning(f"⚠ Could not import history blueprint: {str(e)}")
    
    # ========================================================================
    # SHELL CONTEXT (for Flask shell)
    # ========================================================================
    
    @app.shell_context_processor
    def make_shell_context():
        """Make database available in Flask shell"""
        return {
            'db': db,
            'redis_client': redis_client,
            'sportsbook_client': sportsbook_client
        }
    
    # ========================================================================
    # ERROR HANDLERS
    # ========================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors"""
        db.session.rollback()
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403
    
    # ========================================================================
    # HEALTH CHECK ENDPOINT
    # ========================================================================
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        status = {
            'status': 'healthy',
            'environment': app.config.get('ENVIRONMENT', 'development'),
            'database': 'connected' if db else 'disconnected',
            'redis': 'connected' if redis_client else 'disconnected',
            'api_client': 'initialized' if sportsbook_client else 'not initialized'
        }
        return jsonify(status), 200
    
    # ========================================================================
    # REQUEST/RESPONSE HOOKS
    # ========================================================================
    
    @app.before_request
    def before_request():
        """Execute before each request"""
        from flask import g, request
        
        # Attach redis client to request context
        g.redis = redis_client
        
        # Log request
        logger.debug(f"{request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Execute after each request"""
        from flask import request
        
        # Log response status
        logger.debug(f"Response status: {response.status_code}")
        
        return response
    
    # ========================================================================
    # DATABASE CONTEXT
    # ========================================================================
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up database sessions"""
        pass  # SQLAlchemy handles this automatically
    
    # ========================================================================
    # INITIALIZATION LOG
    # ========================================================================
    
    logger.info("=" * 60)
    logger.info("WagerWise Application Initialized Successfully")
    logger.info(f"Environment: {app.config.get('ENVIRONMENT', 'development')}")
    logger.info(f"Debug Mode: {app.debug}")
    logger.info(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    logger.info("=" * 60)
    
    return app


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    """
    Run the Flask application
    This is only used for local development
    For production, use: gunicorn -w 4 -b 0.0.0.0:8000 app:create_app()
    """
    
    # Determine config from environment
    config_name = os.getenv('FLASK_ENV', 'development')
    
    # Create app
    app = create_app(config_name)
    
    # Run development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=(config_name == 'development')
    )
