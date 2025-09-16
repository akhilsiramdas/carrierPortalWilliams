"""
TFST Carrier Portal - Shipments Routes
Shipment management, tracking, and document upload functionality
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.services.salesforce_service import salesforce_service
from app.services.firebase_service import firebase_service
# from app.services.s3_service import s3_service
from app.utils.helpers import allowed_file, validate_file_upload
from datetime import datetime, timezone
import logging
import os

shipments_bp = Blueprint('shipments', __name__)
logger = logging.getLogger(__name__)

@shipments_bp.route('/')
@login_required
def index():
    """Display all carrier shipments"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Get filters from request
        status_filter = request.args.get('status')
        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        
        # Get shipments from Salesforce
        shipments = salesforce_service.get_carrier_shipments(carrier_id, limit=200)
        
        # Get real-time data from Firebase
        realtime_data = firebase_service.get_carrier_shipments_realtime(carrier_id)
        
        # Merge data
        from app.routes.dashboard import merge_shipment_data
        merged_shipments = merge_shipment_data(shipments, realtime_data)
        
        # Apply filters
        if status_filter:
            merged_shipments = [s for s in merged_shipments if s.get('status') == status_filter]
        
        if search_query:
            merged_shipments = [s for s in merged_shipments 
                              if (search_query.lower() in s.get('Name', '').lower() or
                                  search_query.lower() in s.get('TFST_Project_Reference__c', '').lower())]
        
        # Get unique statuses for filter dropdown
        all_statuses = list(set([s.get('status') for s in merged_shipments if s.get('status')]))
        all_statuses.sort()
        
        # Pagination (simple implementation)
        total_shipments = len(merged_shipments)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_shipments = merged_shipments[start:end]
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total_shipments,
            'pages': (total_shipments + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': end < total_shipments
        }
        
        return render_template(
            'shipments/index.html',
            shipments=paginated_shipments,
            statuses=all_statuses,
            current_filters={
                'status': status_filter,
                'search': search_query
            },
            pagination=pagination_info
        )
        
    except Exception as e:
        logger.error(f"Shipments index error: {str(e)}")
        flash('Error loading shipments. Please try again.', 'error')
        return render_template('shipments/index.html', shipments=[], statuses=[])

@shipments_bp.route('/<shipment_id>')
@login_required
def detail(shipment_id):
    """Display detailed shipment information"""
    try:
        # Get shipment details from Salesforce
        shipment = salesforce_service.get_shipment_details(shipment_id)
        
        if not shipment:
            flash('Shipment not found.', 'error')
            return redirect(url_for('shipments.index'))
        
        # Verify this shipment belongs to the current carrier
        carrier_id = session.get('carrier_id')
        if shipment.get('TFST_Carrier__c') != carrier_id:
            flash('You do not have access to this shipment.', 'error')
            return redirect(url_for('shipments.index'))
        
        # Get real-time tracking data from Firebase
        tracking_data = firebase_service.get_shipment_tracking(shipment_id)
        
        # Get status history from Firebase
        status_history = firebase_service.get_shipment_history(shipment_id)
        
        # Get shipment stages from Salesforce
        shipment_stages = salesforce_service.get_shipment_stages(shipment.get('Id'))
        
        # Get documents from Firebase
        documents = firebase_service.get_shipment_documents(shipment_id)
        
        return render_template(
            'shipments/detail.html',
            shipment=shipment,
            tracking_data=tracking_data,
            status_history=status_history,
            shipment_stages=shipment_stages,
            documents=documents
        )
        
    except Exception as e:
        logger.error(f"Shipment detail error for {shipment_id}: {str(e)}")
        flash('Error loading shipment details. Please try again.', 'error')
        return redirect(url_for('shipments.index'))

@shipments_bp.route('/<shipment_id>/update-status', methods=['POST'])
@login_required
def update_status(shipment_id):
    """Update shipment status"""
    if not current_user.can_update_shipments:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        # Verify shipment belongs to carrier
        shipment = salesforce_service.get_shipment_details(shipment_id)
        carrier_id = session.get('carrier_id')
        
        if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify({'success': False, 'error': 'Shipment not found or access denied'}), 404
        
        # Prepare update data
        status = data['status']
        location = data.get('location')
        driver_info = data.get('driver_info')
        notes = data.get('notes', '')
        
        # Update Salesforce
        sf_success = salesforce_service.update_shipment_status(
            shipment_id, status, location, driver_info
        )
        
        if not sf_success:
            return jsonify({'success': False, 'error': 'Failed to update Salesforce'}), 500
        
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
        
        # Create tracking record in Salesforce
        event_data = {
            'status': status,
            'timestamp': tracking_data['timestamp'],
            'location': location,
            'notes': notes
        }
        salesforce_service.create_tracking_record(shipment.get('Id'), event_data)
        
        logger.info(f"Updated shipment {shipment_id} status to {status}")
        
        return jsonify({
            'success': True,
            'message': 'Status updated successfully',
            'salesforce_updated': sf_success,
            'firebase_updated': fb_success
        })
        
    except Exception as e:
        logger.error(f"Error updating status for {shipment_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@shipments_bp.route('/<shipment_id>/upload-document', methods=['POST'])
@login_required
def upload_document(shipment_id):
    """Upload document/photo for shipment"""
    if not current_user.can_upload_documents:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        file = request.files['file']
        document_type = request.form.get('document_type', 'general')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file
        validation_result = validate_file_upload(file)
        if not validation_result['valid']:
            return jsonify({'success': False, 'error': validation_result['error']}), 400
        
        # Verify shipment belongs to carrier
        shipment = salesforce_service.get_shipment_details(shipment_id)
        carrier_id = session.get('carrier_id')
        
        if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify({'success': False, 'error': 'Shipment not found or access denied'}), 404
        
        # Upload to Firebase
        download_url = firebase_service.upload_document(
            file, shipment_id, document_type, carrier_id
        )
        
        if not download_url:
            return jsonify({'success': False, 'error': 'Failed to upload document'}), 500
        
        logger.info(f"Uploaded document for shipment {shipment_id}: {file.filename}")
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document_url': download_url,
            'document_type': document_type
        })
        
    except Exception as e:
        logger.error(f"Error uploading document for {shipment_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@shipments_bp.route('/<shipment_id>/documents')
@login_required
def get_documents(shipment_id):
    """Get documents for a shipment"""
    try:
        # Verify shipment belongs to carrier
        shipment = salesforce_service.get_shipment_details(shipment_id)
        carrier_id = session.get('carrier_id')
        
        if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify({'success': False, 'error': 'Shipment not found or access denied'}), 404
        
        # Get documents from Firebase
        documents = firebase_service.get_shipment_documents(shipment_id)
        
        return jsonify({
            'success': True,
            'documents': documents
        })
        
    except Exception as e:
        logger.error(f"Error getting documents for {shipment_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@shipments_bp.route('/<shipment_id>/tracking-history')
@login_required
def get_tracking_history(shipment_id):
    """Get tracking history for a shipment"""
    try:
        # Verify shipment belongs to carrier
        shipment = salesforce_service.get_shipment_details(shipment_id)
        carrier_id = session.get('carrier_id')
        
        if not shipment or shipment.get('TFST_Carrier__c') != carrier_id:
            return jsonify({'success': False, 'error': 'Shipment not found or access denied'}), 404
        
        # Get tracking history from Firebase
        history = firebase_service.get_shipment_history(shipment_id)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error getting tracking history for {shipment_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@shipments_bp.route('/bulk-update')
@login_required
def bulk_update():
    """Display bulk update page for CSV uploads"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Get available CSV files from S3
        csv_files = s3_service.list_carrier_csv_files(carrier_id)
        
        # Get processing history
        processing_history = s3_service.get_processing_history(carrier_id)
        
        return render_template(
            'shipments/bulk_update.html',
            csv_files=csv_files,
            processing_history=processing_history
        )
        
    except Exception as e:
        logger.error(f"Bulk update page error: {str(e)}")
        flash('Error loading bulk update page. Please try again.', 'error')
        return render_template('shipments/bulk_update.html', csv_files=[], processing_history=[])

@shipments_bp.route('/process-csv/<path:s3_key>', methods=['POST'])
@login_required
def process_csv(s3_key):
    """Process a CSV file from S3"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Process the CSV file
        result = s3_service.process_csv_file(carrier_id, s3_key)
        
        if result['success']:
            flash(f"CSV processed successfully. {result['processed_count']} records updated, "
                  f"{result['failed_count']} failed.", 'success')
        else:
            flash(f"CSV processing failed: {result.get('error', 'Unknown error')}", 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing CSV {s3_key}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@shipments_bp.route('/upload-csv', methods=['POST'])
@login_required
def upload_csv():
    """Upload CSV file to S3 for processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'}), 400
        
        carrier_id = session.get('carrier_id')
        filename = secure_filename(file.filename)
        
        # Upload to S3
        upload_result = s3_service.upload_csv_to_s3(carrier_id, file, filename)
        
        if not upload_result['success']:
            return jsonify({'success': False, 'error': upload_result.get('error')}), 500
        
        # Process the uploaded file
        process_result = s3_service.process_csv_file(carrier_id, upload_result['s3_key'])
        
        return jsonify({
            'success': True,
            'message': 'File uploaded and processed successfully',
            'upload_result': upload_result,
            'process_result': process_result
        })
        
    except Exception as e:
        logger.error(f"Error uploading CSV: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@shipments_bp.route('/map')
@login_required
def map_view():
    """Display map view of shipments"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Get shipments with location data
        realtime_data = firebase_service.get_carrier_shipments_realtime(carrier_id)
        
        # Filter shipments with valid location data
        shipments_with_location = []
        for shipment in realtime_data:
            if shipment.get('location') and 'lat' in shipment['location'] and 'lng' in shipment['location']:
                shipments_with_location.append(shipment)
        
        return render_template(
            'shipments/map.html',
            shipments=shipments_with_location
        )
        
    except Exception as e:
        logger.error(f"Map view error: {str(e)}")
        flash('Error loading map view. Please try again.', 'error')
        return render_template('shipments/map.html', shipments=[])

# Status validation
VALID_STATUSES = [
    'Dispatched',
    'At pickup site',
    'Pickup Complete',
    'In Transit',
    'Delayed',
    'Arrived at site',
    'Delivered',
    'Unloading complete'
]

@shipments_bp.route('/api/valid-statuses')
@login_required
def get_valid_statuses():
    """Get list of valid shipment statuses"""
    return jsonify({
        'success': True,
        'statuses': VALID_STATUSES
    })

@shipments_bp.route('/api/search')
@login_required
def search_shipments():
    """API endpoint for shipment search"""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
        
        carrier_id = session.get('carrier_id')
        
        # Get all carrier shipments
        shipments = salesforce_service.get_carrier_shipments(carrier_id, limit=200)
        
        # Search in shipment names and project references
        results = []
        for shipment in shipments:
            if (query.lower() in shipment.get('Name', '').lower() or 
                query.lower() in shipment.get('TFST_Project_Reference__c', '').lower()):
                results.append({
                    'id': shipment.get('Id'),
                    'name': shipment.get('Name'),
                    'project': shipment.get('TFST_Project_Reference__c'),
                    'status': shipment.get('TFST_Status__c')
                })
                
                if len(results) >= limit:
                    break
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'success': False, 'error': 'Search failed'}), 500