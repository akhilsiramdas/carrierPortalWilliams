"""
TFST Carrier Portal - User Service
Manages user data by interacting with Salesforce
"""
from typing import Dict, Optional, Any
import logging
from app.services.salesforce_service import salesforce_service

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Salesforce ID"""
        # This will be implemented in salesforce_service
        return salesforce_service.get_user_by_id(user_id)

    @staticmethod
    def find_user_by_salesforce_id(salesforce_id: str) -> Optional[Dict[str, Any]]:
        """Find user by Salesforce ID (alias for get_user_by_id)"""
        return UserService.get_user_by_id(salesforce_id)

    @staticmethod
    def create_or_update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user in Salesforce"""
        # This will be implemented in salesforce_service
        return salesforce_service.create_or_update_user(user_data)

# Export singleton
user_service = UserService()