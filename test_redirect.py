"""
Temporary test route to redirect Salesforce OAuth to our debug endpoint
"""
from flask import Blueprint, redirect, request

test_bp = Blueprint('test', __name__)

@test_bp.route('/auth/callback')
def redirect_to_debug():
    """Temporarily redirect OAuth callback to debug version"""
    # Get all parameters from the original callback
    args = dict(request.args)
    
    # Build query string
    query_string = '&'.join([f"{k}={v}" for k, v in args.items()])
    
    # Redirect to debug callback
    return redirect(f'/auth/callback-debug?{query_string}')
