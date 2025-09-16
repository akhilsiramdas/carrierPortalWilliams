"""
TFST Carrier Portal - Authentication Routes
Salesforce OAuth integration with local user management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.services.salesforce_service import salesforce_service
from app.services.user_service import user_service
from app import login_manager
import secrets
import logging
from datetime import datetime
import time

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    user_data = user_service.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

@auth_bp.route('/login')
def login():
    """Display login page and redirect to Salesforce OAuth"""
    try:
        print("DEBUG: Login route accessed")
        
        if current_user.is_authenticated:
            print("DEBUG: User already authenticated, redirecting to dashboard")
            return redirect(url_for('dashboard.index'))
        
        # Generate state parameter for CSRF protection - include timestamp
        import time
        timestamp = str(int(time.time()))
        state = secrets.token_urlsafe(32)
        state_with_timestamp = f"{state}:{timestamp}"
        
        print(f"DEBUG: Generated state with timestamp: {state_with_timestamp}")
        
        # Don't rely on session - we'll validate the timestamp in callback
        # Get Salesforce OAuth URL
        print("DEBUG: Getting Salesforce OAuth URL...")
        oauth_url = salesforce_service.get_oauth_url(state=state_with_timestamp)
        print(f"DEBUG: OAuth URL generated: {oauth_url[:100]}...")
        
        return render_template('auth/login.html', oauth_url=oauth_url)
        
    except Exception as e:
        print(f"DEBUG: Error in login route: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        flash('An error occurred. Please try again.', 'error')
        return render_template('auth/login.html', oauth_url=None)

@auth_bp.route('/callback')
def oauth_callback():
    """Handle Salesforce OAuth callback"""
    try:
        print(f"DEBUG: OAuth callback started with args: {dict(request.args)}")
        
        # Get and validate state parameter with timestamp
        state_from_request = request.args.get('state')
        if not state_from_request or ':' not in state_from_request:
            print("DEBUG: Invalid state format (no timestamp)")
            flash('Invalid request. Please try logging in again.', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            state_part, timestamp_part = state_from_request.rsplit(':', 1)
            timestamp = int(timestamp_part)
            current_time = int(time.time())
            
            # Allow 10 minutes for OAuth flow completion
            if current_time - timestamp > 600:
                print(f"DEBUG: State expired: {current_time - timestamp} seconds old")
                flash('Login session expired. Please try again.', 'warning')
                return redirect(url_for('auth.login'))
                
            print(f"DEBUG: State timestamp valid: {current_time - timestamp} seconds old")
            
        except (ValueError, IndexError) as e:
            print(f"DEBUG: Error parsing state timestamp: {e}")
            flash('Invalid request format. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Handle OAuth error
        if request.args.get('error'):
            error_description = request.args.get('error_description', 'Unknown OAuth error')
            print(f"DEBUG: OAuth error: {error_description}")
            flash(f'OAuth error: {error_description}', 'error')
            return redirect(url_for('auth.login'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            print("DEBUG: No authorization code received")
            flash('No authorization code received.', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"DEBUG: Starting token exchange...")
        # Exchange code for tokens
        token_response = salesforce_service.exchange_code_for_token(code)
        access_token = token_response['access_token']
        instance_url = token_response['instance_url']
        print(f"DEBUG: Token exchange successful")
        
        # Get user information from Salesforce
        print(f"DEBUG: Getting user info...")
        user_info = salesforce_service.get_user_info(access_token, instance_url)
        print(f"DEBUG: User info keys: {list(user_info.keys()) if user_info else 'None'}")
        logger.info(f"Retrieved user info: {user_info.get('email', 'Unknown')}")
        
        # Check if this user is associated with a carrier
        print(f"DEBUG: Getting carrier info...")
        user_id = user_info.get('user_id') or user_info.get('sub') or user_info.get('id')
        print(f"DEBUG: User ID for carrier lookup: {user_id}")
        
        carrier_info = salesforce_service.get_carrier_info(user_id)
        print(f"DEBUG: Carrier info: {bool(carrier_info)}")
        logger.info(f"Carrier lookup result: {bool(carrier_info)}")
        
        if not carrier_info:
            print(f"DEBUG: No carrier found, using mock data")
            # Use mock carrier data for now
            carrier_info = {
                'Id': 'mock_carrier_123',
                'Name': 'Mock Test Carrier',
                'Is_Active__c': True
            }
        
        if not carrier_info.get('Is_Active__c', True):  # Default to True if field doesn't exist
            print(f"DEBUG: Inactive carrier")
            logger.warning(f"Inactive carrier for user: {user_info.get('email')}")
            flash('Your carrier account is inactive. Please contact your administrator.', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"DEBUG: Creating user data...")
        # Find or create user using user service
        user_data = {
            'salesforce_user_id': user_id,
            'carrier_id': carrier_info['Id'],
            'email': user_info.get('email', 'unknown@test.com'),
            'name': user_info.get('name', 'Test User'),
            'company_name': carrier_info.get('Name'),
            'phone_number': carrier_info.get('TFST_Contact_Number__c'),
            'can_update_shipments': True,
            'can_upload_documents': True,
            'can_view_analytics': False,
            'last_login': datetime.utcnow().isoformat()
        }
        
        print(f"DEBUG: Creating/updating user...")
        user = user_service.create_or_update_user(user_data)
        print(f"DEBUG: User created/updated: {bool(user)}")
        
        if not user.get('is_active', True):
            print(f"DEBUG: User is inactive")
            flash('Your account is inactive. Please contact your administrator.', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"DEBUG: Creating session...")
        # Create user session
        user_session = user_service.create_session(
            user.get('id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        print(f"DEBUG: Session created: {bool(user_session)}")
        
        print(f"DEBUG: Logging in user...")
        # Log in user
        login_user(User(user), remember=True)
        print(f"DEBUG: User logged in via Flask-Login")
        
        # Store additional session info
        session['carrier_id'] = user.get('carrier_id')
        session['session_token'] = user_session.get('session_token')
        session.permanent = True  # Ensure session persists
        
        print(f"DEBUG: Session data set: carrier_id={session.get('carrier_id')}, session_token={session.get('session_token')}")
        print(f"DEBUG: Final session keys: {list(session.keys())}")
        
        flash(f'Welcome back, {user.get("name")}!', 'success')
        logger.info(f"User {user.get('email')} logged in successfully")
        
        print(f"DEBUG: Redirecting to dashboard...")
        # Redirect to intended page or dashboard
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.index'))
        
    except Exception as e:
        print(f"DEBUG: Exception in OAuth callback: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        logger.error(f"OAuth callback error: {str(e)}")
        flash('An error occurred during login. Please try again.', 'error')
        return redirect(url_for('auth.login'))
        
@auth_bp.route('/logout')
@login_required
def logout():
    """Log out user and revoke session"""
    try:
        # Revoke current session
        if 'session_token' in session:
            user_service.revoke_session(session['session_token'])
        
        # Clear session
        session.clear()
        
        # Log out user
        logout_user()
        
        flash('You have been logged out successfully.', 'info')
        logger.info(f"User logged out successfully")
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        flash('An error occurred during logout.', 'error')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Display user profile"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/sessions')
@login_required
def sessions():
    """Display user's active sessions"""
    active_sessions = user_service.get_user_active_sessions(current_user.id)
    return render_template('auth/sessions.html', sessions=active_sessions)

@auth_bp.route('/revoke-session/<session_token>', methods=['POST'])
@login_required
def revoke_session(session_token):
    """Revoke a specific session"""
    try:
        if user_service.revoke_session(session_token):
            flash('Session revoked successfully.', 'success')
        else:
            flash('Session not found.', 'error')
            
    except Exception as e:
        logger.error(f"Error revoking session {session_token}: {str(e)}")
        flash('An error occurred while revoking the session.', 'error')
    
    return redirect(url_for('auth.sessions'))

@auth_bp.route('/api/verify-session', methods=['GET'])
@login_required
def verify_session():
    """API endpoint to verify session validity"""
    from flask import jsonify
    try:
        if 'session_token' not in session:
            return jsonify({'valid': False, 'error': 'No session token'}), 401
        
        if not user_service.validate_session(session['session_token']):
            return jsonify({'valid': False, 'error': 'Session expired'}), 401
        
        user_session = user_service.get_session(session['session_token'])
        
        return jsonify({
            'valid': True,
            'user': current_user.to_dict() if hasattr(current_user, 'to_dict') else {'id': current_user.id},
            'session': {
                'expires_at': user_session.get('expires_at'),
                'last_activity': user_session.get('last_activity')
            }
        })
        
    except Exception as e:
        logger.error(f"Session verification error: {str(e)}")
        return jsonify({'valid': False, 'error': 'Internal error'}), 500

# Error handlers
@auth_bp.errorhandler(401)
def unauthorized(error):
    from flask import jsonify
    if request.is_json:
        return jsonify({'error': 'Unauthorized'}), 401
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(403)
def forbidden(error):
    from flask import jsonify
    if request.is_json:
        return jsonify({'error': 'Forbidden'}), 403
    flash('You do not have permission to access this page.', 'error')
    return redirect(url_for('dashboard.index'))
