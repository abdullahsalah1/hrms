import frappe
from frappe.utils import flt

# Heuristics to detect amount/date/requester/status fields
AMOUNT_PRIORITY = [
	"grand_total",
	"total",
	"amount",
	"net_total",
	"paid_amount",
	"claimed_amount",
	"budget",
	"total_amount",
	"expense_amount",
]

DATE_CANDIDATES = ["posting_date", "transaction_date", "date", "creation"]
REQUESTER_CANDIDATES = ["requester", "employee", "requested_by", "owner", "applicant"]

DEFAULT_CATEGORY_MAP = {
	"Purchases Order": "Purchases",
	"Work Mission Request": "Missions",
	"Petty Cash": "Petty Cash",
	"Internet and Phone Payment": "Internet/Phone",
}


def _get_meta_fields(doctype: str):
	meta = frappe.get_meta(doctype)
	return {df.fieldname: df.as_dict() for df in meta.fields}


def _choose_amount_field(field_map):
	# strong exacts first
	for name in AMOUNT_PRIORITY:
		if name in field_map and field_map[name].get("fieldtype") in ("Currency", "Float"):
			return name
	# keyword currency-like
	for fname, df in field_map.items():
		if df.get("fieldtype") in ("Currency", "Float"):
			lname = fname.lower()
			if any(k in lname for k in AMOUNT_PRIORITY):
				return fname
	# fallback: first currency/float
	for fname, df in field_map.items():
		if df.get("fieldtype") in ("Currency", "Float"):
			return fname
	return None


def _choose_date_field(field_map):
	for cand in DATE_CANDIDATES:
		if cand in field_map:
			return cand
	for fname, df in field_map.items():
		if df.get("fieldtype") in ("Date", "Datetime"):
			return fname
	return None


def _choose_requester_field(field_map):
	for cand in REQUESTER_CANDIDATES:
		if cand in field_map:
			return cand
	for fname, df in field_map.items():
		if df.get("fieldtype") == "Link" and df.get("options") in ("Employee", "User"):
			return fname
	return "owner"


def _choose_status_field(field_map):
	if "workflow_state" in field_map:
		return "workflow_state"
	if "status" in field_map:
		return "status"
	return None


def build_config(doctype: str):
	fmap = _get_meta_fields(doctype)
	return {
		"amount_field": _choose_amount_field(fmap),
		"date_field": _choose_date_field(fmap),
		"requester_field": _choose_requester_field(fmap),
		"status_field": _choose_status_field(fmap),
	}


def _apply_filters(args, doctype: str, date_field: str):
	filters = {}
	if args.get("status"):
		filters["status"] = args.get("status")
	if args.get("company"):
		filters["company"] = args.get("company")
	additional_filters = []
	if date_field:
		if args.get("date_from"):
			additional_filters.append([doctype, date_field, ">=", args.get("date_from")])
		if args.get("date_to"):
			additional_filters.append([doctype, date_field, "<=", args.get("date_to")])
	return filters, additional_filters


def _get_list(doctype: str, fields, filters, additional_filters):
	return frappe.get_list(
		doctype=doctype,
		fields=fields,
		filters=filters,
		limit_page_length=0,
		as_list=False,
	)


def _normalize(doctype: str, cfg: dict, row: dict):
	amount = flt(row.get(cfg.get("amount_field"))) if cfg.get("amount_field") else 0.0
	date_value = row.get(cfg.get("date_field")) if cfg.get("date_field") else row.get("creation")
	requester = row.get(cfg.get("requester_field")) if cfg.get("requester_field") else row.get("owner")
	status = row.get(cfg.get("status_field")) if cfg.get("status_field") else row.get("status")
	company = row.get("company")
	category = DEFAULT_CATEGORY_MAP.get(doctype, doctype)
	return {
		"doctype": doctype,
		"name": row.get("name"),
		"date": str(date_value) if date_value else None,
		"amount": amount,
		"status": status,
		"requester": requester,
		"company": company,
		"category": category,
		"currency": row.get("currency"),
	}


def fetch_normalized(doctype: str, args):
	cfg = build_config(doctype)
	fields = ["name", "company", "currency"]
	for key in ("amount_field", "date_field", "requester_field", "status_field"):
		if cfg.get(key) and cfg[key] not in fields:
			fields.append(cfg[key])
	filters, additional_filters = _apply_filters(args, doctype, cfg.get("date_field"))
	rows = _get_list(doctype, fields, filters, additional_filters)
	return [_normalize(doctype, cfg, r) for r in rows]


