from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and subscription management"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Subscription fields
    is_active = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    subscription_status = db.Column(
        db.String(50), 
        default='trial',
        nullable=False
    )
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Free trial tracking
    free_preview_used = db.Column(db.Integer, default=0)
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    
    # User preferences
    preferred_sports = db.Column(db.JSON, default=list)
    notification_preferences = db.Column(db.JSON, default=dict)
    
    # Relationships
    analyses = db.relationship('BetAnalysis', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    feedback_records = db.relationship('AnalysisFeedback', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_active_subscription(self):
        """Check if user has active subscription"""
        if self.subscription_status == 'active' and self.subscription_end_date:
            return self.subscription_end_date > datetime.utcnow()
        return False
    
    def can_use_preview(self):
        """Check if user can use free preview"""
        return self.free_preview_used < 1 and self.subscription_status == 'trial'
    
    def has_analysis_access(self):
        """Check if user has access to analysis tools"""
        return self.is_active and (self.has_active_subscription() or self.can_use_preview())
    
    def get_remaining_requests(self):
        """Get remaining analysis requests for user"""
        if self.has_active_subscription():
            return float('inf')
        elif self.can_use_preview():
            return 1 - self.free_preview_used
        return 0
    
    def __repr__(self):
        return f'<User {self.username}>'


class BetAnalysis(db.Model):
    """Model for storing bet analysis requests and results"""
    __tablename__ = 'bet_analysis'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Analysis type
    analysis_type = db.Column(
        db.String(50),
        nullable=False,
    )
    
    # For specific bet analysis
    sport = db.Column(db.String(100), nullable=True)
    game = db.Column(db.String(255), nullable=True)
    
    # Bet legs (stored as JSON for flexibility)
    bet_legs = db.Column(db.JSON, default=list)
    
    # API and Analysis Results
    api_response = db.Column(db.JSON, nullable=True)
    ollama_analysis = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.JSON, nullable=True)
    
    # Metadata
    status = db.Column(
        db.String(50),
        default='pending',
        nullable=False
    )
    error_message = db.Column(db.Text, nullable=True)
    processing_time = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    feedback = db.relationship('AnalysisFeedback', backref='analysis', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BetAnalysis {self.id} - {self.analysis_type}>'


class AnalysisFeedback(db.Model):
    """Model for user feedback on analysis accuracy"""
    __tablename__ = 'analysis_feedback'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    analysis_id = db.Column(db.String(36), db.ForeignKey('bet_analysis.id'), nullable=False, index=True)
    
    # Feedback
    is_accurate = db.Column(db.Boolean, nullable=False)
    accuracy_score = db.Column(db.Integer, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    actual_outcome = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AnalysisFeedback {self.id}>'


class StripeEvent(db.Model):
    """Model for tracking Stripe webhook events"""
    __tablename__ = 'stripe_events'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True, index=True)
    
    event_data = db.Column(db.JSON, nullable=False)
    processed = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StripeEvent {self.stripe_event_id}>'
