"""
API endpoints for custom doctypes: Work Mission Request and Petty Cash
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_work_mission_requests(filters=None, fields=None, limit=None):
    """
    Fetch all Work Mission Request records with their details
    
    Args:
        filters (dict, optional): Filters to apply to the query
        fields (list, optional): Specific fields to fetch
        limit (int, optional): Limit number of records returned
    
    Returns:
        dict: JSON response with work mission request data
    """
    try:
        # Default fields if none specified
        if not fields:
            fields = [
                'name', 'naming_series', 'workflow_state', 'mission_type', 
                'employee', 'employee_name', 'date', 'posting_date', 'place', 
                'street', 'subject', 'notes', 'progress', 'superior', 
                'transportation_wage', 'operation', 'finance', 'price', 
                'name1', 'sign', 'amended_from'
            ]
        
        # Build query parameters
        query_params = {
            'doctype': 'Work Mission Request',
            'fields': fields,
            'order_by': 'creation desc'
        }
        
        if filters:
            query_params['filters'] = filters
        
        if limit:
            query_params['limit'] = limit
        
        # Fetch records
        records = frappe.get_list(**query_params)
        
        # Get detailed data for each record
        detailed_records = []
        for record in records:
            doc = frappe.get_doc('Work Mission Request', record.name)
            record_data = {
                'name': doc.name,
                'naming_series': doc.get('naming_series'),
                'workflow_state': doc.get('workflow_state'),
                'mission_type': doc.get('mission_type'),
                'employee': doc.get('employee'),
                'employee_name': doc.get('employee_name'),
                'date': doc.get('date'),
                'posting_date': doc.get('posting_date'),
                'place': doc.get('place'),
                'street': doc.get('street'),
                'subject': doc.get('subject'),
                'notes': doc.get('notes'),
                'progress': doc.get('progress'),
                'superior': doc.get('superior'),
                'transportation_wage': doc.get('transportation_wage'),
                'operation': doc.get('operation'),
                'finance': doc.get('finance'),
                'price': doc.get('price'),
                'name1': doc.get('name1'),
                'sign': doc.get('sign'),
                'amended_from': doc.get('amended_from'),
                'creation': doc.creation,
                'modified': doc.modified,
                'owner': doc.owner,
                'modified_by': doc.modified_by,
                'docstatus': doc.docstatus
            }
            detailed_records.append(record_data)
        
        return {
            'success': True,
            'data': detailed_records,
            'count': len(detailed_records),
            'message': f'Successfully fetched {len(detailed_records)} Work Mission Request records'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_work_mission_requests: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch Work Mission Request records'
        }


@frappe.whitelist()
def get_petty_cash_records(filters=None, fields=None, limit=None):
    """
    Fetch all Petty Cash records with their details and child table data
    
    Args:
        filters (dict, optional): Filters to apply to the query
        fields (list, optional): Specific fields to fetch
        limit (int, optional): Limit number of records returned
    
    Returns:
        dict: JSON response with petty cash data including child table records
    """
    try:
        # Default fields if none specified
        if not fields:
            fields = [
                'name', 'naming_series', 'no', 'received_date', 'statement',
                'total_amount', 'total_transportations', 'total_phones_and_internet',
                'total_utilities', 'total_hospitality_and_puffah', 'total_fuel',
                'total_stationery', 'total_guards', 'total_others',
                'previous_balance', 'last_reimbursement_transferred', 'returns_amounts',
                'total_amount_of_petty_cash', 'amount_expenses_of_petty_cash',
                'remaining_amount_of_petty_cash', 'amount_reimbursement_of_petty_cash',
                'received_the_amounts', 'invoices_and_purchase_orders', 'amended_from'
            ]
        
        # Build query parameters
        query_params = {
            'doctype': 'Petty Cash',
            'fields': fields,
            'order_by': 'creation desc'
        }
        
        if filters:
            query_params['filters'] = filters
        
        if limit:
            query_params['limit'] = limit
        
        # Fetch records
        records = frappe.get_list(**query_params)
        
        # Get detailed data for each record including child table
        detailed_records = []
        for record in records:
            doc = frappe.get_doc('Petty Cash', record.name)
            
            # Get child table data
            details = []
            for detail in doc.get('details', []):
                detail_data = {
                    'statement': detail.get('statement'),
                    'date': detail.get('date'),
                    'amount': detail.get('amount'),
                    'transportations': detail.get('transportations'),
                    'phones_and_net': detail.get('phones_and_net'),
                    'utilities': detail.get('utilities'),
                    'hospitality_and_puffah': detail.get('hospitality_and_puffah'),
                    'fuel': detail.get('fuel'),
                    'stationery': detail.get('stationery'),
                    'guards': detail.get('guards'),
                    'others': detail.get('others'),
                    'remark': detail.get('remark')
                }
                details.append(detail_data)
            
            record_data = {
                'name': doc.name,
                'naming_series': doc.get('naming_series'),
                'no': doc.get('no'),
                'received_date': doc.get('received_date'),
                'statement': doc.get('statement'),
                'total_amount': doc.get('total_amount'),
                'total_transportations': doc.get('total_transportations'),
                'total_phones_and_internet': doc.get('total_phones_and_internet'),
                'total_utilities': doc.get('total_utilities'),
                'total_hospitality_and_puffah': doc.get('total_hospitality_and_puffah'),
                'total_fuel': doc.get('total_fuel'),
                'total_stationery': doc.get('total_stationery'),
                'total_guards': doc.get('total_guards'),
                'total_others': doc.get('total_others'),
                'previous_balance': doc.get('previous_balance'),
                'last_reimbursement_transferred': doc.get('last_reimbursement_transferred'),
                'returns_amounts': doc.get('returns_amounts'),
                'total_amount_of_petty_cash': doc.get('total_amount_of_petty_cash'),
                'amount_expenses_of_petty_cash': doc.get('amount_expenses_of_petty_cash'),
                'remaining_amount_of_petty_cash': doc.get('remaining_amount_of_petty_cash'),
                'amount_reimbursement_of_petty_cash': doc.get('amount_reimbursement_of_petty_cash'),
                'received_the_amounts': doc.get('received_the_amounts'),
                'invoices_and_purchase_orders': doc.get('invoices_and_purchase_orders'),
                'amended_from': doc.get('amended_from'),
                'details': details,  # Child table data
                'creation': doc.creation,
                'modified': doc.modified,
                'owner': doc.owner,
                'modified_by': doc.modified_by,
                'docstatus': doc.docstatus
            }
            detailed_records.append(record_data)
        
        return {
            'success': True,
            'data': detailed_records,
            'count': len(detailed_records),
            'message': f'Successfully fetched {len(detailed_records)} Petty Cash records'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_petty_cash_records: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch Petty Cash records'
        }


@frappe.whitelist()
def get_work_mission_request_summary():
    """
    Get summary statistics for Work Mission Request records
    
    Returns:
        dict: Summary data for dashboard/charts
    """
    try:
        # Get total count
        total_count = frappe.db.count('Work Mission Request')
        
        # Get count by status/workflow state
        status_counts = frappe.db.sql("""
            SELECT workflow_state, COUNT(*) as count
            FROM `tabWork Mission Request`
            GROUP BY workflow_state
        """, as_dict=True)
        
        # Get count by mission type
        mission_type_counts = frappe.db.sql("""
            SELECT mission_type, COUNT(*) as count
            FROM `tabWork Mission Request`
            WHERE mission_type IS NOT NULL AND mission_type != ''
            GROUP BY mission_type
        """, as_dict=True)
        
        # Get monthly data for current year
        monthly_data = frappe.db.sql("""
            SELECT 
                MONTH(date) as month,
                MONTHNAME(date) as month_name,
                COUNT(*) as count,
                SUM(CAST(transportation_wage as DECIMAL(10,2))) as total_transportation_wage
            FROM `tabWork Mission Request`
            WHERE YEAR(date) = YEAR(CURDATE())
            GROUP BY MONTH(date), MONTHNAME(date)
            ORDER BY MONTH(date)
        """, as_dict=True)
        
        return {
            'success': True,
            'data': {
                'total_count': total_count,
                'status_distribution': status_counts,
                'mission_type_distribution': mission_type_counts,
                'monthly_trends': monthly_data
            },
            'message': 'Successfully fetched Work Mission Request summary'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_work_mission_request_summary: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch Work Mission Request summary'
        }


@frappe.whitelist()
def get_petty_cash_summary():
    """
    Get summary statistics for Petty Cash records
    
    Returns:
        dict: Summary data for dashboard/charts
    """
    try:
        # Get total count
        total_count = frappe.db.count('Petty Cash')
        
        # Get total amounts summary
        totals = frappe.db.sql("""
            SELECT 
                SUM(total_amount) as total_amount,
                SUM(total_transportations) as total_transportations,
                SUM(total_phones_and_internet) as total_phones_and_internet,
                SUM(total_utilities) as total_utilities,
                SUM(total_hospitality_and_puffah) as total_hospitality_and_puffah,
                SUM(total_fuel) as total_fuel,
                SUM(total_stationery) as total_stationery,
                SUM(total_guards) as total_guards,
                SUM(total_others) as total_others,
                SUM(remaining_amount_of_petty_cash) as total_remaining
            FROM `tabPetty Cash`
        """, as_dict=True)
        
        # Get monthly data for current year
        monthly_data = frappe.db.sql("""
            SELECT 
                MONTH(received_date) as month,
                MONTHNAME(received_date) as month_name,
                COUNT(*) as count,
                SUM(total_amount) as total_amount,
                SUM(remaining_amount_of_petty_cash) as total_remaining
            FROM `tabPetty Cash`
            WHERE YEAR(received_date) = YEAR(CURDATE())
            GROUP BY MONTH(received_date), MONTHNAME(received_date)
            ORDER BY MONTH(received_date)
        """, as_dict=True)
        
        # Get expense category breakdown
        expense_categories = {
            'transportations': totals[0].get('total_transportations', 0) if totals else 0,
            'phones_and_internet': totals[0].get('total_phones_and_internet', 0) if totals else 0,
            'utilities': totals[0].get('total_utilities', 0) if totals else 0,
            'hospitality_and_puffah': totals[0].get('total_hospitality_and_puffah', 0) if totals else 0,
            'fuel': totals[0].get('total_fuel', 0) if totals else 0,
            'stationery': totals[0].get('total_stationery', 0) if totals else 0,
            'guards': totals[0].get('total_guards', 0) if totals else 0,
            'others': totals[0].get('total_others', 0) if totals else 0
        }
        
        return {
            'success': True,
            'data': {
                'total_count': total_count,
                'totals': totals[0] if totals else {},
                'monthly_trends': monthly_data,
                'expense_categories': expense_categories
            },
            'message': 'Successfully fetched Petty Cash summary'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_petty_cash_summary: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch Petty Cash summary'
        }


@frappe.whitelist()
def get_combined_dashboard_data():
    """
    Get combined dashboard data for both doctypes
    
    Returns:
        dict: Combined summary data for dashboard
    """
    try:
        work_mission_summary = get_work_mission_request_summary()
        petty_cash_summary = get_petty_cash_summary()
        
        return {
            'success': True,
            'data': {
                'work_mission_requests': work_mission_summary.get('data', {}),
                'petty_cash': petty_cash_summary.get('data', {})
            },
            'message': 'Successfully fetched combined dashboard data'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_combined_dashboard_data: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch combined dashboard data'
        }

