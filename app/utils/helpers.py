"""
TFST Carrier Portal - Helper Utilities
Common utility functions for file handling, validation, etc.
"""
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'pdf', 'csv'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_file_upload(file) -> Dict[str, Any]:
    """Validate file upload requirements"""
    try:
        # Check if filename is provided
        if not file.filename:
            return {'valid': False, 'error': 'No filename provided'}
        
        # Check file extension
        if not allowed_file(file.filename):
            return {'valid': False, 'error': 'File type not allowed'}
        
        # Check file size (16MB limit)
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if file_size > max_size:
            return {'valid': False, 'error': f'File size exceeds {max_size // (1024*1024)}MB limit'}
        
        if file_size == 0:
            return {'valid': False, 'error': 'File is empty'}
        
        return {'valid': True}
        
    except Exception as e:
        logger.error(f"File validation error: {str(e)}")
        return {'valid': False, 'error': 'File validation failed'}

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename while preserving extension"""
    try:
        secure_name = secure_filename(original_filename)
        name, ext = os.path.splitext(secure_name)
        unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        return unique_name
    except Exception as e:
        logger.error(f"Error generating unique filename: {str(e)}")
        return f"file_{uuid.uuid4().hex[:8]}.txt"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(size_units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {size_units[unit_index]}"

def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate GPS coordinates"""
    try:
        lat = float(lat)
        lng = float(lng)
        
        # Check valid ranges
        if not (-90 <= lat <= 90):
            return False
        
        if not (-180 <= lng <= 180):
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False

def format_phone_number(phone: str) -> str:
    """Format phone number consistently"""
    if not phone:
        return ""
    
    # Remove all non-numeric characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone  # Return original if can't format

def sanitize_input(input_string: str, max_length: int = None) -> str:
    """Sanitize user input"""
    if not input_string:
        return ""
    
    # Strip whitespace
    sanitized = input_string.strip()
    
    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def parse_csv_timestamp(timestamp_str: str) -> str:
    """Parse various timestamp formats to ISO format"""
    from datetime import datetime, timezone
    import dateutil.parser as date_parser
    
    if not timestamp_str:
        return datetime.now(timezone.utc).isoformat()
    
    try:
        # Try parsing with dateutil (handles many formats)
        parsed_date = date_parser.parse(timestamp_str)
        
        # Convert to UTC if no timezone info
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        
        return parsed_date.isoformat()
        
    except Exception as e:
        logger.warning(f"Could not parse timestamp '{timestamp_str}': {str(e)}")
        return datetime.now(timezone.utc).isoformat()

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two GPS coordinates in miles"""
    from math import radians, cos, sin, asin, sqrt
    
    try:
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in miles
        r = 3956
        
        return c * r
        
    except Exception as e:
        logger.error(f"Error calculating distance: {str(e)}")
        return 0.0

def get_status_color(status: str) -> str:
    """Get color code for shipment status"""
    status_colors = {
        'Dispatched': '#FFA500',           # Orange
        'At pickup site': '#FFD700',       # Gold
        'Pickup Complete': '#32CD32',       # Lime Green
        'In Transit': '#1E90FF',           # Dodger Blue
        'Delayed': '#FF4500',              # Red Orange
        'Arrived at site': '#9370DB',      # Medium Purple
        'Delivered': '#228B22',            # Forest Green
        'Unloading complete': '#008000'    # Green
    }
    
    return status_colors.get(status, '#708090')  # Slate Gray as default

def get_priority_level(shipment: Dict[str, Any]) -> str:
    """Determine shipment priority level"""
    try:
        # Check service level
        service_level = shipment.get('TFST_Service_Level__c', '').lower()
        if 'urgent' in service_level or 'critical' in service_level:
            return 'high'
        
        # Check if it's on critical path
        if shipment.get('Critical_Path') == True:
            return 'high'
        
        # Check delivery date proximity
        delivery_date = shipment.get('Required_Delivery_Date__c')
        if delivery_date:
            from datetime import datetime, timedelta
            try:
                delivery_datetime = datetime.strptime(delivery_date, '%Y-%m-%d')
                days_until_delivery = (delivery_datetime.date() - datetime.now().date()).days
                
                if days_until_delivery <= 1:
                    return 'high'
                elif days_until_delivery <= 3:
                    return 'medium'
            except:
                pass
        
        return 'normal'
        
    except Exception as e:
        logger.error(f"Error determining priority level: {str(e)}")
        return 'normal'

def format_currency(amount: float, currency: str = 'USD') -> str:
    """Format currency amount"""
    try:
        if currency == 'USD':
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return "N/A"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def is_json_request(request):
    """Check if request expects JSON response"""
    return (request.headers.get('Content-Type', '').startswith('application/json') or
            request.headers.get('Accept', '').startswith('application/json') or
            request.is_json)

def log_user_activity(user_id: int, activity: str, details: str = None):
    """Log user activity for audit trail"""
    try:
        logger.info(f"User {user_id} - {activity}" + (f": {details}" if details else ""))
        
        # Here you could also save to database audit table if needed
        # audit_log = UserActivityLog(
        #     user_id=user_id,
        #     activity=activity,
        #     details=details,
        #     timestamp=datetime.utcnow()
        # )
        # db.session.add(audit_log)
        # db.session.commit()
        
    except Exception as e:
        logger.error(f"Error logging user activity: {str(e)}")

def create_error_response(message: str, status_code: int = 400, details: Dict = None) -> Dict:
    """Create standardized error response"""
    response = {
        'success': False,
        'error': message,
        'status_code': status_code
    }
    
    if details:
        response['details'] = details
    
    return response

def create_success_response(data: Any = None, message: str = None) -> Dict:
    """Create standardized success response"""
    response = {
        'success': True
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    return response

def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    
    if not email:
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def get_client_ip(request):
    """Get client IP address from request"""
    # Check for forwarded IP (proxy/load balancer)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr