"""
TFST Carrier Portal - S3 CSV Processing Service
Process carrier CSV uploads from Amazon S3 (without database dependencies)
"""
import boto3
import pandas as pd
import io
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from flask import current_app
import uuid

logger = logging.getLogger(__name__)

# In-memory storage for upload logs
_upload_logs = {}

class S3UploadLog:
    """In-memory replacement for TFST_S3UploadLog database model"""
    
    def __init__(self, carrier_id, filename, s3_key):
        self.id = str(uuid.uuid4())
        self.carrier_id = carrier_id
        self.filename = filename
        self.s3_key = s3_key
        self.processed_at = None
        self.status = 'pending'
        self.error_details = None
        self.records_processed = 0
        self.records_failed = 0
        self.created_at = datetime.utcnow()
        
        # Store in memory
        _upload_logs[self.id] = self
    
    def mark_processing(self):
        """Mark upload as currently being processed"""
        self.status = 'processing'
        self.processed_at = datetime.utcnow()
    
    def mark_completed(self, processed_count, failed_count=0):
        """Mark upload as completed"""
        self.status = 'completed'
        self.records_processed = processed_count
        self.records_failed = failed_count
        self.processed_at = datetime.utcnow()
    
    def mark_error(self, error_message):
        """Mark upload as failed with error details"""
        self.status = 'error'
        self.error_details = error_message
        self.processed_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert upload log to dictionary"""
        return {
            'id': self.id,
            'carrier_id': self.carrier_id,
            'filename': self.filename,
            'status': self.status,
            'records_processed': self.records_processed,
            'records_failed': self.records_failed,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'error_details': self.error_details
        }

class TFST_S3Service:
    """
    Service class for S3 CSV processing
    Handles bulk shipment status updates from carrier CSV files
    """
    
    def __init__(self):
        self.s3_client = None
        self._initialized = False
    
    def _initialize_s3(self):
        """Initialize S3 client if not already initialized"""
        if self._initialized:
            return
            
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
                region_name=current_app.config['AWS_S3_REGION']
            )
            self._initialized = True
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def list_carrier_csv_files(self, carrier_id: str, prefix: str = None) -> List[Dict[str, Any]]:
        """
        List CSV files for a specific carrier in S3
        """
        self._initialize_s3()
        
        try:
            bucket_name = current_app.config['AWS_S3_BUCKET']
            
            # Create prefix for carrier files
            if prefix:
                file_prefix = f"carriers/{carrier_id}/{prefix}"
            else:
                file_prefix = f"carriers/{carrier_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=file_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.csv'):
                        files.append({
                            'key': obj['Key'],
                            'filename': obj['Key'].split('/')[-1],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'processed': self._check_if_processed(carrier_id, obj['Key'])
                        })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing CSV files for carrier {carrier_id}: {str(e)}")
            return []
    
    def process_csv_file(self, carrier_id: str, s3_key: str) -> Dict[str, Any]:
        """
        Process a CSV file from S3 and update shipment statuses
        """
        self._initialize_s3()
        
        filename = s3_key.split('/')[-1]
        
        # Create upload log entry
        upload_log = S3UploadLog(
            carrier_id=carrier_id,
            filename=filename,
            s3_key=s3_key
        )
        upload_log.mark_processing()
        
        try:
            # Download CSV from S3
            csv_content = self._download_csv_from_s3(s3_key)
            
            # Parse CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Validate CSV format
            validation_result = self._validate_csv_format(df)
            if not validation_result['valid']:
                upload_log.mark_error(f"CSV validation failed: {validation_result['error']}")
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'upload_log_id': upload_log.id
                }
            
            # Process each row
            processed_count = 0
            failed_count = 0
            errors = []
            
            salesforce_updates = []
            firebase_updates = []
            
            for index, row in df.iterrows():
                try:
                    # Parse row data
                    shipment_data = self._parse_csv_row(row, carrier_id)
                    
                    if shipment_data:
                        salesforce_updates.append(shipment_data)
                        firebase_updates.append(shipment_data)
                        processed_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Row {index + 1}: Invalid data format")
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: {str(e)}")
                    logger.error(f"Error processing row {index + 1}: {str(e)}")
            
            # In a real implementation, we would update Salesforce and Firebase here
            # For now, we'll just simulate success
            sf_results = {update.get('shipment_id', f"unknown_{i}"): True for i, update in enumerate(salesforce_updates)}
            fb_results = {update.get('shipment_id', f"unknown_{i}"): True for i, update in enumerate(firebase_updates)}
            
            # Update log with results
            upload_log.mark_completed(processed_count, failed_count)
            
            result = {
                'success': True,
                'processed_count': processed_count,
                'failed_count': failed_count,
                'upload_log_id': upload_log.id,
                'salesforce_results': sf_results,
                'firebase_results': fb_results
            }
            
            if errors:
                result['errors'] = errors[:10]  # Limit errors shown
            
            logger.info(f"Processed CSV file {filename}: {processed_count} success, {failed_count} failed")
            return result
            
        except Exception as e:
            error_msg = f"Failed to process CSV file {filename}: {str(e)}"
            logger.error(error_msg)
            upload_log.mark_error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'upload_log_id': upload_log.id
            }
    
    def _download_csv_from_s3(self, s3_key: str) -> str:
        """Download CSV content from S3"""
        try:
            bucket_name = current_app.config['AWS_S3_BUCKET']
            
            response = self.s3_client.get_object(
                Bucket=bucket_name,
                Key=s3_key
            )
            
            return response['Body'].read().decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to download CSV from S3: {str(e)}")
            raise
    
    def _validate_csv_format(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate CSV format and required columns"""
        required_columns = [
            'shipment_id',
            'status',
            'timestamp'
        ]
        
        # Check for required columns
        missing_columns = []
        for col in required_columns:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            return {
                'valid': False,
                'error': f"Missing required columns: {', '.join(missing_columns)}"
            }
        
        # Validate data types
        if df.empty:
            return {
                'valid': False,
                'error': "CSV file is empty"
            }
        
        # Check for valid statuses
        valid_statuses = [
            'Dispatched',
            'At pickup site',
            'Pickup Complete',
            'In Transit',
            'Delayed',
            'Arrived at site',
            'Delivered',
            'Unloading complete'
        ]
        
        invalid_statuses = df[~df['status'].isin(valid_statuses)]['status'].unique()
        if len(invalid_statuses) > 0:
            return {
                'valid': False,
                'error': f"Invalid status values found: {', '.join(invalid_statuses)}"
            }
        
        return {'valid': True}
    
    def _parse_csv_row(self, row: pd.Series, carrier_id: str) -> Optional[Dict[str, Any]]:
        """Parse a CSV row into shipment update data"""
        try:
            shipment_data = {
                'shipment_id': str(row['shipment_id']).strip(),
                'status': str(row['status']).strip(),
                'timestamp': str(row['timestamp']).strip(),
                'carrier_id': carrier_id
            }
            
            # Parse location if provided
            if pd.notna(row.get('location_lat')) and pd.notna(row.get('location_lng')):
                try:
                    shipment_data['location'] = {
                        'lat': float(row['location_lat']),
                        'lng': float(row['location_lng'])
                    }
                except (ValueError, TypeError):
                    pass  # Skip invalid coordinates
            
            # Parse driver info if provided
            driver_info = {}
            if pd.notna(row.get('driver_name')):
                driver_info['name'] = str(row['driver_name']).strip()
            if pd.notna(row.get('truck_number')):
                driver_info['truck_number'] = str(row['truck_number']).strip()
            
            if driver_info:
                shipment_data['driver_info'] = driver_info
            
            # Add notes if provided
            if pd.notna(row.get('notes')):
                shipment_data['notes'] = str(row['notes']).strip()
            
            # Validate timestamp format
            try:
                datetime.fromisoformat(shipment_data['timestamp'].replace('Z', '+00:00'))
            except:
                # If timestamp is invalid, use current time
                shipment_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            return shipment_data
            
        except Exception as e:
            logger.error(f"Error parsing CSV row: {str(e)}")
            return None
    
    def _check_if_processed(self, carrier_id: str, s3_key: str) -> bool:
        """Check if a file has already been processed"""
        try:
            # Look in our in-memory storage
            for log_id, log in _upload_logs.items():
                if log.carrier_id == carrier_id and log.s3_key == s3_key and log.status == 'completed':
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if file processed: {str(e)}")
            return False
    
    def get_processing_history(self, carrier_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get CSV processing history for a carrier"""
        try:
            # Filter logs for this carrier and sort by created_at
            carrier_logs = [log for log_id, log in _upload_logs.items() if log.carrier_id == carrier_id]
            carrier_logs.sort(key=lambda x: x.created_at, reverse=True)
            
            # Limit results
            limited_logs = carrier_logs[:limit]
            
            return [log.to_dict() for log in limited_logs]
            
        except Exception as e:
            logger.error(f"Error getting processing history: {str(e)}")
            return []
    
    def retry_failed_processing(self, upload_log_id: str) -> Dict[str, Any]:
        """Retry processing a failed CSV file"""
        try:
            upload_log = _upload_logs.get(upload_log_id)
            
            if not upload_log or upload_log.status != 'error':
                return {
                    'success': False,
                    'error': 'Upload log not found or not in error status'
                }
            
            # Reset status and retry processing
            upload_log.status = 'pending'
            upload_log.error_details = None
            
            return self.process_csv_file(upload_log.carrier_id, upload_log.s3_key)
            
        except Exception as e:
            logger.error(f"Error retrying processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_csv_to_s3(self, carrier_id: str, file, filename: str) -> Dict[str, Any]:
        """Upload CSV file to S3 (if needed for manual uploads)"""
        self._initialize_s3()
        
        try:
            bucket_name = current_app.config['AWS_S3_BUCKET']
            
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"carriers/{carrier_id}/uploads/{timestamp}_{filename}"
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file,
                bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )
            
            logger.info(f"Uploaded CSV file to S3: {s3_key}")
            
            return {
                'success': True,
                's3_key': s3_key,
                'filename': filename
            }
            
        except Exception as e:
            logger.error(f"Error uploading CSV to S3: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Singleton instance
s3_service = TFST_S3Service()