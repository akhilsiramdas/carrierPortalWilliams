// app/static/js/shipments.js
/**
 * TFST Carrier Portal - Shipments JavaScript
 */

class TFSTShipments {
    constructor() {
        this.selectedShipments = new Set();
        this.map = null;
        this.markers = {};
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupDataTable();
        this.connectWebSocket();
    }
    
    setupEventListeners() {
        // Checkbox handlers
        $('#selectAll').change((e) => this.handleSelectAll(e));
        $('.shipment-checkbox').change((e) => this.handleShipmentSelect(e));
        
        // Bulk actions
        $('#bulkStatusUpdate').click(() => this.showBulkUpdateModal());
        $('#bulkExport').click(() => this.exportSelected());
        
        // Status update modal
        $('#statusUpdateForm').submit((e) => this.handleStatusUpdate(e));
        
        // Search and filters
        $('#shipmentSearch').on('input', debounce(() => this.handleSearch(), 300));
        $('.filter-select').change(() => this.applyFilters());
        
        // Refresh button
        $('#refreshShipments').click(() => this.refreshData());
    }
    
    setupDataTable() {
        if ($.fn.DataTable) {
            $('#shipmentsTable').DataTable({
                responsive: true,
                pageLength: 25,
                order: [[1, 'desc']], // Order by shipment ID
                columnDefs: [
                    { orderable: false, targets: [0, -1] } // Disable sorting on checkbox and actions
                ]
            });
        }
    }
    
    handleSelectAll(e) {
        const checked = e.target.checked;
        $('.shipment-checkbox').prop('checked', checked);
        
        if (checked) {
            $('.shipment-checkbox').each((i, el) => {
                this.selectedShipments.add(el.value);
            });
        } else {
            this.selectedShipments.clear();
        }
        
        this.updateBulkActions();
    }
    
    handleShipmentSelect(e) {
        const shipmentId = e.target.value;
        const checked = e.target.checked;
        
        if (checked) {
            this.selectedShipments.add(shipmentId);
        } else {
            this.selectedShipments.delete(shipmentId);
        }
        
        // Update select all checkbox
        const totalCheckboxes = $('.shipment-checkbox').length;
        const checkedBoxes = $('.shipment-checkbox:checked').length;
        
        $('#selectAll').prop('checked', totalCheckboxes === checkedBoxes);
        $('#selectAll').prop('indeterminate', checkedBoxes > 0 && checkedBoxes < totalCheckboxes);
        
        this.updateBulkActions();
    }
    
    updateBulkActions() {
        const count = this.selectedShipments.size;
        $('#selectedCount').text(count);
        
        if (count > 0) {
            $('#bulkActionsPanel').show();
        } else {
            $('#bulkActionsPanel').hide();
        }
    }
    
    handleStatusUpdate(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const shipmentId = formData.get('shipment_id');
        
        const updateData = {
            status: formData.get('status'),
            notes: formData.get('notes')
        };
        
        const lat = parseFloat(formData.get('latitude'));
        const lng = parseFloat(formData.get('longitude'));
        const driverName = formData.get('driver_name');
        
        if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
            updateData.location = { lat, lng };
        }
        
        if (driverName) {
            updateData.driver_info = { name: driverName };
        }
        
        this.updateShipmentStatus(shipmentId, updateData);
    }
    
    updateShipmentStatus(shipmentId, data) {
        $.ajax({
            url: `/shipments/${shipmentId}/update-status`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: (response) => {
                if (response.success) {
                    this.showNotification('Status updated successfully', 'success');
                    $('#statusUpdateModal').modal('hide');
                    this.refreshData();
                } else {
                    this.showNotification('Failed to update status: ' + response.error, 'error');
                }
            },
            error: (xhr) => {
                const response = xhr.responseJSON || {};
                this.showNotification('Update failed: ' + (response.error || 'Server error'), 'error');
            }
        });
    }
    
    connectWebSocket() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('shipment_update', (data) => {
                this.handleRealtimeUpdate(data);
            });
            
            this.socket.on('location_update', (data) => {
                this.updateMapMarker(data.shipment_id, data.location);
            });
        }
    }
    
    handleRealtimeUpdate(data) {
        // Update shipment row in table
        const row = $(`.shipment-row[data-shipment-id="${data.shipment_id}"]`);
        if (row.length) {
            const statusBadge = row.find('.status-badge');
            statusBadge.removeClass().addClass(`badge status-badge status-${data.current_status.toLowerCase().replace(' ', '-')}`);
            statusBadge.text(data.current_status);
            
            // Add visual indicator for update
            row.addClass('table-warning');
            setTimeout(() => row.removeClass('table-warning'), 3000);
        }
        
        this.showNotification(`${data.shipment_id} updated: ${data.current_status}`, 'info');
    }
    
    showNotification(message, type = 'info') {
        // Similar to dashboard notification system
        const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
        const alert = `
            <div class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('body').append(alert);
        setTimeout(() => $('.alert').last().alert('close'), 5000);
    }
    
    refreshData() {
        location.reload(); // Simple refresh - could be enhanced with AJAX
    }
}

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize when document is ready
$(document).ready(function() {
    window.TFST_Shipments = new TFSTShipments();
});