"""
TFST Carrier Portal - WebSocket Real-time Integration
Integrates with existing mobile app Firebase data for real-time updates
"""
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from flask import session
import logging
import json
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", logger=True, engineio_logger=True)

class FirebaseListener:
    """
    Listens to Firebase changes from mobile driver app and broadcasts to web portal
    """
    
    def __init__(self, firebase_service, socketio_instance):
        self.firebase_service = firebase_service
        self.socketio = socketio_instance
        self.active_listeners = {}
    
    def start_carrier_listener(self, carrier_id: str):
        """Start listening to Firebase changes for a specific carrier"""
        if carrier_id in self.active_listeners:
            return  # Already listening
        
        try:
            # Create Firebase real-time listener
            from firebase_admin import firestore
            
            db = firestore.client()
            
            # Listen to shipment_tracking changes for this carrier
            query = db.collection('shipment_tracking').where('carrier_id', '==', carrier_id)
            
            def on_snapshot(docs, changes, read_time):
                """Handle Firebase document changes"""
                for change in changes:
                    if change.type.name in ['ADDED', 'MODIFIED']:
                        doc_data = change.document.to_dict()
                        doc_data['document_id'] = change.document.id
                        
                        # Broadcast to carrier room
                        self.broadcast_shipment_update(carrier_id, doc_data)
            
            # Start the listener
            listener = query.on_snapshot(on_snapshot)
            self.active_listeners[carrier_id] = listener
            
            logger.info(f"Started Firebase listener for carrier {carrier_id}")
            
        except Exception as e:
            logger.error(f"Failed to start Firebase listener for carrier {carrier_id}: {str(e)}")
    
    def stop_carrier_listener(self, carrier_id: str):
        """Stop listening to Firebase changes for a carrier"""
        if carrier_id in self.active_listeners:
            listener = self.active_listeners[carrier_id]
            listener.unsubscribe()
            del self.active_listeners[carrier_id]
            logger.info(f"Stopped Firebase listener for carrier {carrier_id}")
    
    def broadcast_shipment_update(self, carrier_id: str, shipment_data: Dict[str, Any]):
        """Broadcast shipment update to all connected carrier users"""
        try:
            # Format data for web portal
            update_data = {
                'shipment_id': shipment_data.get('shipment_id'),
                'current_status': shipment_data.get('current_status'),
                'location': shipment_data.get('location'),
                'driver_info': shipment_data.get('driver_info'),
                'last_updated': shipment_data.get('last_updated'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'mobile_app'
            }
            
            # Emit to carrier room
            self.socketio.emit('shipment_update', update_data, room=f"carrier_{carrier_id}")
            
            # Emit specific location update for map
            if shipment_data.get('location'):
                location_data = {
                    'shipment_id': shipment_data.get('shipment_id'),
                    'location': shipment_data.get('location'),
                    'timestamp': update_data['timestamp']
                }
                self.socketio.emit('location_update', location_data, room=f"carrier_{carrier_id}")
            
            logger.info(f"Broadcasted update for shipment {shipment_data.get('shipment_id')} to carrier {carrier_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast shipment update: {str(e)}")

# Global Firebase listener instance
firebase_listener = None

def init_websocket(app, firebase_service):
    """Initialize WebSocket with app and Firebase service"""
    global firebase_listener
    
    socketio.init_app(app, async_mode='threading', cors_allowed_origins="*")
    firebase_listener = FirebaseListener(firebase_service, socketio)
    
    return socketio

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        if current_user.is_authenticated:
            carrier_id = session.get('carrier_id')
            
            if carrier_id:
                # Join carrier-specific room
                join_room(f"carrier_{carrier_id}")
                
                # Start Firebase listener for this carrier if not already active
                if firebase_listener:
                    firebase_listener.start_carrier_listener(carrier_id)
                
                emit('connected', {
                    'status': 'success',
                    'user_id': current_user.id,
                    'carrier_id': carrier_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                logger.info(f"User {current_user.id} (Carrier: {carrier_id}) connected to WebSocket")
            else:
                emit('connected', {'status': 'error', 'message': 'No carrier ID found'})
        else:
            emit('connected', {'status': 'error', 'message': 'Not authenticated'})
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        emit('connected', {'status': 'error', 'message': 'Connection failed'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        if current_user.is_authenticated:
            carrier_id = session.get('carrier_id')
            
            if carrier_id:
                leave_room(f"carrier_{carrier_id}")
                logger.info(f"User {current_user.id} (Carrier: {carrier_id}) disconnected from WebSocket")
            
            # Note: We don't stop the Firebase listener here as other users from the same carrier might be connected
            
    except Exception as e:
        logger.error(f"WebSocket disconnection error: {str(e)}")

@socketio.on('subscribe_shipment')
def handle_subscribe_shipment(data):
    """Subscribe to specific shipment updates"""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Not authenticated'})
            return
        
        shipment_id = data.get('shipment_id')
        carrier_id = session.get('carrier_id')
        
        if not shipment_id:
            emit('error', {'message': 'Shipment ID required'})
            return
        
        # Join shipment-specific room
        join_room(f"shipment_{shipment_id}")
        
        emit('subscribed', {
            'shipment_id': shipment_id,
            'status': 'success'
        })
        
        logger.info(f"User {current_user.id} subscribed to shipment {shipment_id}")
        
    except Exception as e:
        logger.error(f"Shipment subscription error: {str(e)}")
        emit('error', {'message': 'Subscription failed'})

@socketio.on('unsubscribe_shipment')
def handle_unsubscribe_shipment(data):
    """Unsubscribe from specific shipment updates"""
    try:
        shipment_id = data.get('shipment_id')
        
        if shipment_id:
            leave_room(f"shipment_{shipment_id}")
            emit('unsubscribed', {'shipment_id': shipment_id})
            logger.info(f"User {current_user.id if current_user.is_authenticated else 'Anonymous'} unsubscribed from shipment {shipment_id}")
        
    except Exception as e:
        logger.error(f"Shipment unsubscription error: {str(e)}")

@socketio.on('ping')
def handle_ping():
    """Handle ping for connection health check"""
    emit('pong', {'timestamp': datetime.now(timezone.utc).isoformat()})

@socketio.on('request_shipment_status')
def handle_request_status(data):
    """Handle request for current shipment status"""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Not authenticated'})
            return
        
        shipment_id = data.get('shipment_id')
        carrier_id = session.get('carrier_id')
        
        if not shipment_id:
            emit('error', {'message': 'Shipment ID required'})
            return
        
        # Get current status from Firebase
        if firebase_listener and firebase_listener.firebase_service:
            tracking_data = firebase_listener.firebase_service.get_shipment_tracking(shipment_id)
            
            if tracking_data:
                emit('shipment_status', {
                    'shipment_id': shipment_id,
                    'data': tracking_data,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            else:
                emit('shipment_status', {
                    'shipment_id': shipment_id,
                    'data': None,
                    'message': 'No tracking data found'
                })
        else:
            emit('error', {'message': 'Firebase service not available'})
            
    except Exception as e:
        logger.error(f"Status request error: {str(e)}")
        emit('error', {'message': 'Status request failed'})

# Utility functions for manual broadcasting (used by routes)
def broadcast_to_carrier(carrier_id: str, event: str, data: Dict[str, Any]):
    """Broadcast event to all users of a specific carrier"""
    socketio.emit(event, data, room=f"carrier_{carrier_id}")

def broadcast_to_shipment(shipment_id: str, event: str, data: Dict[str, Any]):
    """Broadcast event to all users subscribed to a specific shipment"""
    socketio.emit(event, data, room=f"shipment_{shipment_id}")

def broadcast_status_update(carrier_id: str, shipment_id: str, status_data: Dict[str, Any]):
    """Broadcast status update to carrier and shipment rooms"""
    update_data = {
        'shipment_id': shipment_id,
        'status_data': status_data,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': 'web_portal'
    }
    
    # Broadcast to carrier room
    socketio.emit('shipment_update', update_data, room=f"carrier_{carrier_id}")
    
    # Broadcast to shipment-specific room
    socketio.emit('shipment_update', update_data, room=f"shipment_{shipment_id}")

def get_connected_users_count(carrier_id: str = None) -> int:
    """Get count of connected users for a carrier or total"""
    try:
        if carrier_id:
            room_name = f"carrier_{carrier_id}"
            # This is a simplified count - in production you'd need to track this properly
            return len(socketio.server.manager.get_participants(socketio.server.eio.namespace, room_name))
        else:
            return len(socketio.server.manager.get_participants(socketio.server.eio.namespace, '/'))
    except:
        return 0

# Integration with existing mobile app Firebase data
class MobileAppIntegration:
    """
    Integration layer with existing mobile driver app Firebase data
    """
    
    @staticmethod
    def sync_mobile_data_to_portal(shipment_updates: list):
        """
        Sync mobile app updates to web portal users
        This would be called when mobile app writes to Firebase
        """
        for update in shipment_updates:
            carrier_id = update.get('carrier_id')
            shipment_id = update.get('shipment_id')
            
            if carrier_id and shipment_id:
                # Format for web portal
                portal_update = {
                    'shipment_id': shipment_id,
                    'current_status': update.get('status'),
                    'location': update.get('location'),
                    'driver_info': update.get('driver_info'),
                    'timestamp': update.get('timestamp'),
                    'source': 'mobile_app'
                }
                
                broadcast_to_carrier(carrier_id, 'mobile_update', portal_update)
    
    @staticmethod
    def handle_driver_status_change(driver_data: dict):
        """
        Handle when driver comes online/offline in mobile app
        """
        carrier_id = driver_data.get('carrier_id')
        driver_info = {
            'driver_name': driver_data.get('name'),
            'truck_number': driver_data.get('truck_number'),
            'status': driver_data.get('status'),  # online, offline, driving
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        broadcast_to_carrier(carrier_id, 'driver_status_change', driver_info)
    
    @staticmethod
    def handle_emergency_alert(alert_data: dict):
        """
        Handle emergency alerts from mobile app
        """
        carrier_id = alert_data.get('carrier_id')
        shipment_id = alert_data.get('shipment_id')
        
        emergency_data = {
            'type': 'emergency',
            'severity': 'high',
            'shipment_id': shipment_id,
            'alert_message': alert_data.get('message'),
            'location': alert_data.get('location'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'requires_immediate_attention': True
        }
        
        # Broadcast to carrier and shipment rooms
        broadcast_to_carrier(carrier_id, 'emergency_alert', emergency_data)
        if shipment_id:
            broadcast_to_shipment(shipment_id, 'emergency_alert', emergency_data)

# Export main components
__all__ = [
    'socketio',
    'init_websocket', 
    'broadcast_to_carrier',
    'broadcast_to_shipment',
    'broadcast_status_update',
    'get_connected_users_count',
    'MobileAppIntegration'
]