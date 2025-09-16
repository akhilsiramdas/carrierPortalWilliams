from flask import Flask, render_template
from flask_login import LoginManager
import logging
from config.config import Config
import os

# Setup login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """Create Flask application with factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize login manager
    login_manager.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.shipments import shipments_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(shipments_bp, url_prefix='/shipments')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register debug routes in development
    if app.config.get('DEBUG', False):
        from app.routes.auth_debug import auth_debug_bp
        app.register_blueprint(auth_debug_bp)
        
        # Temporary redirect for OAuth callback
        from test_redirect import test_bp
        app.register_blueprint(test_bp)
    
    # Root route
    @app.route('/')
    def index():
        return "Hello World! TFST Carrier Portal is running."
    
    # Test route to verify session functionality
    @app.route('/test-session')
    def test_session():
        from flask import session
        if 'test_value' not in session:
            session['test_value'] = 'Session is working!'
            session.permanent = True
            return f"Session created. Visit again to test persistence."
        else:
            return f"Session persisted! Value: {session['test_value']}"
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    return app