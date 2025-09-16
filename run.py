# import os
# import logging
# from logging.handlers import RotatingFileHandler
# from app import create_app
# from app.services.firebase_service import firebase_service
# from app.services.websocket_service import init_websocket

# # Create application instance
# app = create_app()

# # Initialize WebSocket with Firebase integration
# socketio = init_websocket(app, firebase_service)

# # Configure logging
# if not app.debug:
#     if not os.path.exists('logs'):
#         os.mkdir('logs')
    
#     file_handler = RotatingFileHandler('logs/tfst_carrier_portal.log', 
#                                      maxBytes=10240000, backupCount=10)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
#     file_handler.setLevel(logging.INFO)
#     app.logger.addHandler(file_handler)
    
#     app.logger.setLevel(logging.INFO)
#     app.logger.info('TFST Carrier Portal startup')

# @app.shell_context_processor
# def make_shell_context():
#     """Make shell context for flask shell command."""
#     return {
#         'socketio': socketio
#     }

# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 5000))
#     debug = os.environ.get('FLASK_DEBUG', True)  # Set to True for development
    
#     # Use socketio.run instead of app.run for WebSocket support
#     socketio.run(app, host='0.0.0.0', port=port, debug=debug)


import os
from app import create_app

# Create application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', True)
    
    app.run(host='0.0.0.0', port=port, debug=debug)