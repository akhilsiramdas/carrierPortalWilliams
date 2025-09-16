# """
# TFST Carrier Portal - User Models
# Local user management with Salesforce Identity authentication
# """
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import UserMixin
# from datetime import datetime, timezone
# from app import db

# class TFST_CarrierUser(UserMixin, db.Model):
#     """
#     Local carrier user management table
#     Authenticates via Salesforce but manages user data locally
#     """
#     __tablename__ = 'tfst_carrier_users'
    
#     id = db.Column(db.Integer, primary_key=True)
#     salesforce_user_id = db.Column(db.String(255), unique=True, nullable=False)
#     carrier_id = db.Column(db.String(255), nullable=False)  # References TFST_Master_Carrier in Salesforce
#     email = db.Column(db.String(255), unique=True, nullable=False)
#     name = db.Column(db.String(255), nullable=False)
#     is_active = db.Column(db.Boolean, default=True, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
#     last_login = db.Column(db.DateTime)
    
#     # User permissions/roles (carrier-specific)
#     can_update_shipments = db.Column(db.Boolean, default=True)
#     can_upload_documents = db.Column(db.Boolean, default=True)
#     can_view_analytics = db.Column(db.Boolean, default=False)
    
#     # Additional carrier information
#     phone_number = db.Column(db.String(20))
#     company_name = db.Column(db.String(255))
    
#     # Relationship with sessions
#     sessions = db.relationship('TFST_UserSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
#     def __repr__(self):
#         return f'<TFST_CarrierUser {self.name} - {self.email}>'
    
#     def get_id(self):
#         """Required by Flask-Login"""
#         return str(self.id)
    
#     def update_last_login(self):
#         """Update the last login timestamp"""
#         self.last_login = datetime.utcnow()
#         db.session.commit()
    
#     def has_permission(self, permission):
#         """Check if user has specific permission"""
#         return getattr(self, f'can_{permission}', False)
    
#     def to_dict(self):
#         """Convert user object to dictionary"""
#         return {
#             'id': self.id,
#             'salesforce_user_id': self.salesforce_user_id,
#             'carrier_id': self.carrier_id,
#             'email': self.email,
#             'name': self.name,
#             'is_active': self.is_active,
#             'company_name': self.company_name,
#             'phone_number': self.phone_number,
#             'last_login': self.last_login.isoformat() if self.last_login else None,
#             'permissions': {
#                 'update_shipments': self.can_update_shipments,
#                 'upload_documents': self.can_upload_documents,
#                 'view_analytics': self.can_view_analytics
#             }
#         }

# class TFST_UserSession(db.Model):
#     """
#     User session management for enhanced security
#     """
#     __tablename__ = 'tfst_user_sessions'
    
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('tfst_carrier_users.id'), nullable=False)
#     session_token = db.Column(db.String(255), unique=True, nullable=False)
#     expires_at = db.Column(db.DateTime, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
#     is_active = db.Column(db.Boolean, default=True, nullable=False)
    
#     # Session metadata
#     ip_address = db.Column(db.String(45))  # IPv6 compatible
#     user_agent = db.Column(db.String(500))
#     last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
#     def __repr__(self):
#         return f'<TFST_UserSession {self.session_token[:10]}... for User {self.user_id}>'
    
#     def is_expired(self):
#         """Check if session is expired"""
#         return datetime.utcnow() > self.expires_at
    
#     def extend_session(self, hours=8):
#         """Extend session expiration"""
#         from datetime import timedelta
#         self.expires_at = datetime.utcnow() + timedelta(hours=hours)
#         self.last_activity = datetime.utcnow()
#         db.session.commit()
    
#     def revoke(self):
#         """Revoke the session"""
#         self.is_active = False
#         db.session.commit()
    
#     def to_dict(self):
#         """Convert session to dictionary"""
#         return {
#             'id': self.id,
#             'user_id': self.user_id,
#             'created_at': self.created_at.isoformat(),
#             'expires_at': self.expires_at.isoformat(),
#             'last_activity': self.last_activity.isoformat() if self.last_activity else None,
#             'is_active': self.is_active,
#             'ip_address': self.ip_address,
#             'is_expired': self.is_expired()
#         }

# class TFST_S3UploadLog(db.Model):
#     """
#     Track S3 CSV upload processing for carriers
#     """
#     __tablename__ = 'tfst_s3_upload_logs'
    
#     id = db.Column(db.Integer, primary_key=True)
#     carrier_id = db.Column(db.String(255), nullable=False)
#     filename = db.Column(db.String(255), nullable=False)
#     s3_key = db.Column(db.String(500), nullable=False)  # S3 object key
#     processed_at = db.Column(db.DateTime)
#     status = db.Column(db.String(50), default='pending', nullable=False)  # 'pending', 'processing', 'completed', 'error'
#     error_details = db.Column(db.Text)
#     records_processed = db.Column(db.Integer, default=0)
#     records_failed = db.Column(db.Integer, default=0)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
#     def __repr__(self):
#         return f'<TFST_S3UploadLog {self.filename} - {self.status}>'
    
#     def mark_processing(self):
#         """Mark upload as currently being processed"""
#         self.status = 'processing'
#         self.processed_at = datetime.utcnow()
#         db.session.commit()
    
#     def mark_completed(self, processed_count, failed_count=0):
#         """Mark upload as completed"""
#         self.status = 'completed'
#         self.records_processed = processed_count
#         self.records_failed = failed_count
#         self.processed_at = datetime.utcnow()
#         db.session.commit()
    
#     def mark_error(self, error_message):
#         """Mark upload as failed with error details"""
#         self.status = 'error'
#         self.error_details = error_message
#         self.processed_at = datetime.utcnow()
#         db.session.commit()
    
#     def to_dict(self):
#         """Convert upload log to dictionary"""
#         return {
#             'id': self.id,
#             'carrier_id': self.carrier_id,
#             'filename': self.filename,
#             'status': self.status,
#             'records_processed': self.records_processed,
#             'records_failed': self.records_failed,
#             'created_at': self.created_at.isoformat(),
#             'processed_at': self.processed_at.isoformat() if self.processed_at else None,
#             'error_details': self.error_details
#         }

from flask_login import UserMixin

class User(UserMixin):
    """
    A user class for Flask-Login that wraps user data from Salesforce.
    The `id` property is mapped to the Salesforce User ID.
    """
    
    def __init__(self, user_data: dict):
        if not user_data:
            raise ValueError("user_data cannot be empty")

        # The primary ID for the user in the portal is the Salesforce User ID
        self._id = user_data.get('Salesforce_User_Id__c') or user_data.get('Id')
        self._email = user_data.get('Email__c')
        self._name = user_data.get('Name__c') or user_data.get('Name')
        self._carrier_id = user_data.get('Carrier_Id__c')
        self._is_active = user_data.get('Is_Active__c', True)

        # Permissions
        self._can_update_shipments = user_data.get('Can_Update_Shipments__c', True)
        self._can_upload_documents = user_data.get('Can_Upload_Documents__c', True)
        self._can_view_analytics = user_data.get('Can_View_Analytics__c', False)

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
        """Required by Flask-Login."""
        return str(self._id)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        permission_attr = f"_can_{permission}"
        return getattr(self, permission_attr, False)
    
    def to_dict(self) -> dict:
        """Convert user object to a dictionary for API responses."""
        return {
            'id': self._id,
            'salesforce_user_id': self._id,
            'carrier_id': self._carrier_id,
            'email': self._email,
            'name': self._name,
            'is_active': self._is_active,
            'company_name': self._user_data.get('Company_Name__c'),
            'phone_number': self._user_data.get('Phone_Number__c'),
            'last_login': self._user_data.get('Last_Login__c'),
            'permissions': {
                'update_shipments': self._can_update_shipments,
                'upload_documents': self._can_upload_documents,
                'view_analytics': self._can_view_analytics
            }
        }