"""
TFST Carrier Portal - Firebase Integration Service
Direct Firebase connection for real-time shipment tracking and document storage
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask import current_app
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class TFST_FirebaseService:
    """
    Service class for Firebase integration
    Handles real-time shipment tracking and document storage
    """
    
    def __init__(self):
        self.db = None
        self.bucket = None
        self._initialized = False
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK if not already initialized"""
        if self._initialized:
            return
            
        try:
            # Check if Firebase app is already initialized
            try:
                app = firebase_admin.get_app()
                logger.info("Firebase app already initialized")
            except ValueError:
                # Initialize Firebase with service account credentials
                from flask import current_app
                
                cred_dict = {
                    "type": "service_account",
                    "project_id": current_app.config['FIREBASE_PROJECT_ID'],
                    "private_key_id": current_app.config['FIREBASE_PRIVATE_KEY_ID'],
                    "private_key": current_app.config['FIREBASE_PRIVATE_KEY'],
                    "client_email": current_app.config['FIREBASE_CLIENT_EMAIL'],
                    "client_id": current_app.config['FIREBASE_CLIENT_ID'],
                    "auth_uri": current_app.config['FIREBASE_AUTH_URI'],
                    "token_uri": current_app.config['FIREBASE_TOKEN_URI'],
                }
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': f"{current_app.config['FIREBASE_PROJECT_ID']}.appspot.com"
                })
                logger.info("Firebase app initialized successfully")
            
            # Initialize Firestore and Storage
            self.db = firestore.client()
            self.bucket = storage.bucket()
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    def update_shipment_tracking(self, shipment_id: str, tracking_data: Dict[str, Any]) -> bool:
        """
        Update real-time shipment tracking data in Firestore
        """
        try:
            self._initialize_firebase()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Prepare tracking update
            update_data = {
                'shipment_id': shipment_id,
                'current_status': tracking_data.get('status'),
                'last_updated': timestamp,
                'carrier_id': tracking_data.get('carrier_id'),
                'updated_by': 'carrier_portal'
            }
            
            # Add location if provided
            if 'location' in tracking_data:
                update_data['location'] = {
                    'lat': tracking_data['location'].get('lat', 0),
                    'lng': tracking_data['location'].get('lng', 0),
                    'timestamp': timestamp
                }
            
            # Add driver information if provided
            if 'driver_info' in tracking_data:
                update_data['driver_info'] = tracking_data['driver_info']
            
            # Add notes if provided
            if 'notes' in tracking_data:
                update_data['notes'] = tracking_data['notes']
            
            # Update current tracking data
            doc_ref = self.db.collection('shipment_tracking').document(shipment_id)
            doc_ref.set(update_data, merge=True)
            
            # Add to status history
            history_ref = self.db.collection('shipment_tracking').document(shipment_id).collection('status_history')
            history_data = {
                'status': tracking_data.get('status'),
                'timestamp': timestamp,
                'location': update_data.get('location'),
                'notes': tracking_data.get('notes', ''),
                'updated_by': 'carrier_portal'
            }
            history_ref.add(history_data)
            
            logger.info(f"Updated Firebase tracking for shipment {shipment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Firebase tracking for {shipment_id}: {str(e)}")
            return False
    
    def get_shipment_tracking(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current tracking data for a shipment
        """
        try:
            self._initialize_firebase()
            doc_ref = self.db.collection('shipment_tracking').document(shipment_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Firebase tracking for {shipment_id}: {str(e)}")
            return None
    
    def get_shipment_history(self, shipment_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get status history for a shipment
        """
        try:
            self._initialize_firebase()
            history_ref = self.db.collection('shipment_tracking').document(shipment_id).collection('status_history')
            query = history_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            
            history = []
            for doc in query.stream():
                history.append(doc.to_dict())
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get Firebase history for {shipment_id}: {str(e)}")
            return []
    
    def upload_document(self, file, shipment_id: str, document_type: str, carrier_id: str) -> Optional[str]:
        """
        Upload document to Firebase Storage
        document_type: 'pickup_photo', 'delivery_photo', 'pod_document', etc.
        """
        try:
            self._initialize_firebase()
            # Generate unique filename
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            # Create storage path
            storage_path = f"documents/{carrier_id}/{shipment_id}/{document_type}/{unique_filename}"
            
            # Upload to Firebase Storage
            blob = self.bucket.blob(storage_path)
            blob.upload_from_file(file, content_type=file.content_type)
            
            # Make the blob publicly accessible (or set appropriate permissions)
            blob.make_public()
            
            # Get download URL
            download_url = blob.public_url
            
            # Update Firestore document record
            doc_ref = self.db.collection('documents').document(shipment_id)
            doc_data = doc_ref.get()
            
            if doc_data.exists:
                current_data = doc_data.to_dict()
            else:
                current_data = {'shipment_id': shipment_id}
            
            # Add document URL to appropriate category
            if document_type not in current_data:
                current_data[document_type] = []
            
            current_data[document_type].append({
                'url': download_url,
                'filename': filename,
                'uploaded_by': carrier_id,
                'uploaded_at': datetime.now(timezone.utc).isoformat(),
                'file_size': blob.size if hasattr(blob, 'size') else None,
                'content_type': file.content_type
            })
            
            doc_ref.set(current_data, merge=True)
            
            logger.info(f"Uploaded document for shipment {shipment_id}: {filename}")
            return download_url
            
        except Exception as e:
            logger.error(f"Failed to upload document for {shipment_id}: {str(e)}")
            return None
    
    def get_shipment_documents(self, shipment_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all documents for a shipment
        """
        try:
            self._initialize_firebase()
            doc_ref = self.db.collection('documents').document(shipment_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Remove shipment_id from the response
                data.pop('shipment_id', None)
                return data
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get documents for {shipment_id}: {str(e)}")
            return {}
    
    def delete_document(self, shipment_id: str, document_type: str, document_url: str, carrier_id: str) -> bool:
        """
        Delete a document from Firebase Storage and Firestore
        """
        try:
            self._initialize_firebase()
            # Extract storage path from URL
            # This is a simplified approach - in production, you'd want to store the path
            storage_path = document_url.split(f"{current_app.config['FIREBASE_PROJECT_ID']}.appspot.com/")[1]
            
            # Delete from Storage
            blob = self.bucket.blob(storage_path)
            blob.delete()
            
            # Update Firestore record
            doc_ref = self.db.collection('documents').document(shipment_id)
            doc_data = doc_ref.get()
            
            if doc_data.exists:
                current_data = doc_data.to_dict()
                
                if document_type in current_data:
                    # Remove the document from the list
                    current_data[document_type] = [
                        doc for doc in current_data[document_type] 
                        if doc.get('url') != document_url
                    ]
                    
                    doc_ref.set(current_data, merge=True)
            
            logger.info(f"Deleted document for shipment {shipment_id}: {document_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document for {shipment_id}: {str(e)}")
            return False
    
    def get_carrier_shipments_realtime(self, carrier_id: str) -> List[Dict[str, Any]]:
        """
        Get real-time tracking data for all shipments assigned to a carrier
        """
        try:
            self._initialize_firebase()
            # Query shipments by carrier_id
            query = self.db.collection('shipment_tracking').where('carrier_id', '==', carrier_id)
            
            shipments = []
            for doc in query.stream():
                shipment_data = doc.to_dict()
                shipment_data['id'] = doc.id
                shipments.append(shipment_data)
            
            return shipments
            
        except Exception as e:
            logger.error(f"Failed to get carrier shipments for {carrier_id}: {str(e)}")
            return []
    
    def batch_update_shipments(self, updates: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Batch update multiple shipments (useful for CSV processing)
        """
        results = {}
        
        try:
            self._initialize_firebase()
            # Process in batches of 500 (Firestore limit)
            batch_size = 500
            for i in range(0, len(updates), batch_size):
                batch = self.db.batch()
                batch_updates = updates[i:i + batch_size]
                
                for update in batch_updates:
                    shipment_id = update.get('shipment_id')
                    if not shipment_id:
                        results[f"update_{i}"] = False
                        continue
                    
                    doc_ref = self.db.collection('shipment_tracking').document(shipment_id)
                    
                    # Prepare the update data
                    timestamp = datetime.now(timezone.utc).isoformat()
                    tracking_data = {
                        'shipment_id': shipment_id,
                        'current_status': update.get('status'),
                        'last_updated': timestamp,
                        'carrier_id': update.get('carrier_id'),
                        'updated_by': 'csv_batch_update'
                    }
                    
                    if 'location' in update:
                        tracking_data['location'] = update['location']
                    
                    if 'driver_info' in update:
                        tracking_data['driver_info'] = update['driver_info']
                    
                    batch.set(doc_ref, tracking_data, merge=True)
                    results[shipment_id] = True
                
                # Commit the batch
                batch.commit()
                
            logger.info(f"Batch updated {len(updates)} shipments")
            
        except Exception as e:
            logger.error(f"Failed to batch update shipments: {str(e)}")
            # Mark all updates as failed
            for update in updates:
                if 'shipment_id' in update:
                    results[update['shipment_id']] = False
        
        return results
    
    def create_realtime_listener(self, carrier_id: str, callback):
        """
        Create a real-time listener for carrier's shipments
        This would be used in a WebSocket implementation
        """
        try:
            self._initialize_firebase()
            query = self.db.collection('shipment_tracking').where('carrier_id', '==', carrier_id)
            
            # Create listener
            def on_snapshot(docs, changes, read_time):
                for change in changes:
                    if change.type.name == 'ADDED' or change.type.name == 'MODIFIED':
                        callback(change.document.to_dict())
            
            query.on_snapshot(on_snapshot)
            logger.info(f"Created realtime listener for carrier {carrier_id}")
            
        except Exception as e:
            logger.error(f"Failed to create realtime listener for {carrier_id}: {str(e)}")

# Singleton instance
firebase_service = TFST_FirebaseService()