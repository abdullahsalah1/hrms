# Custom Doctypes API Documentation

This document describes the API endpoints created for the custom doctypes: **Work Mission Request** and **Petty Cash**.

## API Endpoints

All endpoints are accessible via POST requests to `/api/method/hrms.api.custom_doctypes.<method_name>`

### 1. Get Work Mission Requests

**Endpoint:** `hrms.api.custom_doctypes.get_work_mission_requests`

**Description:** Fetch all Work Mission Request records with their details.

**Parameters:**
- `filters` (dict, optional): Filters to apply to the query
- `fields` (list, optional): Specific fields to fetch
- `limit` (int, optional): Limit number of records returned

**Response Fields:**
- `name`: Document name/ID
- `naming_series`: Series used for naming
- `workflow_state`: Current workflow state
- `mission_type`: Type of mission
- `employee`: Employee ID
- `employee_name`: Employee name
- `date`: Mission date
- `posting_date`: Document posting date
- `place`: Mission location
- `street`: Street address
- `subject`: Mission subject/description
- `notes`: Additional notes
- `progress`: Mission progress percentage
- `superior`: Superior/manager
- `transportation_wage`: Transportation allowance
- `operation`: Operation details
- `finance`: Finance information
- `price`: Price/cost
- `name1`: Additional name field
- `sign`: Signature field
- `amended_from`: If amended, reference to original document

**Example Usage:**
```javascript
fetch('/api/method/hrms.api.custom_doctypes.get_work_mission_requests', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': getCsrfToken()
    },
    body: JSON.stringify({
        filters: { "workflow_state": "Approved" },
        limit: 50
    })
})
```

### 2. Get Petty Cash Records

**Endpoint:** `hrms.api.custom_doctypes.get_petty_cash_records`

**Description:** Fetch all Petty Cash records with their details and child table data.

**Parameters:**
- `filters` (dict, optional): Filters to apply to the query
- `fields` (list, optional): Specific fields to fetch
- `limit` (int, optional): Limit number of records returned

**Response Fields:**
- `name`: Document name/ID
- `naming_series`: Series used for naming
- `no`: Petty cash number
- `received_date`: Date received
- `statement`: Statement/description
- `total_amount`: Total amount
- `total_transportations`: Total transportation expenses
- `total_phones_and_internet`: Total phone and internet expenses
- `total_utilities`: Total utility expenses
- `total_hospitality_and_puffah`: Total hospitality expenses
- `total_fuel`: Total fuel expenses
- `total_stationery`: Total stationery expenses
- `total_guards`: Total guard expenses
- `total_others`: Total other expenses
- `previous_balance`: Previous balance
- `last_reimbursement_transferred`: Last reimbursement amount
- `returns_amounts`: Return amounts
- `total_amount_of_petty_cash`: Total petty cash amount
- `amount_expenses_of_petty_cash`: Total expenses
- `remaining_amount_of_petty_cash`: Remaining amount
- `amount_reimbursement_of_petty_cash`: Reimbursement amount
- `received_the_amounts`: Received by
- `invoices_and_purchase_orders`: Attached documents
- `details`: Array of child table records with expense details

**Child Table Fields (details):**
- `statement`: Expense description
- `date`: Expense date
- `amount`: Expense amount
- `transportations`: Transportation amount
- `phones_and_net`: Phone and internet amount
- `utilities`: Utilities amount
- `hospitality_and_puffah`: Hospitality amount
- `fuel`: Fuel amount
- `stationery`: Stationery amount
- `guards`: Guards amount
- `others`: Other expenses amount
- `remark`: Additional remarks

### 3. Get Work Mission Request Summary

**Endpoint:** `hrms.api.custom_doctypes.get_work_mission_request_summary`

**Description:** Get summary statistics for Work Mission Request records for dashboard/charts.

**Response Data:**
- `total_count`: Total number of records
- `status_distribution`: Count by workflow state
- `mission_type_distribution`: Count by mission type
- `monthly_trends`: Monthly data for current year

### 4. Get Petty Cash Summary

**Endpoint:** `hrms.api.custom_doctypes.get_petty_cash_summary`

**Description:** Get summary statistics for Petty Cash records for dashboard/charts.

**Response Data:**
- `total_count`: Total number of records
- `totals`: Sum of all amount fields
- `monthly_trends`: Monthly data for current year
- `expense_categories`: Breakdown by expense category

### 5. Get Combined Dashboard Data

**Endpoint:** `hrms.api.custom_doctypes.get_combined_dashboard_data`

**Description:** Get combined dashboard data for both doctypes.

**Response Data:**
- `work_mission_requests`: Summary data for Work Mission Requests
- `petty_cash`: Summary data for Petty Cash

## Authentication

All API endpoints require proper Frappe authentication. Include the CSRF token in your requests:

```javascript
headers: {
    'Content-Type': 'application/json',
    'X-Frappe-CSRF-Token': getCsrfToken()
}
```

## Error Handling

All endpoints return a consistent response format:

**Success Response:**
```json
{
    "success": true,
    "data": [...],
    "count": 10,
    "message": "Successfully fetched records"
}
```

**Error Response:**
```json
{
    "success": false,
    "error": "Error message",
    "message": "Failed to fetch records"
}
```

## Testing

A test HTML page is available at `/assets/hrms/api_test.html` which demonstrates:
- Loading and displaying data from both doctypes
- Creating charts and visualizations
- Dashboard statistics
- Responsive design for mobile devices

## Usage Examples

### Basic Data Fetching
```javascript
// Get all Work Mission Requests
const wmrResponse = await fetch('/api/method/hrms.api.custom_doctypes.get_work_mission_requests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
});
const wmrData = await wmrResponse.json();

// Get Petty Cash records with filters
const pcResponse = await fetch('/api/method/hrms.api.custom_doctypes.get_petty_cash_records', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        filters: { "received_date": [">=", "2024-01-01"] },
        limit: 100
    })
});
const pcData = await pcResponse.json();
```

### Dashboard Data
```javascript
// Get combined dashboard data
const dashboardResponse = await fetch('/api/method/hrms.api.custom_doctypes.get_combined_dashboard_data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
});
const dashboardData = await dashboardResponse.json();

// Use data for charts and statistics
if (dashboardData.success) {
    const wmrStats = dashboardData.data.work_mission_requests;
    const pcStats = dashboardData.data.petty_cash;
    
    // Create charts, update UI, etc.
}
```

## Security Notes

1. All endpoints use `@frappe.whitelist()` decorator for proper access control
2. Error logging is implemented for debugging
3. Input validation should be added based on your security requirements
4. Consider implementing rate limiting for production use

## Customization

The API endpoints can be customized by:
1. Modifying the field lists in the functions
2. Adding additional filters or parameters
3. Implementing custom business logic
4. Adding more summary/aggregation endpoints as needed

