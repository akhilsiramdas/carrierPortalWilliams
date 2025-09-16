"""
TFST Carrier Portal - Dashboard Routes
Main carrier dashboard with shipment overview and KPIs
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from flask_login import login_required, current_user
from app.services.salesforce_service import salesforce_service
from app.utils.decorators import salesforce_token_required
from app.services.firebase_service import firebase_service
from datetime import datetime, timedelta
import logging

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)

@dashboard_bp.route('/')
@login_required
@salesforce_token_required
def index():
    """Main carrier dashboard"""
    try:
        print(f"DEBUG: Dashboard accessed, current_user.is_authenticated: {current_user.is_authenticated}")
        print(f"DEBUG: current_user: {current_user}")
        print(f"DEBUG: Session keys in dashboard: {list(session.keys())}")
        
        carrier_id = session.get('carrier_id')
        print(f"DEBUG: carrier_id from session: {carrier_id}")
        
        if not carrier_id:
            print("DEBUG: No carrier_id in session, redirecting to login")
            return redirect(url_for('auth.login'))
        
        # Get carrier's active shipments from Salesforce
        shipments = salesforce_service.get_carrier_shipments(carrier_id)
        
        # Get real-time tracking data from Firebase
        realtime_data = firebase_service.get_carrier_shipments_realtime(carrier_id)
        
        # Merge Salesforce and Firebase data
        merged_shipments = merge_shipment_data(shipments, realtime_data)
        
        # Calculate KPIs
        kpis = calculate_dashboard_kpis(merged_shipments)
        
        # Get recent status updates (last 24 hours)
        recent_updates = get_recent_updates(carrier_id)
        
        return render_template(
            'dashboard/index.html',
            shipments=merged_shipments[:10],  # Show top 10 on dashboard
            kpis=kpis,
            recent_updates=recent_updates,
            user=current_user
        )
        
    except Exception as e:
        logger.error(f"Dashboard error for carrier {carrier_id}: {str(e)}")
        return render_template('dashboard/index.html', 
                             error="Unable to load dashboard data", 
                             shipments=[], 
                             kpis={
                                 'total_shipments': 0,
                                 'in_transit': 0,
                                 'delivered_today': 0,
                                 'delayed': 0,
                                 'on_time_percentage': 0,
                                 'status_breakdown': {}
                             }, 
                             recent_updates=[],
                             user=current_user)
    
@dashboard_bp.route('/api/kpis')
@login_required
@salesforce_token_required
def get_kpis():
    """API endpoint for KPI data"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Get shipments
        shipments = salesforce_service.get_carrier_shipments(carrier_id, limit=200)
        realtime_data = firebase_service.get_carrier_shipments_realtime(carrier_id)
        
        # Merge and calculate KPIs
        merged_shipments = merge_shipment_data(shipments, realtime_data)
        kpis = calculate_dashboard_kpis(merged_shipments)
        
        return jsonify({
            'success': True,
            'data': kpis
        })
        
    except Exception as e:
        logger.error(f"KPI API error for carrier {carrier_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load KPI data'
        }), 500

@dashboard_bp.route('/api/shipments/summary')
@login_required
@salesforce_token_required
def get_shipments_summary():
    """API endpoint for shipments summary"""
    try:
        carrier_id = session.get('carrier_id')
        limit = request.args.get('limit', 50, type=int)
        status_filter = request.args.get('status')
        
        # Get shipments
        shipments = salesforce_service.get_carrier_shipments(carrier_id, limit=limit)
        realtime_data = firebase_service.get_carrier_shipments_realtime(carrier_id)
        
        # Merge data
        merged_shipments = merge_shipment_data(shipments, realtime_data)
        
        # Apply status filter if provided
        if status_filter:
            merged_shipments = [s for s in merged_shipments if s.get('status') == status_filter]
        
        # Format for API response
        summary_data = []
        for shipment in merged_shipments:
            summary_data.append({
                'id': shipment.get('Id'),
                'name': shipment.get('Name'),
                'status': shipment.get('status'),
                'project': shipment.get('TFST_Project_Reference__c'),
                'delivery_date': shipment.get('Required_Delivery_Date__c'),
                'weight': shipment.get('TFST_Total_Weight__c'),
                'location': shipment.get('location'),
                'last_updated': shipment.get('last_updated')
            })
        
        return jsonify({
            'success': True,
            'data': summary_data,
            'total': len(summary_data)
        })
        
    except Exception as e:
        logger.error(f"Shipments summary API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load shipments data'
        }), 500

@dashboard_bp.route('/api/performance')
@login_required
@salesforce_token_required
def get_performance_metrics():
    """API endpoint for carrier performance metrics"""
    try:
        carrier_id = session.get('carrier_id')
        days = request.args.get('days', 30, type=int)
        
        # Get performance data from Salesforce
        performance_data = salesforce_service.get_carrier_performance_metrics(carrier_id, days)
        
        # Add additional metrics calculation here
        performance_data['on_time_percentage'] = calculate_on_time_percentage(carrier_id, days)
        performance_data['average_delay_hours'] = calculate_average_delay(carrier_id, days)
        
        return jsonify({
            'success': True,
            'data': performance_data
        })
        
    except Exception as e:
        logger.error(f"Performance API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load performance data'
        }), 500

@dashboard_bp.route('/alerts')
@login_required
@salesforce_token_required
def alerts():
    """Display carrier alerts and notifications"""
    try:
        carrier_id = session.get('carrier_id')
        
        # Get urgent shipments and alerts
        urgent_shipments = get_urgent_shipments(carrier_id)
        delayed_shipments = get_delayed_shipments(carrier_id)
        delivery_alerts = get_delivery_alerts(carrier_id)
        
        return render_template(
            'dashboard/alerts.html',
            urgent_shipments=urgent_shipments,
            delayed_shipments=delayed_shipments,
            delivery_alerts=delivery_alerts
        )
        
    except Exception as e:
        logger.error(f"Alerts page error: {str(e)}")
        return render_template('dashboard/alerts.html', error="Unable to load alerts")

@dashboard_bp.route('/analytics')
@login_required
@salesforce_token_required
def analytics():
    """Carrier analytics and performance dashboard"""
    if not current_user.can_view_analytics:
        return render_template('errors/403.html', 
                             message="You don't have permission to view analytics")
    
    try:
        carrier_id = session.get('carrier_id')
        
        # Get analytics data for different time periods
        performance_30d = salesforce_service.get_carrier_performance_metrics(carrier_id, 30)
        performance_90d = salesforce_service.get_carrier_performance_metrics(carrier_id, 90)
        
        # Calculate trends
        analytics_data = {
            'performance_30d': performance_30d,
            'performance_90d': performance_90d,
            'delivery_trend': calculate_delivery_trend(carrier_id),
            'route_efficiency': calculate_route_efficiency(carrier_id),
            'customer_satisfaction': get_customer_satisfaction_score(carrier_id)
        }
        
        return render_template('dashboard/analytics.html', analytics=analytics_data)
        
    except Exception as e:
        logger.error(f"Analytics page error: {str(e)}")
        return render_template('dashboard/analytics.html', error="Unable to load analytics")

# Helper Functions

def merge_shipment_data(salesforce_shipments, firebase_data):
    """Merge Salesforce and Firebase shipment data"""
    try:
        # Create lookup dictionary for Firebase data
        firebase_lookup = {}
        for fb_data in firebase_data:
            shipment_id = fb_data.get('shipment_id')
            if shipment_id:
                firebase_lookup[shipment_id] = fb_data
        
        merged_data = []
        for sf_shipment in salesforce_shipments:
            # Start with Salesforce data
            merged_shipment = dict(sf_shipment)
            
            # Try to find Firebase data by ID or Name
            shipment_id = sf_shipment.get('Id')
            shipment_name = sf_shipment.get('Name')
            
            fb_data = firebase_lookup.get(shipment_id) or firebase_lookup.get(shipment_name)
            
            if fb_data:
                # Merge Firebase real-time data
                merged_shipment.update({
                    'status': fb_data.get('current_status', sf_shipment.get('TFST_Status__c')),
                    'location': fb_data.get('location'),
                    'last_updated': fb_data.get('last_updated'),
                    'driver_info': fb_data.get('driver_info'),
                    'realtime_available': True
                })
            else:
                # Use Salesforce data only
                merged_shipment.update({
                    'status': sf_shipment.get('TFST_Status__c'),
                    'realtime_available': False
                })
            
            merged_data.append(merged_shipment)
        
        return merged_data
        
    except Exception as e:
        logger.error(f"Error merging shipment data: {str(e)}")
        return salesforce_shipments

def calculate_dashboard_kpis(shipments):
    """Calculate KPIs for dashboard"""
    try:
        total_shipments = len(shipments)
        
        if total_shipments == 0:
            return {
                'total_shipments': 0,
                'in_transit': 0,
                'delivered_today': 0,
                'delayed': 0,
                'on_time_percentage': 0,
                'status_breakdown': {}  # Empty dict, not None or undefined
            }
        
        # Count by status
        status_counts = {}
        delayed_count = 0
        delivered_today = 0
        
        today = datetime.now().date()
        
        for shipment in shipments:
            status = shipment.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Check for delays
            delivery_date = shipment.get('Required_Delivery_Date__c')
            if delivery_date and status not in ['Delivered', 'Cancelled']:
                try:
                    delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
                    if delivery_date < today:
                        delayed_count += 1
                except:
                    pass
            
            # Count deliveries today
            if status == 'Delivered':
                last_updated = shipment.get('last_updated')
                if last_updated:
                    try:
                        update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00')).date()
                        if update_date == today:
                            delivered_today += 1
                    except:
                        pass
        
        # Calculate on-time percentage (simplified)
        delivered_total = status_counts.get('Delivered', 0)
        on_time_percentage = ((delivered_total - delayed_count) / delivered_total * 100) if delivered_total > 0 else 0
        
        return {
            'total_shipments': total_shipments,
            'in_transit': status_counts.get('In Transit', 0),
            'delivered_today': delivered_today,
            'delayed': delayed_count,
            'on_time_percentage': round(on_time_percentage, 1),
            'status_breakdown': status_counts  # This should be a dict, not None
        }
        
    except Exception as e:
        logger.error(f"Error calculating KPIs: {str(e)}")
        return {
            'total_shipments': 0,
            'in_transit': 0,
            'delivered_today': 0,
            'delayed': 0,
            'on_time_percentage': 0,
            'status_breakdown': {}  # Empty dict in case of error
        }
def get_recent_updates(carrier_id, hours=24):
    """Get recent shipment updates for the carrier"""
    try:
        # This would get recent updates from Firebase
        # For now, return empty list - implement based on Firebase schema
        return []
        
    except Exception as e:
        logger.error(f"Error getting recent updates: {str(e)}")
        return []

def get_urgent_shipments(carrier_id):
    """Get urgent/priority shipments"""
    try:
        shipments = salesforce_service.get_carrier_shipments(carrier_id)
        
        urgent = []
        for shipment in shipments:
            # Check for urgency criteria
            if (shipment.get('TFST_Service_Level__c') == 'Urgent' or 
                shipment.get('Critical_Path') == True):
                urgent.append(shipment)
        
        return urgent
        
    except Exception as e:
        logger.error(f"Error getting urgent shipments: {str(e)}")
        return []

def get_delayed_shipments(carrier_id):
    """Get delayed shipments"""
    try:
        shipments = salesforce_service.get_carrier_shipments(carrier_id)
        today = datetime.now().date()
        
        delayed = []
        for shipment in shipments:
            delivery_date = shipment.get('Required_Delivery_Date__c')
            status = shipment.get('TFST_Status__c')
            
            if delivery_date and status not in ['Delivered', 'Cancelled']:
                try:
                    delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
                    if delivery_date < today:
                        delayed.append(shipment)
                except:
                    pass
        
        return delayed
        
    except Exception as e:
        logger.error(f"Error getting delayed shipments: {str(e)}")
        return []

def get_delivery_alerts(carrier_id):
    """Get upcoming delivery alerts"""
    try:
        # Get shipments due in next 2 days
        shipments = salesforce_service.get_carrier_shipments(carrier_id)
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        day_after = (datetime.now() + timedelta(days=2)).date()
        
        alerts = []
        for shipment in shipments:
            delivery_date = shipment.get('Required_Delivery_Date__c')
            if delivery_date:
                try:
                    delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
                    if delivery_date in [tomorrow, day_after]:
                        alerts.append({
                            'shipment': shipment,
                            'delivery_date': delivery_date,
                            'days_until': (delivery_date - datetime.now().date()).days
                        })
                except:
                    pass
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting delivery alerts: {str(e)}")
        return []

def calculate_on_time_percentage(carrier_id, days):
    """Calculate on-time delivery percentage"""
    try:
        # This would require more complex Salesforce queries
        # For now, return a placeholder
        return 85.5
    except Exception as e:
        logger.error(f"Error calculating on-time percentage: {str(e)}")
        return 0

def calculate_average_delay(carrier_id, days):
    """Calculate average delay in hours"""
    try:
        # Placeholder implementation
        return 2.3
    except Exception as e:
        logger.error(f"Error calculating average delay: {str(e)}")
        return 0

def calculate_delivery_trend(carrier_id):
    """Calculate delivery trend data"""
    try:
        # Placeholder for trend calculation
        return {
            'trend': 'improving',
            'percentage_change': 5.2
        }
    except Exception as e:
        logger.error(f"Error calculating delivery trend: {str(e)}")
        return {}

def calculate_route_efficiency(carrier_id):
    """Calculate route efficiency metrics"""
    try:
        # Placeholder implementation
        return {
            'efficiency_score': 88.5,
            'average_route_time': 4.2
        }
    except Exception as e:
        logger.error(f"Error calculating route efficiency: {str(e)}")
        return {}

def get_customer_satisfaction_score(carrier_id):
    """Get customer satisfaction score"""
    try:
        # Placeholder implementation
        return {
            'score': 4.2,
            'max_score': 5.0,
            'feedback_count': 47
        }
    except Exception as e:
        logger.error(f"Error getting customer satisfaction: {str(e)}")
        return {}