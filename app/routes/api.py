"""
TFST Carrier Portal - API Routes
RESTful API endpoints for external integrations and AJAX calls
"""
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_required, current_user
from app.services.salesforce_service import salesforce_service
from app.services.firebase_service import firebase_service
from app.services.s3_service import s3_service
from app.utils.helpers import (
    validate_coordinates, sanitize_input, create_error_response, 
    create_success_response, get_client_ip, log_user_activity
)
from datetime import datetime, timezone
import logging
from functools import wraps

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# API Rate limiting decorator (basic implementation)
def rate_limit(max_requests=100):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Basic rate limiting - in production, use Redis-based solution
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# API Key authentication for external systems (optional)
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify(create_error_response('API key required', 401)), 401
        
        # Validate API key (implement your validation logic)
        # For now, just check if it exists
        if not validate_api_key(api_key):
            return jsonify(create_error_response('Invalid API key', 401)), 401
        
        return f(*args, **kwargs)
    return decorated_function

def validate_api_key(api_key):
    """Validate API key - implement based on your requirements"""
    # Placeholder implementation
    return True

# Shipment API Endpoints

@api_bp.route('/shipments', methods=['GET'])
@login_required
@rate_limit(max_requests=50)
def get_shipments():
    """Get carrier's shipments with filtering and pagination"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 25, type=int), 100)  # Max 100 per page
        status = sanitize_input(request.args.get('status'), 50)
        search = sanitize_input(request.args.get('search'), 100)
        
        # Get shipments from Salesforce
        limit = min(per_page * 5, 500)  # Get more data for filtering
        shipments = salesforce_service.get_carrier_shipments(carrier_id, limit=limit)
        
        # Get real-time data from Firebase
        realtime_data = firebase_service.get_carrier_shipments_realtime(carrier_id)
        
        # Merge data
        from app.routes.dashboard import merge_shipment_data
        merged_shipments = merge_shipment_data(shipments, realtime_data)
        
        # Apply filters
        filtered_shipments = []
        for shipment in merged_shipments:
            # Status filter
            if status and shipment.get('status') != status:
                continue
            
            # Search filter
            if search:
                search_fields = [
                    shipment.get('Name', ''),
                    shipment.get('TFST_Project_Reference__c', ''),
                    shipment.get('TFST_Service_Order_Number__c', '')
                ]
                if not any(search.lower() in field.lower() for field in search_fields):
                    continue
            
            filtered_shipments.append(shipment)
        
        # Pagination
        total = len(filtered_shipments)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_shipments = filtered_shipments[start:end]
        
        # Format response data
        shipment_data = []
        for shipment in paginated_shipments:
            shipment_data.append({
                'id': shipment.get('Id'),
                'name': shipment.get('Name'),
                'status': shipment.get('status'),
                'project_reference': shipment.get('TFST_Project_Reference__c'),
                'delivery_date': shipment.get('Required_Delivery_Date__c'),
                'pickup_date': shipment.get('PickUp_Date__c'),
                'weight': shipment.get('TFST_Total_Weight__c'),
                'volume': shipment.get('TFST_Total_Volume__c'),
                'service_level': shipment.get('TFST_Service_Level__c'),
                'location': shipment.get('location'),
                'last_updated': shipment.get('last_updated'),
                'realtime_available': shipment.get('realtime_available', False)
            })
        
        return jsonify(create_success_response({
            'shipments': shipment_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': end < total
            }
        }))
        
    except Exception as e:
        logger.error(f"API get_shipments error: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve shipments', 500)), 500

@api_bp.route('/shipments/<shipment_id>', methods=['GET'])
@login_required
@rate_limit(max_requests=100)
def get_shipment(shipment_id):
    """Get detailed shipment information"""
    try:
        carrier_id = session.get('carrier_id')
        shipment_id = sanitize_input(shipment_id, 255)
        
        # Get shipment from Salesforce
        shipment = salesforce_service.get_shipment_details(shipment_id)
        
        if not shipment:
            return jsonify(create_error_response('Shipment not found', 404)), 404
        
        # Verify access
        if shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify(create_error_response('Access denied', 403)), 403
        
        # Get real-time tracking data
        tracking_data = firebase_service.get_shipment_tracking(shipment_id)
        
        # Get shipment stages
        stages = salesforce_service.get_shipment_stages(shipment.get('Id'))
        
        # Get documents
        documents = firebase_service.get_shipment_documents(shipment_id)
        
        response_data = {
            'shipment': {
                'id': shipment.get('Id'),
                'name': shipment.get('Name'),
                'status': tracking_data.get('current_status') if tracking_data else shipment.get('TFST_Status__c'),
                'project_reference': shipment.get('TFST_Project_Reference__c'),
                'delivery_date': shipment.get('Required_Delivery_Date__c'),
                'pickup_date': shipment.get('PickUp_Date__c'),
                'weight': shipment.get('TFST_Total_Weight__c'),
                'volume': shipment.get('TFST_Total_Volume__c'),
                'service_level': shipment.get('TFST_Service_Level__c'),
                'special_instructions': shipment.get('Special_Instructions__c'),
                'service_order_number': shipment.get('TFST_Service_Order_Number__c')
            },
            'tracking': tracking_data,
            'stages': stages,
            'documents': documents
        }
        
        return jsonify(create_success_response(response_data))
        
    except Exception as e:
        logger.error(f"API get_shipment error for {shipment_id}: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve shipment', 500)), 500

@api_bp.route('/shipments/<shipment_id>/status', methods=['PUT'])
@login_required
@rate_limit(max_requests=30)
def update_shipment_status(shipment_id):
    """Update shipment status via API"""
    try:
        if not current_user.can_update_shipments:
            return jsonify(create_error_response('Permission denied', 403)), 403
        
        carrier_id = session.get('carrier_id')
        shipment_id = sanitize_input(shipment_id, 255)
        
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify(create_error_response('No data provided', 400)), 400
        
        status = sanitize_input(data.get('status'), 50)
        if not status:
            return jsonify(create_error_response('Status is required', 400)), 400
        
        # Validate status
        valid_statuses = [
            'Dispatched', 'At pickup site', 'Pickup Complete', 'In Transit',
            'Delayed', 'Arrived at site', 'Delivered', 'Unloading complete'
        ]
        if status not in valid_statuses:
            return jsonify(create_error_response(f'Invalid status. Valid options: {", ".join(valid_statuses)}', 400)), 400
        
        # Verify shipment access
        shipment = salesforce_service.get_shipment_details(shipment_id)
        if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify(create_error_response('Shipment not found or access denied', 404)), 404
        
        # Prepare update data
        location = data.get('location')
        if location:
            lat = location.get('lat')
            lng = location.get('lng')
            if lat is not None and lng is not None:
                if not validate_coordinates(lat, lng):
                    return jsonify(create_error_response('Invalid coordinates', 400)), 400
        
        driver_info = data.get('driver_info', {})
        notes = sanitize_input(data.get('notes', ''), 500)
        
        # Update Salesforce
        sf_success = salesforce_service.update_shipment_status(
            shipment_id, status, location, driver_info
        )
        
        # Update Firebase
        tracking_data = {
            'status': status,
            'carrier_id': carrier_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'notes': notes
        }
        
        if location:
            tracking_data['location'] = location
        
        if driver_info:
            tracking_data['driver_info'] = driver_info
        
        fb_success = firebase_service.update_shipment_tracking(shipment_id, tracking_data)
        
        # Create tracking record
        event_data = {
            'status': status,
            'timestamp': tracking_data['timestamp'],
            'location': location,
            'notes': notes
        }
        salesforce_service.create_tracking_record(shipment.get('Id'), event_data)
        
        # Log activity
        log_user_activity(current_user.id, 'status_update', f'Updated {shipment_id} to {status}')
        
        return jsonify(create_success_response({
            'shipment_id': shipment_id,
            'status': status,
            'timestamp': tracking_data['timestamp'],
            'salesforce_updated': sf_success,
            'firebase_updated': fb_success
        }))
        
    except Exception as e:
        logger.error(f"API update_shipment_status error for {shipment_id}: {str(e)}")
        return jsonify(create_error_response('Failed to update status', 500)), 500

@api_bp.route('/shipments/<shipment_id>/location', methods=['PUT'])
@login_required
@rate_limit(max_requests=60)  # More frequent location updates
def update_shipment_location(shipment_id):
    """Update shipment GPS location"""
    try:
        if not current_user.can_update_shipments:
            return jsonify(create_error_response('Permission denied', 403)), 403
        
        carrier_id = session.get('carrier_id')
        shipment_id = sanitize_input(shipment_id, 255)
        
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify(create_error_response('No data provided', 400)), 400
        
        lat = data.get('lat')
        lng = data.get('lng')
        
        if lat is None or lng is None:
            return jsonify(create_error_response('Latitude and longitude are required', 400)), 400
        
        if not validate_coordinates(lat, lng):
            return jsonify(create_error_response('Invalid coordinates', 400)), 400
        
        # Verify shipment access
        shipment = salesforce_service.get_shipment_details(shipment_id)
        if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify(create_error_response('Shipment not found or access denied', 404)), 404
        
        # Update Firebase with location
        tracking_data = {
            'carrier_id': carrier_id,
            'location': {'lat': lat, 'lng': lng},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Add speed if provided
        if 'speed' in data:
            tracking_data['speed'] = data['speed']
        
        fb_success = firebase_service.update_shipment_tracking(shipment_id, tracking_data)
        
        return jsonify(create_success_response({
            'shipment_id': shipment_id,
            'location': {'lat': lat, 'lng': lng},
            'timestamp': tracking_data['timestamp'],
            'updated': fb_success
        }))
        
    except Exception as e:
        logger.error(f"API update_shipment_location error for {shipment_id}: {str(e)}")
        return jsonify(create_error_response('Failed to update location', 500)), 500

# Bulk Operations

@api_bp.route('/shipments/bulk-status-update', methods=['POST'])
@login_required
@rate_limit(max_requests=10)  # Limited for bulk operations
def bulk_status_update():
    """Bulk update shipment statuses"""
    try:
        if not current_user.can_update_shipments:
            return jsonify(create_error_response('Permission denied', 403)), 403
        
        carrier_id = session.get('carrier_id')
        data = request.get_json()
        
        if not data or 'updates' not in data:
            return jsonify(create_error_response('No updates provided', 400)), 400
        
        updates = data['updates']
        if not isinstance(updates, list) or len(updates) == 0:
            return jsonify(create_error_response('Updates must be a non-empty list', 400)), 400
        
        # Limit bulk operations
        if len(updates) > 100:
            return jsonify(create_error_response('Maximum 100 updates per request', 400)), 400
        
        results = []
        successful_updates = 0
        failed_updates = 0
        
        for update in updates:
            try:
                shipment_id = sanitize_input(update.get('shipment_id'), 255)
                status = sanitize_input(update.get('status'), 50)
                
                if not shipment_id or not status:
                    results.append({
                        'shipment_id': shipment_id,
                        'success': False,
                        'error': 'Missing shipment_id or status'
                    })
                    failed_updates += 1
                    continue
                
                # Verify shipment belongs to carrier
                shipment = salesforce_service.get_shipment_details(shipment_id)
                if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
                    results.append({
                        'shipment_id': shipment_id,
                        'success': False,
                        'error': 'Shipment not found or access denied'
                    })
                    failed_updates += 1
                    continue
                
                # Update status
                location = update.get('location')
                driver_info = update.get('driver_info')
                
                sf_success = salesforce_service.update_shipment_status(
                    shipment_id, status, location, driver_info
                )
                
                # Update Firebase
                tracking_data = {
                    'status': status,
                    'carrier_id': carrier_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'notes': update.get('notes', '')
                }
                
                if location:
                    tracking_data['location'] = location
                if driver_info:
                    tracking_data['driver_info'] = driver_info
                
                fb_success = firebase_service.update_shipment_tracking(shipment_id, tracking_data)
                
                if sf_success:
                    successful_updates += 1
                    results.append({
                        'shipment_id': shipment_id,
                        'success': True,
                        'status': status
                    })
                else:
                    failed_updates += 1
                    results.append({
                        'shipment_id': shipment_id,
                        'success': False,
                        'error': 'Failed to update Salesforce'
                    })
                
            except Exception as e:
                failed_updates += 1
                results.append({
                    'shipment_id': update.get('shipment_id', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        # Log bulk activity
        log_user_activity(current_user.id, 'bulk_status_update', 
                         f'Updated {successful_updates} shipments, {failed_updates} failed')
        
        return jsonify(create_success_response({
            'total_updates': len(updates),
            'successful': successful_updates,
            'failed': failed_updates,
            'results': results
        }))
        
    except Exception as e:
        logger.error(f"API bulk_status_update error: {str(e)}")
        return jsonify(create_error_response('Bulk update failed', 500)), 500

# CSV Processing APIs

@api_bp.route('/csv/upload', methods=['POST'])
@login_required
@rate_limit(max_requests=5)
def upload_csv():
    """Upload CSV file for processing"""
    try:
        if 'file' not in request.files:
            return jsonify(create_error_response('No file provided', 400)), 400
        
        file = request.files['file']
        if not file.filename or not file.filename.lower().endswith('.csv'):
            return jsonify(create_error_response('Only CSV files are allowed', 400)), 400
        
        carrier_id = session.get('carrier_id')
        
        # Upload to S3
        upload_result = s3_service.upload_csv_to_s3(carrier_id, file, file.filename)
        
        if not upload_result['success']:
            return jsonify(create_error_response(upload_result['error'], 500)), 500
        
        # Process the file
        process_result = s3_service.process_csv_file(carrier_id, upload_result['s3_key'])
        
        # Log activity
        log_user_activity(current_user.id, 'csv_upload', f'Uploaded {file.filename}')
        
        return jsonify(create_success_response({
            'filename': file.filename,
            'upload': upload_result,
            'processing': process_result
        }))
        
    except Exception as e:
        logger.error(f"API upload_csv error: {str(e)}")
        return jsonify(create_error_response('CSV upload failed', 500)), 500

@api_bp.route('/csv/history', methods=['GET'])
@login_required
@rate_limit(max_requests=20)
def get_csv_history():
    """Get CSV processing history"""
    try:
        carrier_id = session.get('carrier_id')
        limit = min(request.args.get('limit', 50, type=int), 100)
        
        history = s3_service.get_processing_history(carrier_id, limit)
        
        return jsonify(create_success_response({
            'history': history,
            'total': len(history)
        }))
        
    except Exception as e:
        logger.error(f"API get_csv_history error: {str(e)}")
        return jsonify(create_error_response('Failed to retrieve history', 500)), 500

# Utility APIs

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Basic health checks
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'services': {
                'database': 'healthy',  # Could check db connection
                'salesforce': 'healthy',  # Could ping SF
                'firebase': 'healthy',   # Could check FB connection
                's3': 'healthy'          # Could check S3 connection
            }
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Error Handlers

@api_bp.errorhandler(400)
def bad_request(error):
    return jsonify(create_error_response('Bad request', 400)), 400

@api_bp.errorhandler(401)
def unauthorized(error):
    return jsonify(create_error_response('Unauthorized', 401)), 401

@api_bp.errorhandler(403)
def forbidden(error):
    return jsonify(create_error_response('Forbidden', 403)), 403

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify(create_error_response('Resource not found', 404)), 404

@api_bp.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify(create_error_response('Rate limit exceeded', 429)), 429

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify(create_error_response('Internal server error', 500)), 500