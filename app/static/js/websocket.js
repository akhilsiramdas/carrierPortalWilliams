// app/static/js/websocket.js
/**
 * TFST Carrier Portal - WebSocket Client
 */

class TFSTWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.connected = false;
        this.init();
    }
    
    init() {
        if (typeof io !== 'undefined') {
            this.connect();
            this.setupEventListeners();
        }
    }
    
    connect() {
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay
        });
        
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this.connected = false;
            this.updateConnectionStatus('disconnected');
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus('error');
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log('WebSocket reconnected after', attemptNumber, 'attempts');
            this.updateConnectionStatus('connected');
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection failed:', error);
        });
    }
    
    setupEventListeners() {
        // Listen for shipment updates
        this.socket.on('shipment_update', (data) => {
            this.handleShipmentUpdate(data);
        });
        
        this.socket.on('location_update', (data) => {
            this.handleLocationUpdate(data);
        });
        
        this.socket.on('emergency_alert', (data) => {
            this.handleEmergencyAlert(data);
        });
        
        this.socket.on('driver_status_change', (data) => {
            this.handleDriverStatusChange(data);
        });
        
        this.socket.on('mobile_update', (data) => {
            this.handleMobileUpdate(data);
        });
    }
    
    updateConnectionStatus(status) {
        const statusElement = $('#connectionStatus');
        if (statusElement.length) {
            switch(status) {
                case 'connected':
                    statusElement.html('<i class="fas fa-circle text-success"></i> Connected')
                               .removeClass('text-danger text-warning')
                               .addClass('text-success');
                    break;
                case 'disconnected':
                    statusElement.html('<i class="fas fa-circle text-warning"></i> Disconnected')
                               .removeClass('text-success text-danger')
                               .addClass('text-warning');
                    break;
                case 'error':
                    statusElement.html('<i class="fas fa-circle text-danger"></i> Connection Error')
                               .removeClass('text-success text-warning')
                               .addClass('text-danger');
                    break;
            }
        }
    }
    
    handleShipmentUpdate(data) {
        // Broadcast to all interested components
        $(document).trigger('shipment:update', [data]);
        
        // Update any visible shipment displays
        this.updateShipmentDisplay(data);
        
        // Show notification
        this.showNotification(`Shipment ${data.shipment_id} updated: ${data.current_status}`, 'info');
    }
    
    handleLocationUpdate(data) {
        // Broadcast to map components
        $(document).trigger('location:update', [data]);
        
        // Update location displays
        this.updateLocationDisplay(data);
    }
    
    handleEmergencyAlert(data) {
        // Show urgent notification
        this.showEmergencyAlert(data);
        
        // Broadcast to alert components
        $(document).trigger('emergency:alert', [data]);
        
        // Play alert sound if available
        this.playAlertSound();
    }
    
    handleDriverStatusChange(data) {
        // Update driver status displays
        $(document).trigger('driver:status', [data]);
        
        console.log('Driver status changed:', data);
    }
    
    handleMobileUpdate(data) {
        // Handle updates from mobile driver app
        $(document).trigger('mobile:update', [data]);
        
        this.showNotification(`Mobile update: ${data.shipment_id}`, 'info');
    }
    
    updateShipmentDisplay(data) {
        // Update shipment status in tables
        $(`.shipment-row[data-shipment-id="${data.shipment_id}"]`).each(function() {
            const row = $(this);
            const statusBadge = row.find('.status-badge');
            
            // Update status badge
            statusBadge.removeClass()
                       .addClass(`badge status-badge status-${data.current_status.toLowerCase().replace(' ', '-')}`)
                       .text(data.current_status);
            
            // Add highlight effect
            row.addClass('table-info');
            setTimeout(() => row.removeClass('table-info'), 2000);
        });
        
        // Update status in detail view if open
        if ($('#shipmentDetailModal').is(':visible')) {
            const currentShipmentId = $('#shipmentDetailModal').data('shipment-id');
            if (currentShipmentId === data.shipment_id) {
                $('#currentStatus').text(data.current_status);
                $('#lastUpdated').text('Just now');
            }
        }
    }
    
    updateLocationDisplay(data) {
        // Update location in any visible displays
        $(`.location-display[data-shipment-id="${data.shipment_id}"]`).each(function() {
            $(this).html(`
                <i class="fas fa-map-marker-alt"></i>
                ${data.location.lat.toFixed(4)}, ${data.location.lng.toFixed(4)}
                <small class="text-muted">Just updated</small>
            `);
        });
    }
    
    showNotification(message, type = 'info') {
        // Create notification
        const notification = $(`
            <div class="toast align-items-center text-white bg-${type} border-0 position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999;" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-info-circle me-2"></i>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        $('body').append(notification);
        
        // Show toast
        const toast = new bootstrap.Toast(notification[0]);
        toast.show();
        
        // Remove after hidden
        notification.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }
    
    showEmergencyAlert(data) {
        // Create urgent alert modal
        const alertModal = $(`
            <div class="modal fade" id="emergencyAlertModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog">
                    <div class="modal-content border-danger">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle me-2"></i>EMERGENCY ALERT
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-danger">
                                <h6>Shipment: ${data.shipment_id}</h6>
                                <p class="mb-0">${data.alert_message}</p>
                                ${data.location ? `
                                    <hr>
                                    <small>Location: ${data.location.lat}, ${data.location.lng}</small>
                                ` : ''}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                                Acknowledge
                            </button>
                            <a href="/shipments/${data.shipment_id}" class="btn btn-outline-primary">
                                View Shipment
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(alertModal);
        
        const modal = new bootstrap.Modal(alertModal[0]);
        modal.show();
        
        // Remove modal when hidden
        alertModal.on('hidden.bs.modal', function() {
            $(this).remove();
        });
    }
    
    playAlertSound() {
        // Play alert sound if audio is supported
        try {
            const audio = new Audio('/static/audio/alert.mp3');
            audio.play().catch(() => {
                // Ignore if audio play fails
                console.log('Audio play failed - user interaction required');
            });
        } catch (e) {
            console.log('Audio not supported');
        }
    }
    
    // Public methods for other components to use
    subscribeToShipment(shipmentId) {
        if (this.connected) {
            this.socket.emit('subscribe_shipment', { shipment_id: shipmentId });
        }
    }
    
    unsubscribeFromShipment(shipmentId) {
        if (this.connected) {
            this.socket.emit('unsubscribe_shipment', { shipment_id: shipmentId });
        }
    }
    
    requestShipmentStatus(shipmentId) {
        if (this.connected) {
            this.socket.emit('request_shipment_status', { shipment_id: shipmentId });
        }
    }
    
    ping() {
        if (this.connected) {
            this.socket.emit('ping');
        }
    }
}

// Initialize WebSocket when document is ready
$(document).ready(function() {
    window.TFST_WebSocket = new TFSTWebSocket();
    
    // Set up periodic ping to keep connection alive
    setInterval(() => {
        if (window.TFST_WebSocket) {
            window.TFST_WebSocket.ping();
        }
    }, 30000); // Ping every 30 seconds
});