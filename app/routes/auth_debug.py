"""
DEBUG VERSION - Simple Auth Callback for Testing
Remove this file after debugging
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user
from app.models.user import User
from app.services.salesforce_service import salesforce_service
from app import login_manager
import secrets
import logging

auth_debug_bp = Blueprint('auth_debug', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)

# Simple in-memory user storage for testing
test_users = {}

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    if user_id in test_users:
        return User(test_users[user_id])
    return None

@auth_debug_bp.route('/callback-debug')
def oauth_callback_debug():
    """Debug version of OAuth callback"""
    try:
        logger.info("=== DEBUG CALLBACK START ===")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request args: {dict(request.args)}")
        logger.info(f"Session keys: {list(session.keys())}")
        logger.info(f"Session oauth_state: {session.get('oauth_state')}")
        
        # Get authorization code
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        logger.info(f"Code: {code[:20] if code else None}...")
        logger.info(f"State: {state}")
        logger.info(f"Error: {error}")
        
        if error:
            flash(f'OAuth error: {error}', 'error')
            return redirect(url_for('auth.login'))
        
        if not code:
            flash('No authorization code received.', 'error')
            return redirect(url_for('auth.login'))
        
        # Simple state check
        if 'oauth_state' in session and state != session['oauth_state']:
            logger.error(f"State mismatch: {state} != {session['oauth_state']}")
            flash('State mismatch - please try again', 'warning')
            # Don't fail completely, just warn
        
        # Clear state
        session.pop('oauth_state', None)
        
        try:
            # Exchange code for tokens
            logger.info("Exchanging code for token...")
            token_response = salesforce_service.exchange_code_for_token(code)
            logger.info("Token exchange successful")
            
            access_token = token_response['access_token']
            instance_url = token_response['instance_url']
            
            # Get user information from Salesforce
            logger.info("Getting user info...")
            user_info = salesforce_service.get_user_info(access_token, instance_url)
            logger.info(f"User info: email={user_info.get('email')}, name={user_info.get('name')}")
            
            # Try to get carrier info (but don't fail if it doesn't work)
            logger.info("Getting carrier info...")
            try:
                carrier_info = salesforce_service.get_carrier_info(user_info.get('user_id'))
                logger.info(f"Carrier info: {bool(carrier_info)}")
                if carrier_info:
                    logger.info(f"Carrier: {carrier_info.get('Name')}")
            except Exception as e:
                logger.error(f"Carrier lookup failed: {e}")
                # Create fake carrier for testing
                carrier_info = {
                    'Id': 'test_carrier_123',
                    'Name': 'Test Carrier',
                    'Is_Active__c': True
                }
            
            # Create test user
            user_data = {
                'id': user_info.get('user_id', 'test_user_123'),
                'salesforce_user_id': user_info.get('user_id'),
                'carrier_id': carrier_info.get('Id') if carrier_info else 'test_carrier',
                'email': user_info.get('email', 'test@carrier.com'),
                'name': user_info.get('name', 'Test User'),
                'company_name': carrier_info.get('Name', 'Test Carrier') if carrier_info else 'Test Carrier',
                'is_active': True
            }
            
            # Store user in memory
            test_users[user_data['id']] = user_data
            
            # Log in user
            user_obj = User(user_data)
            login_user(user_obj, remember=True)
            
            # Store session info
            session['carrier_id'] = user_data['carrier_id']
            session['user_email'] = user_data['email']
            
            logger.info(f"User logged in: {user_data['email']}")
            flash(f'Welcome, {user_data["name"]}! (Debug mode)', 'success')
            
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            logger.error(f"Auth process error: {str(e)}")
            flash(f'Authentication failed: {str(e)}', 'error')
            return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"DEBUG callback error: {str(e)}")
        flash('Debug callback failed', 'error')
        return redirect(url_for('auth.login'))

@auth_debug_bp.route('/test-login')
def test_login():
    """Create a test login without Salesforce"""
    try:
        # Create test user
        user_data = {
            'id': 'test_user_debug',
            'salesforce_user_id': 'test_sf_user',
            'carrier_id': 'test_carrier_debug',
            'email': 'debug@testcarrier.com',
            'name': 'Debug Test User',
            'company_name': 'Debug Test Carrier',
            'is_active': True
        }
        
        # Store user in memory
        test_users[user_data['id']] = user_data
        
        # Log in user
        user_obj = User(user_data)
        login_user(user_obj, remember=True)
        
        # Store session info
        session['carrier_id'] = user_data['carrier_id']
        session['user_email'] = user_data['email']
        
        flash('Debug login successful!', 'success')
        return redirect(url_for('dashboard.index'))
        
    except Exception as e:
        logger.error(f"Test login error: {str(e)}")
        flash(f'Test login failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))
