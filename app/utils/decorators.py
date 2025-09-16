"""
TFST Carrier Portal - Custom Decorators
"""
from functools import wraps
from flask import session, redirect, url_for, request, jsonify, flash
from flask_login import current_user
import logging
from app.services.salesforce_service import salesforce_service
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def require_permissions(*permissions):
    """Decorator to require specific user permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login'))
            
            for permission in permissions:
                if not current_user.has_permission(permission):
                    if request.is_json:
                        return jsonify({'error': f'Permission {permission} required'}), 403
                    return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def salesforce_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'sf_access_token' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # Check if the access token is expired
        expires_at = session.get('sf_access_token_expires_at')
        if expires_at and datetime.utcnow() >= datetime.fromisoformat(expires_at):
            if 'sf_refresh_token' not in session:
                flash('Your session has expired. Please log in again.', 'warning')
                return redirect(url_for('auth.logout'))

            try:
                # Refresh the token
                new_token_response = salesforce_service.refresh_access_token(session['sf_refresh_token'])
                session['sf_access_token'] = new_token_response['access_token']
                # Salesforce tokens typically last for 2 hours
                session['sf_access_token_expires_at'] = (datetime.utcnow() + timedelta(hours=2)).isoformat()
            except Exception as e:
                logger.error(f"Failed to refresh Salesforce token: {str(e)}")
                flash('Your session could not be refreshed. Please log in again.', 'error')
                return redirect(url_for('auth.logout'))

        return f(*args, **kwargs)
    return decorated_function

def require_carrier_access(f):
    """Decorator to ensure user has valid carrier access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        carrier_id = session.get('carrier_id')
        if not carrier_id:
            logger.warning(f"User {current_user.id} has no carrier_id in session")
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def api_response(f):
    """Decorator for consistent API responses"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            
            # If result is already a response, return it
            if hasattr(result, 'status_code'):
                return result
            
            # If result is a tuple (data, status_code)
            if isinstance(result, tuple):
                data, status_code = result
                return jsonify(data), status_code
            
            # If result is just data
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"API endpoint error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    return decorated_function

def log_user_action(action_type):
    """Decorator to log user actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated:
                logger.info(f"User {current_user.id} performed action: {action_type}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator