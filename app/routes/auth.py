"""
TFST Carrier Portal - Authentication Routes
Salesforce OAuth integration with user data stored in Salesforce.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.services.salesforce_service import salesforce_service
from app.services.user_service import user_service
from app import login_manager
import secrets
import logging
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login from Salesforce user ID."""
    user_data = user_service.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

@auth_bp.route('/login')
def login():
    """Display login page and redirect to Salesforce OAuth."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    oauth_url = salesforce_service.get_oauth_url(state=state)
    return render_template('auth/login.html', oauth_url=oauth_url)

@auth_bp.route('/callback')
def oauth_callback():
    """Handle Salesforce OAuth callback."""
    # CSRF Protection: Validate state
    state_from_request = request.args.get('state')
    if not state_from_request or state_from_request != session.pop('oauth_state', None):
        flash('Invalid state parameter. Please try logging in again.', 'error')
        return redirect(url_for('auth.login'))

    # Handle OAuth error
    if request.args.get('error'):
        error_description = request.args.get('error_description', 'Unknown OAuth error')
        flash(f'OAuth error: {error_description}', 'error')
        return redirect(url_for('auth.login'))

    # Exchange authorization code for tokens
    code = request.args.get('code')
    if not code:
        flash('No authorization code received.', 'error')
        return redirect(url_for('auth.login'))

    try:
        token_response = salesforce_service.exchange_code_for_token(code)
        session['sf_access_token'] = token_response['access_token']
        session['sf_instance_url'] = token_response['instance_url']
        if 'refresh_token' in token_response:
            session['sf_refresh_token'] = token_response['refresh_token']
        session['sf_access_token_expires_at'] = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        
        # Get user information from Salesforce
        user_info = salesforce_service.get_user_info(session['sf_access_token'], session['sf_instance_url'])
        salesforce_user_id = user_info.get('user_id')

        # Check if user is associated with a carrier
        carrier_info = salesforce_service.get_carrier_info(salesforce_user_id)
        if not carrier_info or not carrier_info.get('Is_Active__c'):
            flash('Your carrier account is inactive or not found. Please contact your administrator.', 'error')
            return redirect(url_for('auth.login'))

        # Create or update user in our system (which is Salesforce itself)
        user_data_to_save = {
            'salesforce_user_id': salesforce_user_id,
            'carrier_id': carrier_info.get('Id'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'company_name': carrier_info.get('Name'),
            'phone_number': carrier_info.get('TFST_Contact_Number__c'),
            'last_login': datetime.utcnow().isoformat()
        }
        
        portal_user = user_service.create_or_update_user(user_data_to_save)
        
        if not portal_user or not portal_user.get('Is_Active__c'):
            flash('Your portal account is inactive. Please contact your administrator.', 'error')
            return redirect(url_for('auth.login'))

        # Log in the user
        login_user(User(portal_user), remember=True)
        
        flash(f'Welcome back, {portal_user.get("Name__c")}!', 'success')
        return redirect(url_for('dashboard.index'))

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        flash('An error occurred during login. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out user."""
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Display user profile."""
    return render_template('auth/profile.html', user=current_user)

# Error handlers
@auth_bp.errorhandler(401)
def unauthorized(error):
    if request.is_json:
        return jsonify({'error': 'Unauthorized'}), 401
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(403)
def forbidden(error):
    if request.is_json:
        return jsonify({'error': 'Forbidden'}), 403
    flash('You do not have permission to access this page.', 'error')
    return redirect(url_for('dashboard.index'))
