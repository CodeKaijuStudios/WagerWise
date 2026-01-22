from functools import wraps
from flask import current_app, request, jsonify
from flask_login import current_user
from models import db, User, StripeEvent
import stripe
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def subscription_required(f):
    """Decorator to check if user has active subscription or preview access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.has_analysis_access():
            return jsonify({'error': 'Subscription or preview access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def paid_subscription_required(f):
    """Decorator to check if user has paid subscription only (not preview)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.has_active_subscription():
            return jsonify({'error': 'Paid subscription required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


class StripeManager:
    """Handles all Stripe payment operations"""
    
    def __init__(self):
        self.stripe_key = current_app.config['STRIPE_SECRET_KEY']
        stripe.api_key = self.stripe_key
    
    def create_customer(self, user):
        """Create a Stripe customer for a user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={'user_id': user.id}
            )
            
            user.stripe_customer_id = customer.id
            db.session.commit()
            
            logger.info(f'Stripe customer created for user {user.username}')
            return customer
        except stripe.error.StripeError as e:
            logger.error(f'Stripe customer creation error: {str(e)}')
            raise
    
    def create_subscription(self, user, price_id):
        """Create a subscription for a user"""
        try:
            if not user.stripe_customer_id:
                self.create_customer(user)
            
            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent']
            )
            
            user.stripe_subscription_id = subscription.id
            user.subscription_status = 'active'
            user.subscription_start_date = datetime.utcnow()
            user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
            
            db.session.commit()
            
            logger.info(f'Subscription created for user {user.username}')
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f'Subscription creation error: {str(e)}')
            raise
    
    def cancel_subscription(self, user):
        """Cancel a user's subscription"""
        try:
            if user.stripe_subscription_id:
                stripe.Subscription.delete(user.stripe_subscription_id)
                
                user.subscription_status = 'cancelled'
                user.subscription_end_date = datetime.utcnow()
                db.session.commit()
                
                logger.info(f'Subscription cancelled for user {user.username}')
                return True
        except stripe.error.StripeError as e:
            logger.error(f'Subscription cancellation error: {str(e)}')
            raise
    
    def handle_webhook(self, event):
        """Handle incoming Stripe webhook events"""
        try:
            event_type = event['type']
            event_id = event['id']
            event_data = event['data']['object']
            
            # Check if event already processed
            existing_event = StripeEvent.query.filter_by(
                stripe_event_id=event_id
            ).first()
            
            if existing_event:
                logger.info(f'Event {event_id} already processed')
                return
            
            user = None
            
            if event_type == 'customer.subscription.updated':
                user_id = event_data['metadata'].get('user_id')
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        user.subscription_status = 'active'
                        user.subscription_end_date = datetime.utcfromtimestamp(
                            event_data['current_period_end']
                        )
                        db.session.commit()
            
            elif event_type == 'customer.subscription.deleted':
                user_id = event_data['metadata'].get('user_id')
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        user.subscription_status = 'cancelled'
                        db.session.commit()
            
            elif event_type == 'invoice.payment_succeeded':
                user_id = event_data['metadata'].get('user_id')
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        user.subscription_status = 'active'
                        db.session.commit()
            
            # Record the event
            stripe_event = StripeEvent(
                stripe_event_id=event_id,
                event_type=event_type,
                user_id=user.id if user else None,
                event_data=event_data,
                processed=True
            )
            db.session.add(stripe_event)
            db.session.commit()
            
            logger.info(f'Webhook event {event_id} processed successfully')
            return True
        
        except Exception as e:
            logger.error(f'Webhook processing error: {str(e)}')
            raise


def verify_webhook_signature(request_data, signature):
    """Verify Stripe webhook signature"""
    try:
        webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']
        event = stripe.Webhook.construct_event(
            request_data,
            signature,
            webhook_secret
        )
        return event
    except ValueError as e:
        logger.error(f'Webhook signature verification failed: {str(e)}')
        return None
    except stripe.error.SignatureVerificationError as e:
        logger.error(f'Invalid webhook signature: {str(e)}')
        return None


def record_analysis_usage(user, analysis_type):
    """Record analysis usage for rate limiting (future feature)"""
    # This can be expanded for rate limiting per user tier
    logger.info(f'User {user.username} used {analysis_type} analysis')
