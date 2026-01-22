from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from config import config
from models import db, User, BetAnalysis, AnalysisFeedback, StripeEvent
import logging
from datetime import datetime, timedelta
import os

def create_app(config_name=None):
    """Application factory"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Configure logging
    logging.basicConfig(
        level=app.config['LOG_LEVEL'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    with app.app_context():
        db.create_all()
    
    # ==================== Public Routes ====================
    
    @app.route('/')
    def index():
        """Landing page"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
            
            # Validation
            if not username or not email or not password:
                return jsonify({'error': 'Missing required fields'}), 400
            
            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            if password != confirm_password:
                return jsonify({'error': 'Passwords do not match'}), 400
            
            if User.query.filter_by(username=username).first():
                return jsonify({'error': 'Username already exists'}), 409
            
            if User.query.filter_by(email=email).first():
                return jsonify({'error': 'Email already registered'}), 409
            
            # Create user
            try:
                user = User(
                    username=username,
                    email=email,
                    is_active=True,
                    subscription_status='trial',
                    trial_ends_at=datetime.utcnow() + timedelta(days=7)
                )
                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
                login_user(user)
                logger.info(f'New user registered: {username}')
                
                return redirect(url_for('upgrade_subscription'))
            except Exception as e:
                db.session.rollback()
                logger.error(f'Registration error: {str(e)}')
                return jsonify({'error': 'Registration failed'}), 500
        
        return render_template('register.html')
    
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            username = data.get('username', '')
            password = data.get('password', '')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                logger.info(f'User logged in: {username}')
                return redirect(url_for('dashboard'))
            else:
                return jsonify({'error': 'Invalid username or password'}), 401
        
        return render_template('login.html')
    
    
    @app.route('/logout')
    @login_required
    def logout():
        """User logout"""
        logout_user()
        return redirect(url_for('index'))
    
    
    # ==================== Dashboard Routes ====================
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard"""
        if not current_user.has_analysis_access():
            return redirect(url_for('upgrade_subscription'))
        
        recent_analyses = BetAnalysis.query.filter_by(
            user_id=current_user.id
        ).order_by(BetAnalysis.created_at.desc()).limit(5).all()
        
        return render_template(
            'dashboard.html',
            recent_analyses=recent_analyses,
            remaining_requests=current_user.get_remaining_requests()
        )
    
    
    @app.route('/analyze')
    @login_required
    def analyze():
        """Analysis selection page"""
        if not current_user.has_analysis_access():
            return redirect(url_for('upgrade_subscription'))
        
        return render_template('analyze.html')
    
    
    @app.route('/api/analyze/all-bets', methods=['POST'])
    @login_required
    def analyze_all_bets():
        """Analyze all possible bets"""
        if not current_user.has_analysis_access():
            return jsonify({'error': 'Unauthorized'}), 403
        
        if current_user.can_use_preview():
            current_user.free_preview_used += 1
        
        try:
            analysis = BetAnalysis(
                user_id=current_user.id,
                analysis_type='all_bets',
                status='processing'
            )
            db.session.add(analysis)
            db.session.commit()
            
            return jsonify({
                'analysis_id': analysis.id,
                'status': 'processing'
            }), 202
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating analysis: {str(e)}')
            return jsonify({'error': 'Failed to create analysis'}), 500
    
    
    @app.route('/api/analyze/specific-bet', methods=['POST'])
    @login_required
    def analyze_specific_bet():
        """Analyze specific bet with legs"""
        if not current_user.has_analysis_access():
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        sport = data.get('sport')
        game = data.get('game')
        bet_legs = data.get('bet_legs', [])
        
        if not sport or not game or not bet_legs:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if current_user.can_use_preview():
            current_user.free_preview_used += 1
        
        try:
            analysis = BetAnalysis(
                user_id=current_user.id,
                analysis_type='specific_bet',
                sport=sport,
                game=game,
                bet_legs=bet_legs,
                status='processing'
            )
            db.session.add(analysis)
            db.session.commit()
            
            return jsonify({
                'analysis_id': analysis.id,
                'status': 'processing'
            }), 202
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating analysis: {str(e)}')
            return jsonify({'error': 'Failed to create analysis'}), 500
    
    
    @app.route('/api/analysis/<analysis_id>')
    @login_required
    def get_analysis(analysis_id):
        """Get analysis results"""
        analysis = BetAnalysis.query.filter_by(
            id=analysis_id,
            user_id=current_user.id
        ).first_or_404()
        
        return jsonify({
            'id': analysis.id,
            'status': analysis.status,
            'analysis_type': analysis.analysis_type,
            'sport': analysis.sport,
            'game': analysis.game,
            'api_response': analysis.api_response,
            'ollama_analysis': analysis.ollama_analysis,
            'recommendations': analysis.recommendations,
            'created_at': analysis.created_at.isoformat(),
            'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None
        })
    
    
    @app.route('/analysis-history')
    @login_required
    def analysis_history():
        """View all past analyses"""
        page = request.args.get('page', 1, type=int)
        analyses = BetAnalysis.query.filter_by(
            user_id=current_user.id
        ).order_by(BetAnalysis.created_at.desc()).paginate(
            page=page,
            per_page=app.config['ITEMS_PER_PAGE']
        )
        
        return render_template(
            'analysis_history.html',
            analyses=analyses
        )
    
    
    @app.route('/api/feedback/<analysis_id>', methods=['POST'])
    @login_required
    def submit_feedback(analysis_id):
        """Submit feedback on analysis accuracy"""
        analysis = BetAnalysis.query.filter_by(
            id=analysis_id,
            user_id=current_user.id
        ).first_or_404()
        
        data = request.get_json()
        is_accurate = data.get('is_accurate')
        accuracy_score = data.get('accuracy_score')
        comments = data.get('comments', '')
        actual_outcome = data.get('actual_outcome', '')
        
        try:
            feedback = AnalysisFeedback(
                user_id=current_user.id,
                analysis_id=analysis_id,
                is_accurate=is_accurate,
                accuracy_score=accuracy_score,
                comments=comments,
                actual_outcome=actual_outcome
            )
            db.session.add(feedback)
            db.session.commit()
            
            logger.info(f'Feedback submitted for analysis {analysis_id}')
            return jsonify({'success': True}), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error submitting feedback: {str(e)}')
            return jsonify({'error': 'Failed to submit feedback'}), 500
    
    
    # ==================== Subscription Routes ====================
    
    @app.route('/upgrade')
    @login_required
    def upgrade_subscription():
        """Upgrade subscription page"""
        return render_template(
            'upgrade.html',
            stripe_key=app.config['STRIPE_PUBLISHABLE_KEY'],
            subscription_price=app.config['SUBSCRIPTION_PRICE']
        )
    
    
    @app.route('/profile')
    @login_required
    def profile():
        """User profile page"""
        return render_template('profile.html', user=current_user)
    
    
    # ==================== Error Handlers ====================
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f'Server error: {str(error)}')
        return render_template('500.html'), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
