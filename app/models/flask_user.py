from flask_login import UserMixin

class User(UserMixin):
    """User class for Flask-Login"""
    
    def __init__(self, user_data):
        self._id = user_data.get('id')
        self._email = user_data.get('email')
        self._name = user_data.get('name')
        self._carrier_id = user_data.get('carrier_id')
        self._is_active = user_data.get('is_active', True)
        self._can_update_shipments = user_data.get('can_update_shipments', True)
        self._can_upload_documents = user_data.get('can_upload_documents', True)
        self._can_view_analytics = user_data.get('can_view_analytics', False)
        self._user_data = user_data
    
    @property
    def id(self):
        return self._id
        
    @property
    def email(self):
        return self._email
        
    @property
    def name(self):
        return self._name
        
    @property
    def carrier_id(self):
        return self._carrier_id
        
    @property
    def is_active(self):
        return self._is_active
        
    def get_id(self):
        return str(self._id)
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        permission_attr = f"_can_{permission}"
        return getattr(self, permission_attr, False)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self._id,
            'salesforce_user_id': self._user_data.get('salesforce_user_id'),
            'carrier_id': self._carrier_id,
            'email': self._email,
            'name': self._name,
            'is_active': self._is_active,
            'company_name': self._user_data.get('company_name'),
            'phone_number': self._user_data.get('phone_number'),
            'last_login': self._user_data.get('last_login'),
            'permissions': {
                'update_shipments': self._can_update_shipments,
                'upload_documents': self._can_upload_documents,
                'view_analytics': self._can_view_analytics
            }
        }