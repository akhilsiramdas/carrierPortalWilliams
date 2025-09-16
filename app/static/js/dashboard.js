// app/static/js/dashboard.js
/**
 * TFST Carrier Portal - Dashboard JavaScript
 */

class TFSTDashboard {
    constructor() {
        this.refreshInterval = 30000; // 30 seconds
        this.charts = {};
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupAutoRefresh();
        this.initializeCharts();
        this.connectWebSocket();
    }
    
    setupEventListeners() {
        // Refresh button
        $('#refreshDashboard').click(() => this.refreshData());
        
        // KPI card clicks
        $('.kpi-card').click(function() {
            const metric = $(this).data('metric');
            window.location.href = `/shipments?status=${metric}`;
        });
        
        // Quick action buttons
        $('.quick-action').click(function(e) {
            e.preventDefault();
            const action = $(this).data('action');
            window.TFST_Dashboard.handleQuickAction(action);
        });
    }
    
    setupAutoRefresh() {
        setInterval(() => {
            this.refreshKPIs();
        }, this.refreshInterval);
    }
    
    refreshData() {
        this.showLoading();
        this.refreshKPIs();
        this.refreshRecentShipments();
    }
    
    refreshKPIs() {
        $.get('/dashboard/api/kpis')
            .done((data) => {
                if (data.success) {
                    this.updateKPICards(data.data);
                    this.updateCharts(data.data);
                }
            })
            .fail(() => {
                console.log('Failed to refresh KPIs');
            });
    }
    
    refreshRecentShipments() {
        $.get('/api/v1/shipments?limit=10')
            .done((data) => {
                if (data.success) {
                    this.updateRecentShipments(data.data.shipments);
                }
            })
            .fail(() => {
                console.log('Failed to refresh shipments');
            });
    }
    
    updateKPICards(kpis) {
        $('#total-shipments').text(kpis.total_shipments || 0);
        $('#in-transit').text(kpis.in_transit || 0);
        $('#delivered-today').text(kpis.delivered_today || 0);
        $('#on-time-percentage').text((kpis.on_time_percentage || 0) + '%');
        
        // Add trend indicators
        this.addTrendIndicators(kpis);
    }
    
    addTrendIndicators(kpis) {
        // Add trend arrows and colors based on data
        const trends = kpis.trends || {};
        
        Object.keys(trends).forEach(metric => {
            const trend = trends[metric];
            const element = $(`#${metric}`).parent();
            
            let icon = 'fas fa-minus';
            let color = 'text-muted';
            
            if (trend > 0) {
                icon = 'fas fa-arrow-up';
                color = 'text-success';
            } else if (trend < 0) {
                icon = 'fas fa-arrow-down';
                color = 'text-danger';
            }
            
            element.find('.trend-indicator').remove();
            element.append(`<small class="trend-indicator ${color}"><i class="${icon}"></i> ${Math.abs(trend)}%</small>`);
        });
    }
    
    initializeCharts() {
        // Initialize Chart.js charts
        this.initStatusChart();
        this.initPerformanceChart();
    }
    
    initStatusChart() {
        const ctx = document.getElementById('statusChart');
        if (!ctx) return;
        
        this.charts.status = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#3b82f6', '#10b981', '#ef4444', '#f59e0b',
                        '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    initPerformanceChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;
        
        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'On-Time Delivery %',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
    
    updateCharts(data) {
        // Update status chart
        if (this.charts.status && data.status_breakdown) {
            const labels = Object.keys(data.status_breakdown);
            const values = Object.values(data.status_breakdown);
            
            this.charts.status.data.labels = labels;
            this.charts.status.data.datasets[0].data = values;
            this.charts.status.update();
        }
        
        // Update performance chart
        if (this.charts.performance && data.performance_trend) {
            this.charts.performance.data.labels = data.performance_trend.labels;
            this.charts.performance.data.datasets[0].data = data.performance_trend.values;
            this.charts.performance.update();
        }
    }
    
    connectWebSocket() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Dashboard WebSocket connected');
            });
            
            this.socket.on('shipment_update', (data) => {
                this.handleRealtimeUpdate(data);
            });
            
            this.socket.on('kpi_update', (data) => {
                this.updateKPICards(data);
            });
        }
    }
    
    handleRealtimeUpdate(data) {
        // Update dashboard with real-time data
        this.showNotification(`Shipment ${data.shipment_id} updated: ${data.current_status}`, 'info');
        
        // Refresh KPIs after a short delay
        setTimeout(() => this.refreshKPIs(), 2000);
    }
    
    showNotification(message, type = 'info') {
        const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
        const alert = `
            <div class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                <i class="fas fa-info-circle me-2"></i>${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('body').append(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            $('.alert').last().alert('close');
        }, 5000);
    }
    
    showLoading() {
        const loading = `
            <div class="loading-overlay position-fixed w-100 h-100" 
                 style="top: 0; left: 0; background: rgba(255,255,255,0.8); z-index: 9999;">
                <div class="d-flex justify-content-center align-items-center h-100">
                    <div class="text-center">
                        <div class="spinner-border text-primary mb-3" role="status"></div>
                        <p>Refreshing dashboard...</p>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(loading);
        
        setTimeout(() => {
            $('.loading-overlay').remove();
        }, 3000);
    }
    
    handleQuickAction(action) {
        switch(action) {
            case 'bulk_update':
                window.location.href = '/shipments/bulk-update';
                break;
            case 'map_view':
                window.location.href = '/shipments/map';
                break;
            case 'analytics':
                window.location.href = '/dashboard/analytics';
                break;
            default:
                console.log('Unknown action:', action);
        }
    }
}

// Initialize dashboard when document is ready
$(document).ready(function() {
    window.TFST_Dashboard = new TFSTDashboard();
});