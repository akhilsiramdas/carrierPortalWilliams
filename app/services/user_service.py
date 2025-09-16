"""
TFST Carrier Portal - User Service
In-memory user management with Salesforce Identity authentication
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# In-memory storage
_users = {}
_sessions = {}

class UserService:
    @staticmethod
    def find_user_by_salesforce_id(salesforce_id):
        """Find user by Salesforce ID"""
        for user_id, user in _users.items():
            if user.get('salesforce_user_id') == salesforce_id:
                return user
        return None
    
    @staticmethod
    def create_or_update_user(user_data):
        """Create or update user"""
        existing_user = UserService.find_user_by_salesforce_id(user_data.get('salesforce_user_id'))
        
        if existing_user:
            # Update existing user
            user_id = existing_user.get('id')
            _users[user_id].update(user_data)
            _users[user_id]['updated_at'] = datetime.utcnow().isoformat()
            return _users[user_id]
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            user_data['id'] = user_id
            user_data['created_at'] = datetime.utcnow().isoformat()
            user_data['is_active'] = True
            _users[user_id] = user_data
            return _users[user_id]
    
    @staticmethod
    def create_session(user_id, ip_address=None, user_agent=None):
        """Create a new session for user"""
        session_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=8)
        
        session = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'session_token': session_token,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat(),
            'is_active': True,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'last_activity': datetime.utcnow().isoformat()
        }
        
        _sessions[session_token] = session
        return session
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return _users.get(user_id)
    
    @staticmethod
    def get_session(session_token):
        """Get session by token"""
        return _sessions.get(session_token)
    
    @staticmethod
    def validate_session(session_token):
        """Check if session is valid and not expired"""
        session = _sessions.get(session_token)
        if not session:
            return False
        
        if not session.get('is_active'):
            return False
        
        expires_at = datetime.fromisoformat(session.get('expires_at'))
        if datetime.utcnow() > expires_at:
            session['is_active'] = False
            return False
        
        # Update last activity
        session['last_activity'] = datetime.utcnow().isoformat()
        return True
    
    @staticmethod
    def revoke_session(session_token):
        """Revoke a session"""
        if session_token in _sessions:
            _sessions[session_token]['is_active'] = False
            return True
        return False
    
    @staticmethod
    def get_user_active_sessions(user_id):
        """Get all active sessions for a user"""
        active_sessions = []
        for token, session in _sessions.items():
            if session.get('user_id') == user_id and session.get('is_active'):
                # Check if expired
                expires_at = datetime.fromisoformat(session.get('expires_at'))
                if datetime.utcnow() <= expires_at:
                    active_sessions.append(session)
                else:
                    session['is_active'] = False
        
        return active_sessions

# Export singleton
user_service = UserService()