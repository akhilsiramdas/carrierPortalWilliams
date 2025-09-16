"""
TFST Carrier Portal - Salesforce Integration Service
Real-time API connection using system admin credentials
"""
import requests
import json
from simple_salesforce import Salesforce
from flask import current_app, session
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

def escape_soql(value: str) -> str:
    """Sanitizes a string for use in a SOQL query to prevent SOQL injection."""
    if value is None:
        return "NULL"
    # Escape single quotes and backslashes
    return str(value).replace('\\', '\\\\').replace('\'', '\\\'')

class TFST_SalesforceService:
    """
    Service class for Salesforce integration
    Handles both OAuth authentication and API operations
    """
    
    def __init__(self):
        self.sf = None
        self.access_token = None
        self.instance_url = None
        self._initialized = False
    
    def _initialize_connection(self):
        """Initialize Salesforce connection using system admin credentials if not already initialized"""
        if self._initialized:
            return
            
        try:
            from flask import current_app
            
            # Skip initialization if required config is missing
            if not all([
                current_app.config.get('SALESFORCE_USERNAME'),
                current_app.config.get('SALESFORCE_PASSWORD')
            ]):
                logger.warning("Salesforce credentials not configured, skipping connection")
                return
                
            self.sf = Salesforce(
                username=current_app.config['SALESFORCE_USERNAME'],
                password=current_app.config['SALESFORCE_PASSWORD'],
                security_token=current_app.config['SALESFORCE_SECURITY_TOKEN'],
                domain='test' if 'test.salesforce.com' in current_app.config['SALESFORCE_LOGIN_URL'] else 'login'
            )
            self.access_token = self.sf.session_id
            self.instance_url = self.sf.sf_instance
            self._initialized = True
            logger.info("Salesforce connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Salesforce connection: {str(e)}")
            # Don't raise in debug mode
            if not current_app.config.get('DEBUG', False):
                raise
    
    # Then add this initialization check to every method
    def get_oauth_url(self, state: str = None) -> str:
        """
        Generate Salesforce OAuth authorization URL for user login
        """
        from flask import current_app
        
        params = {
            'response_type': 'code',
            'client_id': current_app.config['SALESFORCE_CLIENT_ID'],
            'redirect_uri': current_app.config['SALESFORCE_REDIRECT_URI'],
            'scope': 'api id profile email address phone offline_access'
        }
        
        if state:
            params['state'] = state
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        oauth_url = f"{current_app.config['SALESFORCE_LOGIN_URL']}/services/oauth2/authorize?{query_string}"
        
        return oauth_url
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        """
        token_url = f"{current_app.config['SALESFORCE_LOGIN_URL']}/services/oauth2/token"
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': current_app.config['SALESFORCE_CLIENT_ID'],
            'client_secret': current_app.config['SALESFORCE_CLIENT_SECRET'],
            'redirect_uri': current_app.config['SALESFORCE_REDIRECT_URI'],
            'code': code
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        """
        token_url = f"{current_app.config['SALESFORCE_LOGIN_URL']}/services/oauth2/token"

        data = {
            'grant_type': 'refresh_token',
            'client_id': current_app.config['SALESFORCE_CLIENT_ID'],
            'client_secret': current_app.config['SALESFORCE_CLIENT_SECRET'],
            'refresh_token': refresh_token
        }

        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            # Note: A new refresh token is NOT issued in this response
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {str(e)}")
            # If refresh fails, the user might need to log in again
            raise
    
    def get_user_info(self, access_token: str, instance_url: str) -> Dict[str, Any]:
        """
        Get user information from Salesforce using access token
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            self._initialize_connection()
            # Get user ID from token
            identity_url = f"{instance_url}/services/oauth2/userinfo"
            response = requests.get(identity_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise

    def get_carrier_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get carrier information for a specific user from TFST_Master_Carrier
        """
        try:
            # Make sure Salesforce connection is initialized
            self._initialize_connection()
            
            if not self.sf:
                logger.error("Salesforce connection not available.")
                return None

            # Sanitize input to prevent SOQL injection
            safe_user_id = escape_soql(user_id)
            
            # First get the user's email from Salesforce
            user_query = f"SELECT Email FROM User WHERE Id = '{safe_user_id}' LIMIT 1"
            user_result = self.sf.query(user_query)
            
            if user_result['totalSize'] == 0:
                logger.error(f"User not found: {user_id}")
                return None
                
            user_email = user_result['records'][0]['Email']
            safe_user_email = escape_soql(user_email)
            
            # Then query carrier by email
            carrier_query = f"""
                SELECT Id, Name, TFST_Contact_Person__c, TFST_Email__c, TFST_Contact_Number__c,
                    TFST_Service_Types__c, TFST_Reliability_Score__c, Is_Active__c
                FROM TFST_Master_Carrier__c 
                WHERE TFST_Email__c = '{safe_user_email}'
                LIMIT 1
            """
            
            result = self.sf.query(carrier_query)
            
            if result['totalSize'] > 0:
                return result['records'][0]
            return None
                
        except Exception as e:
            logger.error(f"Failed to get carrier info for user {user_id}: {str(e)}")
            return None
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get portal user information from Salesforce by Salesforce User ID
        """
        self._initialize_connection()
        try:
            # This assumes you have a custom object `Portal_User__c` with an external ID field `Salesforce_User_Id__c`
            result = self.sf.Portal_User__c.get_by_custom_id('Salesforce_User_Id__c', user_id)
            return result
        except Exception as e:
            logger.error(f"Failed to get portal user by id {user_id}: {str(e)}")
            return None

    def create_or_update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a portal user in Salesforce.
        This uses the `upsert` method with an external ID field.
        """
        self._initialize_connection()
        salesforce_user_id = user_data.get('salesforce_user_id')
        if not salesforce_user_id:
            raise ValueError("salesforce_user_id is required for upsert")

        # Map application user data to Salesforce custom object fields
        sf_data = {
            'Carrier_Id__c': user_data.get('carrier_id'),
            'Email__c': user_data.get('email'),
            'Name__c': user_data.get('name'),
            'Company_Name__c': user_data.get('company_name'),
            'Phone_Number__c': user_data.get('phone_number'),
            'Can_Update_Shipments__c': user_data.get('can_update_shipments', False),
            'Can_Upload_Documents__c': user_data.get('can_upload_documents', False),
            'Can_View_Analytics__c': user_data.get('can_view_analytics', False),
            'Last_Login__c': user_data.get('last_login'),
            'Is_Active__c': user_data.get('is_active', True)
        }

        try:
            # Upsert user data based on the external ID `Salesforce_User_Id__c`
            result = self.sf.Portal_User__c.upsert(f'Salesforce_User_Id__c/{salesforce_user_id}', sf_data)
            logger.info(f"Upserted portal user {salesforce_user_id}. Status: {result}")

            # After upserting, fetch the full record to return it, ensuring consistency
            return self.get_user_by_id(salesforce_user_id)
        except Exception as e:
            logger.error(f"Failed to upsert portal user {salesforce_user_id}: {str(e)}")
            raise

    def get_carrier_shipments(self, carrier_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get shipments assigned to a specific carrier
        """
        try:
            safe_carrier_id = escape_soql(carrier_id)
            query = f"""
                SELECT Id, Name, TFST_Shipment_Type__c, TFST_Status__c, TFST_Carrier__c,
                       TFST_Current_Coordinates__c, TFST_Driver_Name__c, TFST_Driver_Phone__c,
                       TFST_Predicted_Delivery_Date__c, TFST_Project_Reference__c,
                       Required_Delivery_Date__c, TFST_Total_Weight__c, TFST_Total_Volume__c,
                       TFST_Service_Level__c, TFST_Current_Speed__c, TFST_GPS_Enabled__c
                FROM TFST_Shipment__c
                WHERE TFST_Carrier__c = '{safe_carrier_id}'
                   AND TFST_Status__c NOT IN ('Delivered', 'Cancelled')
                ORDER BY TFST_Predicted_Delivery_Date__c ASC
                LIMIT {limit}
            """
            
            result = self.sf.query(query)
            return result['records']
            
        except Exception as e:
            logger.error(f"Failed to get shipments for carrier {carrier_id}: {str(e)}")
            return []
    
    def get_shipment_details(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific shipment
        """
        try:
            safe_shipment_id = escape_soql(shipment_id)
            query = f"""
                SELECT Id, Name, TFST_Shipment_Type__c, TFST_Status__c, TFST_Carrier__c,
                       TFST_Current_Coordinates__c, TFST_Driver_Name__c, TFST_Driver_Phone__c,
                       TFST_Predicted_Delivery_Date__c, TFST_Project_Reference__c,
                       Required_Delivery_Date__c, TFST_Total_Weight__c, TFST_Total_Volume__c,
                       TFST_Service_Level__c, TFST_Current_Speed__c, TFST_GPS_Enabled__c,
                       Special_Instructions__c, TFST_Transportation_Request__c,
                       TFST_Quote_Request__c, TFST_Service_Order_Number__c
                FROM TFST_Shipment__c
                WHERE Id = '{safe_shipment_id}' OR Name = '{safe_shipment_id}'
                LIMIT 1
            """
            
            result = self.sf.query(query)
            
            if result['totalSize'] > 0:
                return result['records'][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get shipment details for {shipment_id}: {str(e)}")
            return None
    
    def update_shipment_status(self, shipment_id: str, status: str, 
                             location: Dict[str, float] = None, 
                             driver_info: Dict[str, str] = None) -> bool:
        """
        Update shipment status in Salesforce
        """
        try:
            update_data = {
                'TFST_Status__c': status,
                'TFST_Last_Location_Time__c': datetime.utcnow().isoformat()
            }
            
            if location:
                update_data['TFST_Current_Coordinates__c'] = f"{location.get('lat', 0)},{location.get('lng', 0)}"
            
            if driver_info:
                if 'name' in driver_info:
                    update_data['TFST_Driver_Name__c'] = driver_info['name']
                if 'phone' in driver_info:
                    update_data['TFST_Driver_Phone__c'] = driver_info['phone']
            
            # Handle different ID formats (Salesforce ID vs Name)
            if len(shipment_id) == 18 or len(shipment_id) == 15:
                # Salesforce ID format
                result = self.sf.TFST_Shipment__c.update(shipment_id, update_data)
            else:
                # Shipment Name format - need to find the record first
                shipment = self.get_shipment_details(shipment_id)
                if shipment:
                    result = self.sf.TFST_Shipment__c.update(shipment['Id'], update_data)
                else:
                    logger.error(f"Shipment not found: {shipment_id}")
                    return False
            
            logger.info(f"Updated shipment {shipment_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update shipment {shipment_id}: {str(e)}")
            return False
    
    def get_shipment_stages(self, shipment_id: str) -> List[Dict[str, Any]]:
        """
        Get shipment stages for tracking
        """
        try:
            safe_shipment_id = escape_soql(shipment_id)
            query = f"""
                SELECT Id, TFST_Shipment__c, TFST_Stage_Number__c, TFST_Stage_Type__c,
                       TFST_Status__c, TFST_Pickup_Location_Name__c, TFST_Delivery_Location_Name__c,
                       TFST_Scheduled_Start__c, TFST_Scheduled_End__c,
                       TFST_Actual_Start__c, TFST_Actual_End__c,
                       TFST_Carrier__c, TFST_Equipment_Type__c
                FROM TFST_Shipment_Stage__c
                WHERE TFST_Shipment__c = '{safe_shipment_id}'
                ORDER BY TFST_Stage_Number__c ASC
            """
            
            result = self.sf.query(query)
            return result['records']
            
        except Exception as e:
            logger.error(f"Failed to get shipment stages for {shipment_id}: {str(e)}")
            return []
    
    def create_tracking_record(self, shipment_id: str, event_data: Dict[str, Any]) -> bool:
        """
        Create a tracking record in TFST_Tracking__c
        """
        try:
            tracking_data = {
                'TFST_Shipment__c': shipment_id,
                'TFST_Tracking_Event__c': event_data.get('status', 'Update'),
                'TFST_Current_Status__c': event_data.get('status'),
                'Time_of_Event__c': event_data.get('timestamp', datetime.utcnow().isoformat()),
                'TFST_Coordinates__c': f"{event_data.get('location', {}).get('lat', 0)},{event_data.get('location', {}).get('lng', 0)}",
                'TFST_Last_Update_Time__c': datetime.utcnow().isoformat(),
                'TFST_Event_Source__c': 'Carrier Portal'
            }
            
            if 'notes' in event_data:
                tracking_data['TFST_Route_Details__c'] = event_data['notes']
            
            result = self.sf.TFST_Tracking__c.create(tracking_data)
            logger.info(f"Created tracking record for shipment {shipment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create tracking record for {shipment_id}: {str(e)}")
            return False
    
    def get_carrier_performance_metrics(self, carrier_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get carrier performance metrics for analytics
        """
        try:
            # Calculate date range
            start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
            safe_carrier_id = escape_soql(carrier_id)
            
            # Query for completed shipments
            query = f"""
                SELECT COUNT() total_shipments,
                       COUNT_DISTINCT(Id) delivered_shipments
                FROM TFST_Shipment__c
                WHERE TFST_Carrier__c = '{safe_carrier_id}'
                   AND CreatedDate >= {start_date}
            """
            
            # This would need to be enhanced with more complex SOQL queries
            # for detailed analytics like on-time delivery percentage
            result = self.sf.query(query)
            
            return {
                'total_shipments': result.get('totalSize', 0),
                'period_days': days,
                'carrier_id': carrier_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get carrier performance for {carrier_id}: {str(e)}")
            return {}

# Singleton instance
salesforce_service = TFST_SalesforceService()