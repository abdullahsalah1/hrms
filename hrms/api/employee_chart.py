# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime
import json

def create_employee_analytics_indexes():
    """
    Create database indexes for employee analytics performance
    """
    try:
        # Create composite index for status and commonly queried fields
        frappe.db.sql("""
            CREATE INDEX IF NOT EXISTS idx_employee_analytics_status 
            ON `tabEmployee` (status, department, designation, employment_type, gender, marital_status)
        """)
        
        # Create index for status only (most common filter)
        frappe.db.sql("""
            CREATE INDEX IF NOT EXISTS idx_employee_status 
            ON `tabEmployee` (status)
        """)
        
        frappe.logger().info("✅ Employee analytics indexes created successfully")
        return True
        
    except Exception as e:
        frappe.logger().error(f"❌ Error creating indexes: {str(e)}")
        return False

def get_cached_analytics():
    """
    Get cached analytics data if available and not expired
    """
    try:
        cache_key = "employee_analytics_cache"
        cached_data = frappe.cache().get_value(cache_key)
        
        if cached_data:
            cache_time = cached_data.get('timestamp')
            # Cache expires after 5 minutes
            if cache_time and (now_datetime() - cache_time).total_seconds() < 300:
                frappe.logger().debug("✅ Using cached analytics data")
                return cached_data.get('data')
        
        return None
        
    except Exception as e:
        frappe.logger().error(f"❌ Error getting cached analytics: {str(e)}")
        return None

def set_cached_analytics(data):
    """
    Cache analytics data for 5 minutes
    """
    try:
        cache_key = "employee_analytics_cache"
        cache_data = {
            'data': data,
            'timestamp': now_datetime()
        }
        frappe.cache().set_value(cache_key, cache_data, expires_in_sec=300)
        frappe.logger().debug("✅ Analytics data cached successfully")
        
    except Exception as e:
        frappe.logger().error(f"❌ Error caching analytics: {str(e)}")

@frappe.whitelist(allow_guest=True)
def get_employee_count_by_department():
    """
    Returns employee count grouped by department for active employees
    """
    try:
        frappe.logger().debug("Starting get_employee_count_by_department")
        
        # Query to get employee count by department
        result = frappe.db.sql("""
            SELECT 
                COALESCE(department, 'Not Set') as department,
                COUNT(*) as total
            FROM `tabEmployee`
            WHERE status = 'Active'
            GROUP BY department
            ORDER BY total DESC
        """, as_dict=1)

        frappe.logger().debug(f"Query result: {result}")

        # Prepare data for chart
        labels = [row.department for row in result]
        values = [row.total for row in result]

        response = {
            "labels": labels,
            "datasets": [{
                "name": "Employee Count",
                "values": values
            }]
        }

        frappe.logger().debug(f"Response: {response}")
        return response

    except Exception as e:
        frappe.logger().error(f"Error in get_employee_count_by_department: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch employee department data"))

@frappe.whitelist(allow_guest=True)
def get_employee_gender_joining_data():
    """
    Returns employee data grouped by gender and joining date with percentages
    """
    try:
        frappe.logger().debug("Starting get_employee_gender_joining_data")
        
        # Get total active employees count
        total_employees = frappe.db.sql("""
            SELECT COUNT(*) as total
            FROM `tabEmployee`
            WHERE status = 'Active'
        """, as_dict=1)[0].total

        # Query to get employee count by gender
        gender_data = frappe.db.sql("""
            SELECT 
                COALESCE(gender, 'Not Set') as gender,
                COUNT(*) as total
            FROM `tabEmployee`
            WHERE status = 'Active'
            GROUP BY gender
            ORDER BY total DESC
        """, as_dict=1)

        # Calculate percentages for gender
        gender_percentages = []
        for row in gender_data:
            percentage = (row.total / total_employees) * 100
            gender_percentages.append({
                'gender': row.gender,
                'percentage': round(percentage, 1)
            })

        # Query to get employee count by joining date (grouped by year)
        joining_data = frappe.db.sql("""
            SELECT 
                YEAR(date_of_joining) as year,
                COUNT(*) as total
            FROM `tabEmployee`
            WHERE status = 'Active'
                AND date_of_joining IS NOT NULL
            GROUP BY YEAR(date_of_joining)
            ORDER BY year ASC
        """, as_dict=1)

        # Calculate percentages for joining years
        joining_percentages = []
        for row in joining_data:
            percentage = (row.total / total_employees) * 100
            joining_percentages.append({
                'year': row.year,
                'percentage': round(percentage, 1)
            })

        # Prepare data for charts
        gender_response = {
            "labels": [f"{row['gender']} ({row['percentage']}%)" for row in gender_percentages],
            "datasets": [{
                "name": "Employee Percentage",
                "values": [row['percentage'] for row in gender_percentages]
            }]
        }

        joining_response = {
            "labels": [f"{row['year']} ({row['percentage']}%)" for row in joining_percentages],
            "datasets": [{
                "name": "Employee Percentage",
                "values": [row['percentage'] for row in joining_percentages]
            }]
        }

        return {
            "gender": gender_response,
            "joining": joining_response
        }

    except Exception as e:
        frappe.logger().error(f"Error in get_employee_gender_joining_data: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch employee gender and joining data"))

@frappe.whitelist(allow_guest=True)
def get_employee_comprehensive_stats():
    """
    Returns comprehensive employee statistics for various charts
    Optimized for performance with single query approach and caching
    """
    try:
        frappe.logger().debug("Starting get_employee_comprehensive_stats")
        
        # Check cache first
        cached_data = get_cached_analytics()
        if cached_data:
            frappe.logger().debug("✅ Returning cached analytics data")
            return cached_data
        
        # Create indexes if they don't exist (one-time setup)
        create_employee_analytics_indexes()
        
        # Single optimized query to get all statistics at once
        stats_data = frappe.db.sql("""
            SELECT 
                department,
                designation,
                employment_type,
                gender,
                marital_status,
                COUNT(*) as count
            FROM `tabEmployee`
            WHERE status = 'Active'
            GROUP BY department, designation, employment_type, gender, marital_status
        """, as_dict=1)

        frappe.logger().debug(f"Raw stats data count: {len(stats_data)}")

        if not stats_data:
            frappe.logger().debug("No active employees found")
            return {
                "department": {"labels": [], "datasets": [{"name": "Department Distribution", "values": []}]},
                "designation": {"labels": [], "datasets": [{"name": "Designation Distribution", "values": []}]},
                "employment_type": {"labels": [], "datasets": [{"name": "Employment Type Distribution", "values": []}]},
                "gender": {"labels": [], "datasets": [{"name": "Gender Distribution", "values": []}]},
                "marital_status": {"labels": [], "datasets": [{"name": "Marital Status Distribution", "values": []}]}
            }

        # Process data efficiently
        department_counts = {}
        designation_counts = {}
        employment_type_counts = {}
        gender_counts = {}
        marital_status_counts = {}
        total_employees = 0

        for row in stats_data:
            count = row['count']
            total_employees += count
            
            # Department
            dept = row['department'] or 'Not Set'
            department_counts[dept] = department_counts.get(dept, 0) + count
            
            # Designation
            desig = row['designation'] or 'Not Set'
            designation_counts[desig] = designation_counts.get(desig, 0) + count
            
            # Employment Type
            emp_type = row['employment_type'] or 'Not Set'
            employment_type_counts[emp_type] = employment_type_counts.get(emp_type, 0) + count
            
            # Gender
            gender = row['gender'] or 'Not Set'
            gender_counts[gender] = gender_counts.get(gender, 0) + count
            
            # Marital Status
            marital = row['marital_status'] or 'Not Set'
            marital_status_counts[marital] = marital_status_counts.get(marital, 0) + count

        # Sort by count and prepare response
        def prepare_chart_data(counts_dict, name):
            sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
            if name == "designation":
                sorted_items = sorted_items[:10]  # Limit to top 10 designations
            
            labels = [f"{item[0]} ({round((item[1] / total_employees) * 100, 1)}%)" for item in sorted_items]
            values = [round((item[1] / total_employees) * 100, 1) for item in sorted_items]
            
            return {
                "labels": labels,
                "datasets": [{"name": f"{name.title()} Distribution", "values": values}]
            }

        response = {
            "department": prepare_chart_data(department_counts, "department"),
            "designation": prepare_chart_data(designation_counts, "designation"),
            "employment_type": prepare_chart_data(employment_type_counts, "employment_type"),
            "gender": prepare_chart_data(gender_counts, "gender"),
            "marital_status": prepare_chart_data(marital_status_counts, "marital_status")
        }

        frappe.logger().debug(f"Final response prepared with {total_employees} total employees")
        
        # Cache the response for 5 minutes
        set_cached_analytics(response)
        
        return response

    except Exception as e:
        frappe.logger().error(f"Error in get_employee_comprehensive_stats: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch employee statistics"))

# Make sure the module is properly exposed
__all__ = [
    'get_employee_count_by_department', 
    'get_employee_gender_joining_data', 
    'get_employee_comprehensive_stats',
    'create_employee_analytics_indexes',
    'get_analytics_performance_stats'
]

@frappe.whitelist(allow_guest=True)
def get_analytics_performance_stats():
    """
    Get performance statistics for analytics
    """
    try:
        # Get cache hit rate
        cache_key = "employee_analytics_cache"
        cached_data = frappe.cache().get_value(cache_key)
        
        # Get database performance stats
        db_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_employees,
                COUNT(CASE WHEN status = 'Active' THEN 1 END) as active_employees
            FROM `tabEmployee`
        """, as_dict=1)[0]
        
        # Check if indexes exist
        index_exists = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
            AND table_name = 'tabEmployee' 
            AND index_name = 'idx_employee_analytics_status'
        """, as_dict=1)[0].count > 0
        
        return {
            "cache_available": cached_data is not None,
            "total_employees": db_stats.total_employees,
            "active_employees": db_stats.active_employees,
            "indexes_created": index_exists,
            "performance_optimized": True
        }
        
    except Exception as e:
        frappe.logger().error(f"Error getting performance stats: {str(e)}")
        return {"error": str(e)} 