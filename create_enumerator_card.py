import frappe

def create_enumerator_number_card():
    card_name = "Total Enumerators"
    doctype = "i-APS Enumerators"
    dashboard_name = "Workspace"  # Change to your dashboard name if needed

    # 1. Create Number Card if not exists
    if not frappe.db.exists("Number Card", card_name):
        card = frappe.get_doc({
            "doctype": "Number Card",
            "number_card_name": card_name,
            "document_type": doctype,
            "function": "Count",
            "filters_json": "[]",
            "show_percentage_stats": 0,
            "show_transaction_count": 0,
            "show_last_synced_on": 0,
            "color": "blue"
        })
        card.insert(ignore_permissions=True)
        print(f"Created Number Card: {card_name}")
    else:
        card = frappe.get_doc("Number Card", card_name)
        print(f"Number Card already exists: {card_name}")

    # 2. Add Number Card to Dashboard if not already present
    if not frappe.db.exists("Dashboard Card", {"card": card.name, "dashboard": dashboard_name}):
        dashboard_card = frappe.get_doc({
            "doctype": "Dashboard Card",
            "card": card.name,
            "dashboard": dashboard_name,
            "label": card_name,
            "color": "blue",
            "filters_json": "[]",
            "order": 0
        })
        dashboard_card.insert(ignore_permissions=True)
        print(f"Added Number Card to dashboard: {dashboard_name}")
    else:
        print(f"Number Card already on dashboard: {dashboard_name}")

# Run the function if this script is executed directly
if __name__ == "__main__":
    create_enumerator_number_card() 