from collections import defaultdict
from datetime import date
import frappe

from hrms.hrms.api.finance_utils import fetch_normalized

FINANCE_DOCTYPES = [
	"Purchases Order",
	"Work Mission Request",
	"Petty Cash",
	"Internet and Phone Payment",
]


def _resolve_doctypes(args):
	dt = args.get("doctype")
	if dt:
		return [dt] if isinstance(dt, str) else dt
	return FINANCE_DOCTYPES


def _collect_rows(args):
	rows = []
	for dt in _resolve_doctypes(args):
		try:
			rows.extend(fetch_normalized(dt, args))
		except Exception:
			# Missing doctype or permission denied; continue others
			continue
	return rows


@frappe.whitelist()
def summary(**kwargs):
	args = frappe._dict(kwargs)
	rows = _collect_rows(args)
	total = sum(r["amount"] for r in rows)
	today = date.today()
	this_month_rows = [r for r in rows if r["date"] and r["date"][:7] == today.strftime("%Y-%m")]
	total_this_month = sum(r["amount"] for r in this_month_rows)
	# heuristic pending
	pending_rows = [r for r in rows if r.get("status") and str(r["status"]).lower() in ("pending", "open", "draft", "to approve", "to_approve")]
	by_category = defaultdict(float)
	for r in rows:
		by_category[r["category"]] += r["amount"]
	return {
		"totals": {"overall": total, "this_month": total_this_month, "pending": sum(r["amount"] for r in pending_rows)},
		"by_category": [{"category": k, "amount": v} for k, v in by_category.items()],
		"count": len(rows),
	}


@frappe.whitelist()
def trends(**kwargs):
	args = frappe._dict(kwargs)
	rows = _collect_rows(args)
	series = defaultdict(float)
	for r in rows:
		if not r["date"]:
			continue
		series[r["date"][:7]] += r["amount"]
	labels = sorted(series.keys())
	return {"labels": labels, "data": [series[k] for k in labels]}


@frappe.whitelist()
def pending(**kwargs):
	args = frappe._dict(kwargs)
	rows = _collect_rows(args)
	pending_rows = [r for r in rows if r.get("status") and str(r["status"]).lower() in ("pending", "open", "draft", "to approve", "to_approve")]
	return {"count": len(pending_rows), "total": sum(r["amount"] for r in pending_rows), "items": pending_rows[:200]}


@frappe.whitelist()
def by_category(**kwargs):
	args = frappe._dict(kwargs)
	rows = _collect_rows(args)
	by_cat = defaultdict(list)
	totals = defaultdict(float)
	for r in rows:
		by_cat[r["category"]].append(r)
		totals[r["category"]] += r["amount"]
	return {"categories": [{"category": c, "total": totals[c], "items": items[:200]} for c, items in by_cat.items()]}


# Petty Cash specific API methods
@frappe.whitelist()
def petty_cash_summary(**kwargs):
	"""Get summary data for petty cash dashboard"""
	args = frappe._dict(kwargs)
	
	# Get all available fields from Petty Cash doctype
	meta = frappe.get_meta("Petty Cash")
	available_fields = [f.fieldname for f in meta.fields if f.fieldtype == "Currency"]
	
	# Build fields list dynamically
	fields_to_fetch = ["name", "title"]
	for field in available_fields:
		if any(keyword in field.lower() for keyword in ['total', 'amount', 'balance', 'cash', 'expense', 'reimbursement', 'return']):
			fields_to_fetch.append(field)
	
	# Get petty cash documents with dynamic fields
	petty_cash_docs = frappe.get_all("Petty Cash", 
		filters={"docstatus": 1},
		fields=fields_to_fetch
	)
	
	if not petty_cash_docs:
		return {
			"previous_balance": 0,
			"total_petty_cash": 0,
			"total_expenses": 0,
			"remaining_amount": 0,
			"last_reimbursement": 0,
			"returns_amount": 0,
			"reimbursement_amount": 0
		}
	
	# Calculate totals using actual field names
	total_petty_cash = 0
	previous_balance = 0
	returns_amount = 0
	reimbursement_amount = 0
	
	for doc in petty_cash_docs:
		# Try to find the right fields dynamically
		for field_name, value in doc.items():
			if value and isinstance(value, (int, float)):
				if 'total' in field_name.lower() and 'cash' in field_name.lower():
					total_petty_cash += value
				elif 'previous' in field_name.lower() and 'balance' in field_name.lower():
					previous_balance += value
				elif 'return' in field_name.lower():
					returns_amount += value
				elif 'reimbursement' in field_name.lower():
					reimbursement_amount += value
	
	# Get child table expenses
	child_table_name = None
	for field in meta.fields:
		if field.fieldtype == "Table":
			child_table_name = field.options
			break
	
	total_expenses = 0
	if child_table_name:
		# Get all expense amounts from child table
		child_meta = frappe.get_meta(child_table_name)
		currency_fields = [f.fieldname for f in child_meta.fields if f.fieldtype == "Currency"]
		
		for doc in petty_cash_docs:
			child_rows = frappe.get_all(child_table_name, 
				filters={"parent": doc.name},
				fields=currency_fields
			)
			for row in child_rows:
				for field in currency_fields:
					total_expenses += row.get(field, 0) or 0
	
	remaining_amount = total_petty_cash - total_expenses
	
	return {
		"previous_balance": previous_balance,
		"total_petty_cash": total_petty_cash,
		"total_expenses": total_expenses,
		"remaining_amount": remaining_amount,
		"last_reimbursement": reimbursement_amount,
		"returns_amount": returns_amount,
		"reimbursement_amount": reimbursement_amount
	}


@frappe.whitelist()
def petty_cash_category_breakdown(**kwargs):
	"""Get expense breakdown by category"""
	args = frappe._dict(kwargs)
	
	# Get child table metadata
	meta = frappe.get_meta("Petty Cash")
	child_table_name = None
	for field in meta.fields:
		if field.fieldtype == "Table":
			child_table_name = field.options
			break
	
	if not child_table_name:
		return {"labels": [], "values": []}
	
	# Get currency fields from child table
	child_meta = frappe.get_meta(child_table_name)
	currency_fields = [f for f in child_meta.fields if f.fieldtype == "Currency" and f.fieldname not in ["amount", "total"]]
	
	# Calculate totals by category
	category_totals = {}
	for field in currency_fields:
		total = frappe.db.sql(f"""
			SELECT SUM(`{field.fieldname}`) as total
			FROM `tab{child_table_name}`
			WHERE `{field.fieldname}` > 0
		""", as_dict=True)
		
		if total and total[0].total:
			category_totals[field.label or field.fieldname] = total[0].total
	
	# Convert to chart format
	labels = list(category_totals.keys())
	values = list(category_totals.values())
	
	return {"labels": labels, "values": values}


@frappe.whitelist()
def petty_cash_trends(**kwargs):
	"""Get expense trends over time"""
	args = frappe._dict(kwargs)
	
	# Get child table metadata
	meta = frappe.get_meta("Petty Cash")
	child_table_name = None
	for field in meta.fields:
		if field.fieldtype == "Table":
			child_table_name = field.options
			break
	
	if not child_table_name:
		return {"labels": [], "values": []}
	
	# Get date field from child table
	child_meta = frappe.get_meta(child_table_name)
	date_field = None
	for field in child_meta.fields:
		if field.fieldtype == "Date":
			date_field = field.fieldname
			break
	
	if not date_field:
		return {"labels": [], "values": []}
	
	# Get daily totals
	trends = frappe.db.sql(f"""
		SELECT DATE(`{date_field}`) as date, SUM(amount) as total
		FROM `tab{child_table_name}`
		WHERE `{date_field}` IS NOT NULL
		GROUP BY DATE(`{date_field}`)
		ORDER BY DATE(`{date_field}`)
	""", as_dict=True)
	
	labels = [str(trend.date) for trend in trends]
	values = [trend.total or 0 for trend in trends]
	
	return {"labels": labels, "values": values}


@frappe.whitelist()
def petty_cash_transactions(**kwargs):
	"""Get transaction details from child table"""
	args = frappe._dict(kwargs)
	
	# Get child table metadata
	meta = frappe.get_meta("Petty Cash")
	child_table_name = None
	for field in meta.fields:
		if field.fieldtype == "Table":
			child_table_name = field.options
			break
	
	if not child_table_name:
		return {"data": []}
	
	# Build query
	child_meta = frappe.get_meta(child_table_name)
	fields = [f.fieldname for f in child_meta.fields if f.fieldname not in ["name", "parent", "parenttype", "parentfield", "idx"]]
	
	# Apply filters
	filters = {"parent": ["!=", ""]}
	if args.get("document"):
		filters["parent"] = args.document
	
	# Get transactions
	transactions = frappe.get_all(child_table_name,
		filters=filters,
		fields=fields,
		limit=1000
	)
	
	return {"data": transactions}


@frappe.whitelist()
def inspect_petty_cash_structure():
	"""Inspect Petty Cash doctype structure for debugging"""
	try:
		# Get Petty Cash doctype metadata
		meta = frappe.get_meta("Petty Cash")
		parent_fields = []
		child_table_name = None
		child_fields = []
		
		# Get parent doctype fields
		for field in meta.fields:
			parent_fields.append({
				"fieldname": field.fieldname,
				"fieldtype": field.fieldtype,
				"label": field.label,
				"options": getattr(field, 'options', None)
			})
			if field.fieldtype == "Table":
				child_table_name = field.options
		
		# Get child table fields if exists
		if child_table_name:
			try:
				child_meta = frappe.get_meta(child_table_name)
				for field in child_meta.fields:
					child_fields.append({
						"fieldname": field.fieldname,
						"fieldtype": field.fieldtype,
						"label": field.label,
						"options": getattr(field, 'options', None)
					})
			except Exception as e:
				child_fields = [{"error": str(e)}]
		
		# Get sample data
		sample_docs = frappe.get_all("Petty Cash", limit=3, fields=["name", "title", "docstatus"])
		sample_child_data = []
		
		if child_table_name and sample_docs:
			try:
				sample_child_data = frappe.get_all(child_table_name, 
					filters={"parent": sample_docs[0].name}, 
					limit=2, 
					fields=["*"]
				)
			except Exception as e:
				sample_child_data = [{"error": str(e)}]
		
		return {
			"parent_fields": parent_fields,
			"child_table_name": child_table_name,
			"child_fields": child_fields,
			"sample_docs": sample_docs,
			"sample_child_data": sample_child_data,
			"total_parent_docs": frappe.db.count("Petty Cash"),
			"total_child_records": frappe.db.count(child_table_name) if child_table_name else 0
		}
		
	except Exception as e:
		return {"error": str(e), "traceback": frappe.get_traceback()}


