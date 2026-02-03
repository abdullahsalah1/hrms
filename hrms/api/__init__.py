# This file is intentionally left empty to mark this directory as a Python package

import frappe
from frappe import _

# Custom Doctypes API Functions
from frappe.model import get_permitted_fields
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import Order
from frappe.utils import add_days, date_diff, getdate, strip_html

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

SUPPORTED_FIELD_TYPES = [
	"Link",
	"Select",
	"Small Text",
	"Text",
	"Long Text",
	"Text Editor",
	"Table",
	"Check",
	"Data",
	"Float",
	"Int",
	"Section Break",
	"Date",
	"Time",
	"Datetime",
	"Currency",
]


@frappe.whitelist()
def get_current_user_info() -> dict:
	current_user = frappe.session.user
	user = frappe.db.get_value(
		"User", current_user, ["name", "first_name", "full_name", "user_image"], as_dict=True
	)
	user["roles"] = frappe.get_roles(current_user)

	return user


@frappe.whitelist()
def get_current_employee_info() -> dict:
	current_user = frappe.session.user
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": current_user, "status": "Active"},
		[
			"name",
			"first_name",
			"employee_name",
			"designation",
			"department",
			"company",
			"reports_to",
			"user_id",
		],
		as_dict=True,
	)
	return employee


@frappe.whitelist()
def get_all_employees() -> list[dict]:
	return frappe.get_all(
		"Employee",
		fields=[
			"name",
			"employee_name",
			"designation",
			"department",
			"company",
			"reports_to",
			"user_id",
			"image",
			"status",
			"preferred_email",
			"date_of_joining",
		],
		limit=999999,
	)


# HR Settings
@frappe.whitelist()
def get_hr_settings() -> dict:
	settings = frappe.db.get_singles_dict("HR Settings", cast=True)
	return frappe._dict(
		allow_employee_checkin_from_mobile_app=settings.allow_employee_checkin_from_mobile_app,
		allow_geolocation_tracking=settings.allow_geolocation_tracking,
	)


# Notifications
@frappe.whitelist()
def get_unread_notifications_count() -> int:
	return frappe.db.count(
		"PWA Notification",
		{"to_user": frappe.session.user, "read": 0},
	)


@frappe.whitelist()
def mark_all_notifications_as_read() -> None:
	frappe.db.set_value(
		"PWA Notification",
		{"to_user": frappe.session.user, "read": 0},
		"read",
		1,
		update_modified=False,
	)


@frappe.whitelist()
def are_push_notifications_enabled() -> bool:
	try:
		return frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay")
	except frappe.DoesNotExistError:
		# push notifications are not supported in the current framework version
		return False


# Attendance
@frappe.whitelist()
def get_attendance_calendar_events(employee: str, from_date: str, to_date: str) -> dict[str, str]:
	holidays = get_holidays_for_calendar(employee, from_date, to_date)
	attendance = get_attendance_for_calendar(employee, from_date, to_date)
	events = {}

	date = getdate(from_date)
	while date_diff(to_date, date) >= 0:
		date_str = date.strftime("%Y-%m-%d")
		if date in holidays:
			events[date_str] = "Holiday"
		elif date in attendance:
			events[date_str] = attendance[date]
		date = add_days(date, 1)

	return events


def get_attendance_for_calendar(employee: str, from_date: str, to_date: str) -> list[dict[str, str]]:
	attendance = frappe.get_all(
		"Attendance",
		{"employee": employee, "attendance_date": ["between", [from_date, to_date]]},
		["attendance_date", "status"],
	)
	return {d["attendance_date"]: d["status"] for d in attendance}


def get_holidays_for_calendar(employee: str, from_date: str, to_date: str) -> list[str]:
	if holiday_list := get_holiday_list_for_employee(employee, raise_exception=False):
		return frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [from_date, to_date]]},
			pluck="holiday_date",
		)

	return []


@frappe.whitelist()
def get_shift_requests(
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Shift Request", employee, approver_id, for_approval)
	fields = [
		"name",
		"employee",
		"employee_name",
		"shift_type",
		"from_date",
		"to_date",
		"status",
		"approver",
		"docstatus",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Shift Request"):
		fields.append(workflow_state_field)

	shift_requests = frappe.get_list(
		"Shift Request",
		fields=fields,
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in shift_requests:
			application["workflow_state_field"] = workflow_state_field

	return shift_requests


def get_filters(
	doctype: str,
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
) -> dict:
	filters = frappe._dict()
	if for_approval:
		filters.docstatus = 0
		filters.employee = ("!=", employee)

		if workflow := get_workflow(doctype):
			allowed_states = get_allowed_states_for_workflow(workflow, approver_id)
			filters[workflow.workflow_state_field] = ("in", allowed_states)
		else:
			approver_field_map = {
				"Shift Request": "approver",
				"Leave Application": "leave_approver",
				"Expense Claim": "expense_approver",
			}
			filters.status = "Open" if doctype == "Leave Application" else "Draft"
			filters[approver_field_map[doctype]] = approver_id
	else:
		filters.docstatus = ("!=", 2)
		filters.employee = employee

	return filters


@frappe.whitelist()
def get_shift_request_approvers(employee: str) -> str | list[str]:
	shift_request_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["shift_request_approver", "department"],
	)

	department_approvers = []
	if department:
		department_approvers = get_department_approvers(department, "shift_request_approver")
		if not shift_request_approver:
			shift_request_approver = frappe.db.get_value(
				"Department Approver",
				{"parent": department, "parentfield": "shift_request_approver", "idx": 1},
				"approver",
			)

	shift_request_approver_name = frappe.db.get_value("User", shift_request_approver, "full_name", cache=True)

	if shift_request_approver and shift_request_approver not in [
		approver.name for approver in department_approvers
	]:
		department_approvers.insert(
			0, {"name": shift_request_approver, "full_name": shift_request_approver_name}
		)

	return department_approvers


@frappe.whitelist()
def get_shifts(employee: str) -> list[dict[str, str]]:
	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	ShiftType = frappe.qb.DocType("Shift Type")
	return (
		frappe.qb.from_(ShiftAssignment)
		.join(ShiftType)
		.on(ShiftAssignment.shift_type == ShiftType.name)
		.select(
			ShiftAssignment.name,
			ShiftAssignment.shift_type,
			ShiftAssignment.start_date,
			ShiftAssignment.end_date,
			ShiftType.start_time,
			ShiftType.end_time,
		)
		.where(
			(ShiftAssignment.employee == employee)
			& (ShiftAssignment.status == "Active")
			& (ShiftAssignment.docstatus == 1)
		)
		.orderby(ShiftAssignment.start_date, order=Order.asc)
	).run(as_dict=True)


# Leaves and Holidays
@frappe.whitelist()
def get_leave_applications(
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Leave Application", employee, approver_id, for_approval)
	fields = [
		"name",
		"posting_date",
		"employee",
		"employee_name",
		"leave_type",
		"status",
		"from_date",
		"to_date",
		"half_day",
		"half_day_date",
		"description",
		"total_leave_days",
		"leave_balance",
		"leave_approver",
		"posting_date",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Leave Application"):
		fields.append(workflow_state_field)

	applications = frappe.get_list(
		"Leave Application",
		fields=fields,
		filters=filters,
		order_by="posting_date desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in applications:
			application["workflow_state_field"] = workflow_state_field

	return applications


@frappe.whitelist()
def get_leave_balance_map(employee: str) -> dict[str, dict[str, float]]:
	"""
	Returns a map of leave type and balance details like:
	{
	        'Casual Leave': {'allocated_leaves': 10.0, 'balance_leaves': 5.0},
	        'Earned Leave': {'allocated_leaves': 3.0, 'balance_leaves': 3.0},
	}
	"""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	date = getdate()
	leave_map = {}

	leave_details = get_leave_details(employee, date)
	allocation = leave_details["leave_allocation"]

	for leave_type, details in allocation.items():
		leave_map[leave_type] = {
			"allocated_leaves": details.get("total_leaves"),
			"balance_leaves": details.get("remaining_leaves"),
		}

	return leave_map


@frappe.whitelist()
def get_holidays_for_employee(employee: str) -> list[dict]:
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return []

	Holiday = frappe.qb.DocType("Holiday")
	holidays = (
		frappe.qb.from_(Holiday)
		.select(Holiday.name, Holiday.holiday_date, Holiday.description)
		.where((Holiday.parent == holiday_list) & (Holiday.weekly_off == 0))
		.orderby(Holiday.holiday_date, order=Order.asc)
	).run(as_dict=True)

	for holiday in holidays:
		holiday["description"] = strip_html(holiday["description"] or "").strip()

	return holidays


@frappe.whitelist()
def get_leave_approval_details(employee: str) -> dict:
	leave_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["leave_approver", "department"],
	)

	if not leave_approver and department:
		leave_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "leave_approvers", "idx": 1},
			"approver",
		)

	leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name", cache=True)
	department_approvers = get_department_approvers(department, "leave_approvers")

	if leave_approver and leave_approver not in [approver.name for approver in department_approvers]:
		department_approvers.append({"name": leave_approver, "full_name": leave_approver_name})

	return dict(
		leave_approver=leave_approver,
		leave_approver_name=leave_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value(
			"HR Settings", "leave_approver_mandatory_in_leave_application"
		),
	)


def get_department_approvers(department: str, parentfield: str) -> list[str]:
	if not department:
		return []

	department_details = frappe.db.get_value("Department", department, ["lft", "rgt"], as_dict=True)
	departments = frappe.get_all(
		"Department",
		filters={
			"lft": ("<=", department_details.lft),
			"rgt": (">=", department_details.rgt),
			"disabled": 0,
		},
		pluck="name",
	)

	Approver = frappe.qb.DocType("Department Approver")
	User = frappe.qb.DocType("User")
	department_approvers = (
		frappe.qb.from_(User)
		.join(Approver)
		.on(Approver.approver == User.name)
		.select(User.name.as_("name"), User.full_name.as_("full_name"))
		.where((Approver.parent.isin(departments)) & (Approver.parentfield == parentfield))
	).run(as_dict=True)

	return department_approvers


@frappe.whitelist()
def get_leave_types(employee: str, date: str) -> list:
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	date = date or getdate()

	leave_details = get_leave_details(employee, date)
	leave_types = list(leave_details["leave_allocation"].keys()) + leave_details["lwps"]

	return leave_types


# Expense Claims
@frappe.whitelist()
def get_expense_claims(
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Expense Claim", employee, approver_id, for_approval)
	fields = [
		"`tabExpense Claim`.name",
		"`tabExpense Claim`.posting_date",
		"`tabExpense Claim`.employee",
		"`tabExpense Claim`.employee_name",
		"`tabExpense Claim`.approval_status",
		"`tabExpense Claim`.status",
		"`tabExpense Claim`.expense_approver",
		"`tabExpense Claim`.total_claimed_amount",
		"`tabExpense Claim`.posting_date",
		"`tabExpense Claim`.company",
		"`tabExpense Claim`.creation",
		"`tabExpense Claim Detail`.expense_type",
		"count(`tabExpense Claim Detail`.expense_type) as total_expenses",
	]

	if workflow_state_field := get_workflow_state_field("Expense Claim"):
		fields.append(workflow_state_field)

	claims = frappe.get_list(
		"Expense Claim",
		fields=fields,
		filters=filters,
		order_by="`tabExpense Claim`.posting_date desc",
		group_by="`tabExpense Claim`.name",
		limit=limit,
	)

	if workflow_state_field:
		for claim in claims:
			claim["workflow_state_field"] = workflow_state_field

	return claims


@frappe.whitelist()
def get_expense_claim_summary(employee: str) -> dict:
	from frappe.query_builder.functions import Sum

	Claim = frappe.qb.DocType("Expense Claim")

	pending_claims_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Draft", Claim.total_claimed_amount).else_(0)
	)
	sum_pending_claims = Sum(pending_claims_case).as_("total_pending_amount")

	approved_claims_case = (
		frappe.qb.terms.Case()
		.when(Claim.approval_status == "Approved", Claim.total_sanctioned_amount)
		.else_(0)
	)
	sum_approved_claims = Sum(approved_claims_case).as_("total_approved_amount")

	rejected_claims_case = (
		frappe.qb.terms.Case()
		.when(Claim.approval_status == "Rejected", Claim.total_sanctioned_amount)
		.else_(0)
	)
	sum_rejected_claims = Sum(rejected_claims_case).as_("total_rejected_amount")

	summary = (
		frappe.qb.from_(Claim)
		.select(
			sum_pending_claims,
			sum_approved_claims,
			sum_rejected_claims,
			Claim.company,
		)
		.where((Claim.docstatus != 2) & (Claim.employee == employee))
	).run(as_dict=True)[0]

	currency = frappe.db.get_value("Company", summary.company, "default_currency")
	summary["currency"] = currency

	return summary


@frappe.whitelist()
def get_expense_type_description(expense_type: str) -> str:
	return frappe.db.get_value("Expense Claim Type", expense_type, "description")


@frappe.whitelist()
def get_expense_claim_types() -> list[dict]:
	ClaimType = frappe.qb.DocType("Expense Claim Type")

	return (frappe.qb.from_(ClaimType).select(ClaimType.name, ClaimType.description)).run(as_dict=True)


@frappe.whitelist()
def get_expense_approval_details(employee: str) -> dict:
	expense_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["expense_approver", "department"],
	)

	if not expense_approver and department:
		expense_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "expense_approvers", "idx": 1},
			"approver",
		)

	expense_approver_name = frappe.db.get_value("User", expense_approver, "full_name", cache=True)
	department_approvers = get_department_approvers(department, "expense_approvers")

	if expense_approver and expense_approver not in [approver.name for approver in department_approvers]:
		department_approvers.append({"name": expense_approver, "full_name": expense_approver_name})

	return dict(
		expense_approver=expense_approver,
		expense_approver_name=expense_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value("HR Settings", "expense_approver_mandatory_in_expense_claim"),
	)


# Employee Advance
@frappe.whitelist()
def get_employee_advance_balance(employee: str) -> list[dict]:
	Advance = frappe.qb.DocType("Employee Advance")

	advances = (
		frappe.qb.from_(Advance)
		.select(
			Advance.name,
			Advance.employee,
			Advance.status,
			Advance.purpose,
			Advance.paid_amount,
			(Advance.paid_amount - (Advance.claimed_amount + Advance.return_amount)).as_("balance_amount"),
			Advance.posting_date,
			Advance.currency,
		)
		.where(
			(Advance.docstatus == 1)
			& (Advance.paid_amount)
			& (Advance.employee == employee)
			# don't need claimed & returned advances, only partly or completely paid ones
			& (Advance.status.isin(["Paid", "Unpaid"]))
		)
		.orderby(Advance.posting_date, order=Order.desc)
	).run(as_dict=True)

	return advances


@frappe.whitelist()
def get_advance_account(company: str) -> str | None:
	return frappe.db.get_value("Company", company, "default_employee_advance_account", cache=True)


# Company
@frappe.whitelist()
def get_company_currencies() -> dict:
	Company = frappe.qb.DocType("Company")
	Currency = frappe.qb.DocType("Currency")

	query = (
		frappe.qb.from_(Company)
		.join(Currency)
		.on(Company.default_currency == Currency.name)
		.select(
			Company.name,
			Company.default_currency,
			Currency.name.as_("currency"),
			Currency.symbol.as_("symbol"),
		)
	)

	companies = query.run(as_dict=True)
	return {company.name: (company.default_currency, company.symbol) for company in companies}


@frappe.whitelist()
def get_currency_symbols() -> dict:
	Currency = frappe.qb.DocType("Currency")

	currencies = (frappe.qb.from_(Currency).select(Currency.name, Currency.symbol)).run(as_dict=True)

	return {currency.name: currency.symbol or currency.name for currency in currencies}


@frappe.whitelist()
def get_company_cost_center_and_expense_account(company: str) -> dict:
	return frappe.db.get_value(
		"Company", company, ["cost_center", "default_expense_claim_payable_account"], as_dict=True
	)


# Form View APIs
@frappe.whitelist()
def get_doctype_fields(doctype: str) -> list[dict]:
	fields = frappe.get_meta(doctype).fields
	return [
		field
		for field in fields
		if field.fieldtype in SUPPORTED_FIELD_TYPES and field.fieldname != "amended_from"
	]


@frappe.whitelist()
def get_doctype_states(doctype: str) -> dict:
	states = frappe.get_meta(doctype).states
	return {state.title: state.color.lower() for state in states}


# File
@frappe.whitelist()
def get_attachments(dt: str, dn: str):
	from frappe.desk.form.load import get_attachments

	return get_attachments(dt, dn)


@frappe.whitelist()
def upload_base64_file(content, filename, dt=None, dn=None, fieldname=None):
	import base64
	import io
	from mimetypes import guess_type

	from PIL import Image, ImageOps

	from frappe.handler import ALLOWED_MIMETYPES

	decoded_content = base64.b64decode(content)
	content_type = guess_type(filename)[0]
	if content_type not in ALLOWED_MIMETYPES:
		frappe.throw(_("You can only upload JPG, PNG, PDF, TXT or Microsoft documents."))

	if content_type.startswith("image/jpeg"):
		# transpose the image according to the orientation tag, and remove the orientation data
		with Image.open(io.BytesIO(decoded_content)) as image:
			transpose_img = ImageOps.exif_transpose(image)
			# convert the image back to bytes
			file_content = io.BytesIO()
			transpose_img.save(file_content, format="JPEG")
			file_content = file_content.getvalue()
	else:
		file_content = decoded_content

	return frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": dt,
			"attached_to_name": dn,
			"attached_to_field": fieldname,
			"folder": "Home",
			"file_name": filename,
			"content": file_content,
			"is_private": 1,
		}
	).insert()


@frappe.whitelist()
def delete_attachment(filename: str):
	frappe.delete_doc("File", filename)


@frappe.whitelist()
def download_salary_slip(name: str):
	import base64

	from frappe.utils.print_format import download_pdf

	default_print_format = frappe.get_meta("Salary Slip").default_print_format or "Standard"

	try:
		download_pdf("Salary Slip", name, format=default_print_format)
	except Exception:
		frappe.throw(_("Failed to download Salary Slip PDF"))

	base64content = base64.b64encode(frappe.local.response.filecontent)
	content_type = frappe.local.response.type

	return f"data:{content_type};base64," + base64content.decode("utf-8")


# Workflow
@frappe.whitelist()
def get_workflow(doctype: str) -> dict:
	workflow = get_workflow_name(doctype)
	if not workflow:
		return frappe._dict()
	return frappe.get_doc("Workflow", workflow)


def get_workflow_state_field(doctype: str) -> str | None:
	workflow_name = get_workflow_name(doctype)
	if not workflow_name:
		return None

	override_status, workflow_state_field = frappe.db.get_value(
		"Workflow",
		workflow_name,
		["override_status", "workflow_state_field"],
	)
	# NOTE: checkbox labelled 'Don't Override Status' is named override_status hence the inverted logic
	if not override_status:
		return workflow_state_field
	return None


def get_allowed_states_for_workflow(workflow: dict, user_id: str) -> list[str]:
	user_roles = frappe.get_roles(user_id)
	return [transition.state for transition in workflow.transitions if transition.allowed in user_roles]


# Permissions
@frappe.whitelist()
def get_permitted_fields_for_write(doctype: str) -> list[str]:
	return get_permitted_fields(doctype, permission_type="write")


@frappe.whitelist(allow_guest=True)
def get_employee_status_breakdown():
    """Returns a breakdown of Employee status and docstatus counts for debugging."""
    data = frappe.db.sql("""
        SELECT TRIM(LOWER(status)) as status, docstatus, COUNT(*) as count
        FROM `tabEmployee`
        GROUP BY TRIM(LOWER(status)), docstatus
    """, as_dict=1)
    return data

@frappe.whitelist(allow_guest=True)
def get_active_employees_count() -> dict:
    """Returns the total count of active employees (robust: status=Active, case/space-insensitive, docstatus<2) as a dict for API compatibility"""
    try:
        count = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabEmployee`
            WHERE TRIM(LOWER(status)) = 'active' AND docstatus < 2
        """, as_list=1)[0][0]
        return {"message": count}
    except Exception as e:
        frappe.logger().error(f"Error in get_active_employees_count: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch employees count"))


@frappe.whitelist(allow_guest=True)
def get_gender_distribution() -> dict:
	"""Returns the count of male and female employees"""
	try:
		# Get total count for each gender
		gender_counts = frappe.db.sql("""
			SELECT 
				COALESCE(gender, 'Not Set') as gender,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY gender
		""", as_dict=1)

		# Initialize counts
		male_count = 0
		female_count = 0

		# Process the results
		for row in gender_counts:
			if row.gender.lower() == 'male':
				male_count = row.count
			elif row.gender.lower() == 'female':
				female_count = row.count

		return {
			"male": male_count,
			"female": female_count
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_gender_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch gender distribution"))


@frappe.whitelist(allow_guest=True)
def get_department_distribution() -> list:
	"""Returns department distribution for polar chart"""
	try:
		department_counts = frappe.db.sql("""
			SELECT 
				COALESCE(department, 'No Department') as department,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY department
			ORDER BY count DESC
			LIMIT 6
		""", as_dict=1)
		
		return department_counts
	except Exception as e:
		frappe.logger().error(f"Error in get_department_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch department distribution"))


@frappe.whitelist(allow_guest=True)
def get_branch_distribution() -> list:
	"""Returns branch distribution for polar chart"""
	try:
		branch_counts = frappe.db.sql("""
			SELECT 
				COALESCE(branch, 'No Branch') as branch,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY branch
			ORDER BY count DESC
			LIMIT 6
		""", as_dict=1)
		
		return branch_counts
	except Exception as e:
		frappe.logger().error(f"Error in get_branch_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch branch distribution"))


@frappe.whitelist(allow_guest=True)
def get_monthly_attendance_data() -> dict:
	"""Returns monthly attendance data for bar chart"""
	try:
		# Get current year
		from datetime import datetime
		current_year = datetime.now().year
		
		# Get attendance data for current year
		attendance_data = frappe.db.sql("""
			SELECT 
				MONTH(attendance_date) as month,
				COUNT(*) as total_days,
				SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_days,
				SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_days
			FROM `tabAttendance`
			WHERE YEAR(attendance_date) = %s
			GROUP BY MONTH(attendance_date)
			ORDER BY month
		""", (current_year,), as_dict=1)
		
		# Format data for chart
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
				 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		
		present_data = [0] * 12
		absent_data = [0] * 12
		
		for record in attendance_data:
			month_index = record.month - 1
			present_data[month_index] = record.present_days
			absent_data[month_index] = record.absent_days
		
		return {
			"months": months,
			"present": present_data,
			"absent": absent_data
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_monthly_attendance_data: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch monthly attendance data"))


@frappe.whitelist(allow_guest=True)
def get_leave_application_stats() -> dict:
	"""Returns leave application statistics for charts"""
	try:
		# Get current year
		from datetime import datetime
		current_year = datetime.now().year
		
		# Get leave applications for current year
		leave_stats = frappe.db.sql("""
			SELECT 
				MONTH(posting_date) as month,
				COUNT(*) as total_applications,
				SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved,
				SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
				SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as pending
			FROM `tabLeave Application`
			WHERE YEAR(posting_date) = %s
			GROUP BY MONTH(posting_date)
			ORDER BY month
		""", (current_year,), as_dict=1)
		
		# Format data for chart
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
				 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		
		approved_data = [0] * 12
		rejected_data = [0] * 12
		pending_data = [0] * 12
		
		for record in leave_stats:
			month_index = record.month - 1
			approved_data[month_index] = record.approved
			rejected_data[month_index] = record.rejected
			pending_data[month_index] = record.pending
		
		return {
			"months": months,
			"approved": approved_data,
			"rejected": rejected_data,
			"pending": pending_data
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_leave_application_stats: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch leave application statistics"))


@frappe.whitelist(allow_guest=True)
def get_hr_metrics() -> dict:
	"""Returns various HR metrics for progress bars and cards"""
	try:
		# Get total employees
		total_employees = frappe.db.count("Employee", {"status": "Active"})
		
		# Get employees by designation
		designation_counts = frappe.db.sql("""
			SELECT 
				COALESCE(designation, 'No Designation') as designation,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY designation
			ORDER BY count DESC
			LIMIT 5
		""", as_dict=1)
		
		# Get attendance today
		today_attendance = frappe.db.sql("""
			SELECT 
				COUNT(*) as total,
				SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present,
				SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent
			FROM `tabAttendance`
			WHERE attendance_date = CURDATE()
		""", as_dict=1)
		
		# Get leave applications this month (add Cancelled count)
		monthly_leaves = frappe.db.sql("""
			SELECT 
				COUNT(*) as total,
				SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved,
				SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
				SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as pending,
				SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled
			FROM `tabLeave Application`
			WHERE MONTH(posting_date) = MONTH(CURDATE())
			AND YEAR(posting_date) = YEAR(CURDATE())
		""", as_dict=1)
		
		return {
			"total_employees": total_employees,
			"designation_counts": designation_counts,
			"today_attendance": today_attendance[0] if today_attendance else {"total": 0, "present": 0, "absent": 0},
			"monthly_leaves": monthly_leaves[0] if monthly_leaves else {"total": 0, "approved": 0, "rejected": 0, "pending": 0, "cancelled": 0}
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_hr_metrics: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch HR metrics"))

@frappe.whitelist(allow_guest=True)
def get_employee_counts_by_branch():
    data = frappe.db.sql("""
        SELECT
            COALESCE(branch, 'No Branch') AS branch,
            COUNT(*) AS employee_count
        FROM `tabEmployee`
        WHERE status = 'Active'
        GROUP BY branch
        ORDER BY employee_count DESC
        LIMIT 10
    """, as_dict=1)

    return data

@frappe.whitelist(allow_guest=True)
def get_filtered_employees():
    """
    Returns employees with leave_approver = aalwadaey@i-aps.com,
    including their name, preferred_email, status, and designation.
    """
    employees = frappe.get_all(
        "Employee",
        fields=[
            "employee_name",
            "preferred_email",
            "status",
            "designation"
        ],
        filters={"leave_approver": "aalwadaey@i-aps.com"},
        limit=999999,
    )
    return employees

@frappe.whitelist(allow_guest=True)
def get_employees_approved_by_manager_count() -> int:
    """Returns the count of employees approved by manager (manager1_check=1)"""
    try:
        return frappe.db.count("Employee", {"manager1_check": 1})
    except Exception as e:
        frappe.logger().error(f"Error in get_employees_approved_by_manager_count: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch employees approved by manager count"))

@frappe.whitelist(allow_guest=True)
def get_employees_approved_by_manager_list() -> list:
    """Returns a list of employees approved by manager (manager1_check=1, docstatus<2) with key fields"""
    try:
        employees = frappe.get_all(
            "Employee",
            fields=[
                "name",
                "employee_name",
                "preferred_email",
                "status",
                "designation",
                "branch",
                "department",
                "company"
            ],
            filters={
                "manager1_check": 1,
                "docstatus": ["<", 2]
            },
            limit=999999,
        )
        return employees
    except Exception as e:
        frappe.logger().error(f"Error in get_employees_approved_by_manager_list: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch employees approved by manager list"))


@frappe.whitelist(allow_guest=True)
def get_new_hires_this_year() -> dict:
	"""Returns count of new hires for current year"""
	try:
		from datetime import datetime
		current_year = datetime.now().year
		start_of_year = f"{current_year}-01-01"
		
		count = frappe.db.sql("""
			SELECT COUNT(*) FROM `tabEmployee`
			WHERE date_of_joining >= %s
			AND status = 'Active'
		""", (start_of_year,), as_list=1)[0][0]
		
		return {"message": count}
	except Exception as e:
		frappe.logger().error(f"Error in get_new_hires_this_year: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch new hires count"))


@frappe.whitelist(allow_guest=True)
def get_enumerators_count() -> dict:
	"""Returns count of employees with 'Enumerator' in designation"""
	try:
		count = frappe.db.sql("""
			SELECT COUNT(*) FROM `tabEmployee`
			WHERE designation LIKE %s
			AND status = 'Active'
		""", ('%Enumerator%',), as_list=1)[0][0]
		
		return {"message": count}
	except Exception as e:
		frappe.logger().error(f"Error in get_enumerators_count: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch enumerators count"))


@frappe.whitelist(allow_guest=True)
def get_contract_employees_count() -> dict:
	"""Returns count of employees with employment type 'Contract'"""
	try:
		count = frappe.db.sql("""
			SELECT COUNT(*) FROM `tabEmployee`
			WHERE employment_type = 'Contract'
			AND status = 'Active'
		""", as_list=1)[0][0]
		
		return {"message": count}
	except Exception as e:
		frappe.logger().error(f"Error in get_contract_employees_count: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch contract employees count"))


@frappe.whitelist(allow_guest=True)
def get_all_number_cards_data() -> dict:
	"""Returns data for all Number Cards in the system"""
	try:
		# Get all Number Cards
		number_cards = frappe.get_all("Number Card", 
			fields=["name", "label", "document_type", "function", "filters_json", "dynamic_filters_json"],
			filters={"is_public": 1}
		)
		
		result = {}
		
		for card in number_cards:
			try:
				# Execute the Number Card logic
				value = execute_number_card(card)
				result[card.name] = {
					"label": card.label,
					"value": value,
					"document_type": card.document_type,
					"function": card.function
				}
			except Exception as e:
				frappe.logger().error(f"Error executing Number Card {card.name}: {str(e)}")
				result[card.name] = {
					"label": card.label,
					"value": 0,
					"error": str(e)
				}
		
		return result
	except Exception as e:
		frappe.logger().error(f"Error in get_all_number_cards_data: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch Number Cards data"))


def execute_number_card(card):
	"""Execute a Number Card and return its value"""
	try:
		# Parse filters
		filters = {}
		if card.filters_json:
			filters = frappe.parse_json(card.filters_json)
		
		# Parse dynamic filters
		dynamic_filters = {}
		if card.dynamic_filters_json:
			dynamic_filters = frappe.parse_json(card.dynamic_filters_json)
		
		# Merge filters
		all_filters = {}
		for filter_list in [filters, dynamic_filters]:
			for filter_item in filter_list:
				if len(filter_item) >= 4:
					doctype, field, operator, value = filter_item[:4]
					if operator == "=":
						all_filters[field] = value
					elif operator == ">=":
						all_filters[field] = [">=", value]
					elif operator == "like":
						all_filters[field] = ["like", value]
		
		# Execute the function
		if card.function == "Count":
			return frappe.db.count(card.document_type, all_filters)
		elif card.function == "Sum":
			# For sum, we need to specify the field to sum
			# This is a simplified version
			return frappe.db.count(card.document_type, all_filters)
		else:
			return frappe.db.count(card.document_type, all_filters)
			
	except Exception as e:
		frappe.logger().error(f"Error executing Number Card {card.name}: {str(e)}")
		return 0


@frappe.whitelist(allow_guest=True)
def get_specific_number_cards() -> dict:
	"""Returns data for specific Number Cards we need"""
	try:
		# Define the cards we want
		card_names = [
			"Total Employees",
			"New Hires (This Year)", 
			"Enumerators",
			"Contract Employees"
		]
		
		result = {}
		
		for card_name in card_names:
			try:
				# Get the Number Card
				card = frappe.get_doc("Number Card", card_name)
				value = execute_number_card(card)
				result[card_name] = {
					"label": card.label,
					"value": value
				}
			except frappe.DoesNotExistError:
				# Card doesn't exist, use fallback
				fallback_value = get_fallback_value(card_name)
				result[card_name] = {
					"label": card_name,
					"value": fallback_value
				}
			except Exception as e:
				frappe.logger().error(f"Error getting Number Card {card_name}: {str(e)}")
				fallback_value = get_fallback_value(card_name)
				result[card_name] = {
					"label": card_name,
					"value": fallback_value
				}
		
		return result
	except Exception as e:
		frappe.logger().error(f"Error in get_specific_number_cards: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch specific Number Cards data"))


def get_fallback_value(card_name):
	"""Get fallback value when Number Card doesn't exist"""
	try:
		if card_name == "Total Employees":
			return frappe.db.count("Employee", {"status": "Active"})
		elif card_name == "New Hires (This Year)":
			from datetime import datetime
			current_year = datetime.now().year
			start_of_year = f"{current_year}-01-01"
			return frappe.db.count("Employee", {
				"date_of_joining": [">=", start_of_year],
				"status": "Active"
			})
		elif card_name == "Enumerators":
			return frappe.db.count("Employee", {
				"designation": ["like", "%Enumerator%"],
				"status": "Active"
			})
		elif card_name == "Contract Employees":
			return frappe.db.count("Employee", {
				"employment_type": "Contract",
				"status": "Active"
			})
		else:
			return 0
	except Exception as e:
		frappe.logger().error(f"Error in get_fallback_value for {card_name}: {str(e)}")
		return 0

@frappe.whitelist(allow_guest=True)
def get_iaps_enumerators_count() -> dict:
    """Returns count of all records in the 'i-APS Enumerators' DocType"""
    try:
        count = frappe.db.count("i-APS Enumerators")
        return {"message": count}
    except Exception as e:
        frappe.logger().error(f"Error in get_iaps_enumerators_count: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        frappe.throw(_("Failed to fetch i-APS Enumerators count"))

@frappe.whitelist(allow_guest=True)
def get_enumerator_location_distribution():
    frappe.logger().info("API called: get_enumerator_location_distribution (hardcoded test)")
    return {"message": [
        {"location": "South", "count": 5},
        {"location": "North", "count": 3}
    ]}

@frappe.whitelist(allow_guest=True)
def get_leave_applications_by_type() -> dict:
	"""
	Returns leave application counts grouped by leave_type, and for each type, counts by status (Open, Approved, Rejected, Cancelled).
	"""
	try:
		results = {}
		stats = frappe.db.sql("""
			SELECT 
				leave_type,
				status,
				COUNT(*) as count
			FROM `tabLeave Application`
			GROUP BY leave_type, status
		""", as_dict=1)
		for row in stats:
			lt = row.leave_type or 'Unknown'
			if lt not in results:
				results[lt] = {s: 0 for s in ["Open", "Approved", "Rejected", "Cancelled"]}
			results[lt][row.status] = row.count
		return results
	except Exception as e:
		frappe.logger().error(f"Error in get_leave_applications_by_type: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		frappe.throw(_("Failed to fetch leave applications by type"))


# New Leave Management API Functions
@frappe.whitelist(allow_guest=True)
def get_leaves_by_status() -> list:
	"""
	Returns leave count by status for current month (Donut Chart)
	"""
	try:
		from datetime import datetime
		current_month = datetime.now().month
		current_year = datetime.now().year
		
		stats = frappe.db.sql("""
			SELECT 
				COALESCE(status, 'Unknown') as status,
				COUNT(*) as count
			FROM `tabLeave Application`
			WHERE MONTH(posting_date) = %s 
			AND YEAR(posting_date) = %s
			GROUP BY status
			ORDER BY count DESC
		""", (current_month, current_year), as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_leaves_by_status: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_leaves_per_month() -> list:
	"""
	Returns approved leaves per month for last 6 months (Line Chart)
	"""
	try:
		from datetime import datetime, timedelta
		
		# Get last 6 months
		current_date = datetime.now()
		months = []
		for i in range(5, -1, -1):  # 5 to 0 (6 months)
			date = current_date - timedelta(days=30*i)
			months.append((date.year, date.month))
		
		stats = []
		for year, month in months:
			count = frappe.db.sql("""
				SELECT COUNT(*) as count
				FROM `tabLeave Application`
				WHERE MONTH(posting_date) = %s 
				AND YEAR(posting_date) = %s
				AND status = 'Approved'
			""", (month, year), as_list=1)[0][0]
			
			month_name = datetime(year, month, 1).strftime('%b %Y')
			stats.append({
				"month": month_name,
				"count": count
			})
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_leaves_per_month: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_top_leave_types() -> list:
	"""
	Returns top leave types used this year (Bar Chart)
	"""
	try:
		from datetime import datetime
		current_year = datetime.now().year
		
		stats = frappe.db.sql("""
			SELECT 
				COALESCE(leave_type, 'Unknown') as leave_type,
				COUNT(*) as count
			FROM `tabLeave Application`
			WHERE YEAR(posting_date) = %s
			GROUP BY leave_type
			ORDER BY count DESC
			LIMIT 10
		""", (current_year,), as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_top_leave_types: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_leave_trend_by_department() -> list:
	"""
	Returns leave applications by department (Bar Chart)
	"""
	try:
		stats = frappe.db.sql("""
			SELECT 
				COALESCE(e.department, 'No Department') as department,
				COUNT(la.name) as count
			FROM `tabLeave Application` la
			LEFT JOIN `tabEmployee` e ON la.employee = e.name
			WHERE la.status != 'Cancelled'
			GROUP BY e.department
			ORDER BY count DESC
			LIMIT 10
		""", as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_leave_trend_by_department: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_active_employees_by_department() -> list:
	"""
	Returns active employees by department (Bar Chart)
	"""
	try:
		stats = frappe.db.sql("""
			SELECT 
				COALESCE(department, 'No Department') as department,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY department
			ORDER BY count DESC
			LIMIT 10
		""", as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_active_employees_by_department: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_daily_leave_data() -> list:
	"""
	Returns daily leave data for the last year (Line Chart)
	Based on the Daily Leave dashboard chart configuration
	"""
	try:
		from datetime import datetime, timedelta
		
		# Get data for the last year
		end_date = datetime.now()
		start_date = end_date - timedelta(days=365)
		
		# Get daily leave applications
		stats = frappe.db.sql("""
			SELECT 
				DATE(from_date) as date,
				COUNT(*) as count
			FROM `tabLeave Application`
			WHERE from_date >= %s 
			AND from_date <= %s
			AND status != 'Cancelled'
			GROUP BY DATE(from_date)
			ORDER BY date
		""", (start_date.date(), end_date.date()), as_dict=1)
		
		# Format dates for chart
		formatted_stats = []
		for record in stats:
			formatted_stats.append({
				"date": record.date.strftime('%Y-%m-%d'),
				"count": record.count
			})
		
		return formatted_stats
	except Exception as e:
		frappe.logger().error(f"Error in get_daily_leave_data: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_attrition_rate() -> dict:
	"""
	Returns employee attrition rate for current year
	"""
	try:
		from datetime import datetime
		current_year = datetime.now().year
		
		# Get total employees at start of year
		start_of_year = f"{current_year}-01-01"
		employees_start = frappe.db.count("Employee", {
			"status": "Active",
			"date_of_joining": ["<=", start_of_year]
		})
		
		# Get employees who left this year
		employees_left = frappe.db.count("Employee", {
			"status": "Left",
			"relieving_date": [">=", start_of_year]
		})
		
		# Get new hires this year
		new_hires = frappe.db.count("Employee", {
			"status": "Active",
			"date_of_joining": [">=", start_of_year]
		})
		
		# Calculate attrition rate
		attrition_rate = (employees_left / employees_start * 100) if employees_start > 0 else 0
		
		return {
			"attrition_rate": round(attrition_rate, 2),
			"employees_left": employees_left,
			"new_hires": new_hires,
			"total_start": employees_start
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_attrition_rate: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return {"attrition_rate": 0, "employees_left": 0, "new_hires": 0, "total_start": 0}


@frappe.whitelist(allow_guest=True)
def get_employee_salary_distribution() -> list:
	"""
	Returns employee salary distribution by ranges
	"""
	try:
		stats = frappe.db.sql("""
			SELECT 
				CASE 
					WHEN base < 1000 THEN 'Under 1K'
					WHEN base < 2000 THEN '1K - 2K'
					WHEN base < 3000 THEN '2K - 3K'
					WHEN base < 5000 THEN '3K - 5K'
					WHEN base < 10000 THEN '5K - 10K'
					ELSE 'Over 10K'
				END as salary_range,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active' AND base > 0
			GROUP BY salary_range
			ORDER BY 
				CASE salary_range
					WHEN 'Under 1K' THEN 1
					WHEN '1K - 2K' THEN 2
					WHEN '2K - 3K' THEN 3
					WHEN '3K - 5K' THEN 4
					WHEN '5K - 10K' THEN 5
					ELSE 6
				END
		""", as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_salary_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_tenure_distribution() -> list:
	"""
	Returns employee tenure distribution
	"""
	try:
		stats = frappe.db.sql("""
			SELECT 
				CASE 
					WHEN DATEDIFF(CURDATE(), date_of_joining) < 365 THEN 'Less than 1 year'
					WHEN DATEDIFF(CURDATE(), date_of_joining) < 730 THEN '1-2 years'
					WHEN DATEDIFF(CURDATE(), date_of_joining) < 1095 THEN '2-3 years'
					WHEN DATEDIFF(CURDATE(), date_of_joining) < 1825 THEN '3-5 years'
					ELSE 'Over 5 years'
				END as tenure_range,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY tenure_range
			ORDER BY 
				CASE tenure_range
					WHEN 'Less than 1 year' THEN 1
					WHEN '1-2 years' THEN 2
					WHEN '2-3 years' THEN 3
					WHEN '3-5 years' THEN 4
					ELSE 5
				END
		""", as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_tenure_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_performance_metrics() -> dict:
	"""
	Returns employee performance metrics
	"""
	try:
		# Get employees with performance ratings
		performance_stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_employees,
				SUM(CASE WHEN performance_rating >= 4 THEN 1 ELSE 0 END) as high_performers,
				SUM(CASE WHEN performance_rating >= 3 AND performance_rating < 4 THEN 1 ELSE 0 END) as good_performers,
				SUM(CASE WHEN performance_rating < 3 THEN 1 ELSE 0 END) as needs_improvement
			FROM `tabEmployee`
			WHERE status = 'Active' AND performance_rating IS NOT NULL
		""", as_dict=1)
		
		if performance_stats:
			stats = performance_stats[0]
			total = stats.total_employees or 0
			
			return {
				"total_employees": total,
				"high_performers": stats.high_performers or 0,
				"good_performers": stats.good_performers or 0,
				"needs_improvement": stats.needs_improvement or 0,
				"high_performance_rate": round((stats.high_performers / total * 100) if total > 0 else 0, 2)
			}
		
		return {
			"total_employees": 0,
			"high_performers": 0,
			"good_performers": 0,
			"needs_improvement": 0,
			"high_performance_rate": 0
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_performance_metrics: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return {
			"total_employees": 0,
			"high_performers": 0,
			"good_performers": 0,
			"needs_improvement": 0,
			"high_performance_rate": 0
		}


@frappe.whitelist(allow_guest=True)
def get_employee_training_data() -> list:
	"""
	Returns employee training and development data
	"""
	try:
		stats = frappe.db.sql("""
			SELECT 
				COALESCE(training_program, 'No Training') as training_program,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY training_program
			ORDER BY count DESC
			LIMIT 10
		""", as_dict=1)
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_training_data: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_attendance_trend() -> list:
	"""
	Returns employee attendance trend for last 6 months
	"""
	try:
		from datetime import datetime, timedelta
		
		# Get last 6 months
		current_date = datetime.now()
		months = []
		for i in range(5, -1, -1):
			date = current_date - timedelta(days=30*i)
			months.append((date.year, date.month))
		
		stats = []
		for year, month in months:
			# Get attendance data for the month
			attendance_count = frappe.db.sql("""
				SELECT COUNT(*) as count
				FROM `tabAttendance`
				WHERE MONTH(attendance_date) = %s 
				AND YEAR(attendance_date) = %s
				AND status = 'Present'
			""", (month, year), as_list=1)[0][0]
			
			month_name = datetime(year, month, 1).strftime('%b %Y')
			stats.append({
				"month": month_name,
				"attendance_count": attendance_count
			})
		
		return stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_attendance_trend: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_expense_analysis() -> dict:
	"""
	Returns employee expense analysis
	"""
	try:
		from datetime import datetime
		current_year = datetime.now().year
		
		# Get expense claims data
		expense_stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_claims,
				SUM(total_claimed_amount) as total_amount,
				AVG(total_claimed_amount) as avg_amount,
				SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved_claims,
				SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected_claims
			FROM `tabExpense Claim`
			WHERE YEAR(expense_claim_date) = %s
		""", (current_year,), as_dict=1)
		
		if expense_stats:
			stats = expense_stats[0]
			return {
				"total_claims": stats.total_claims or 0,
				"total_amount": float(stats.total_amount or 0),
				"avg_amount": float(stats.avg_amount or 0),
				"approved_claims": stats.approved_claims or 0,
				"rejected_claims": stats.rejected_claims or 0,
				"approval_rate": round((stats.approved_claims / stats.total_claims * 100) if stats.total_claims > 0 else 0, 2)
			}
		
		return {
			"total_claims": 0,
			"total_amount": 0,
			"avg_amount": 0,
			"approved_claims": 0,
			"rejected_claims": 0,
			"approval_rate": 0
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_expense_analysis: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return {
			"total_claims": 0,
			"total_amount": 0,
			"avg_amount": 0,
			"approved_claims": 0,
			"rejected_claims": 0,
			"approval_rate": 0
		}


@frappe.whitelist(allow_guest=True)
def get_employee_workflow_stats() -> dict:
	"""
	Returns employee workflow statistics
	"""
	try:
		# Get workflow statistics
		workflow_stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_employees,
				SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_employees,
				SUM(CASE WHEN status = 'Inactive' THEN 1 ELSE 0 END) as inactive_employees,
				SUM(CASE WHEN status = 'Left' THEN 1 ELSE 0 END) as left_employees,
				SUM(CASE WHEN status = 'Suspended' THEN 1 ELSE 0 END) as suspended_employees
			FROM `tabEmployee`
		""", as_dict=1)
		
		if workflow_stats:
			stats = workflow_stats[0]
			return {
				"total_employees": stats.total_employees or 0,
				"active_employees": stats.active_employees or 0,
				"inactive_employees": stats.inactive_employees or 0,
				"left_employees": stats.left_employees or 0,
				"suspended_employees": stats.suspended_employees or 0,
				"active_rate": round((stats.active_employees / stats.total_employees * 100) if stats.total_employees > 0 else 0, 2)
			}
		
		return {
			"total_employees": 0,
			"active_employees": 0,
			"inactive_employees": 0,
			"left_employees": 0,
			"suspended_employees": 0,
			"active_rate": 0
		}
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_workflow_stats: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return {
			"total_employees": 0,
			"active_employees": 0,
			"inactive_employees": 0,
			"left_employees": 0,
			"suspended_employees": 0,
			"active_rate": 0
		}


@frappe.whitelist(allow_guest=True)
def get_employee_blood_group_distribution() -> list:
	"""
	Returns employee blood group distribution
	"""
	try:
		blood_group_stats = frappe.db.sql("""
			SELECT 
				COALESCE(blood_group, 'Not Set') as blood_group,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY blood_group
			ORDER BY count DESC
		""", as_dict=1)
		
		return blood_group_stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_blood_group_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_marital_status_distribution() -> list:
	"""
	Returns employee marital status distribution
	"""
	try:
		marital_stats = frappe.db.sql("""
			SELECT 
				COALESCE(marital_status, 'Not Set') as marital_status,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active'
			GROUP BY marital_status
			ORDER BY count DESC
		""", as_dict=1)
		
		return marital_stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_marital_status_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_joining_year_distribution() -> list:
	"""
	Returns employee joining year distribution
	"""
	try:
		joining_year_stats = frappe.db.sql("""
			SELECT 
				YEAR(date_of_joining) as joining_year,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active' AND date_of_joining IS NOT NULL
			GROUP BY YEAR(date_of_joining)
			ORDER BY joining_year DESC
		""", as_dict=1)
		
		return joining_year_stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_joining_year_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


@frappe.whitelist(allow_guest=True)
def get_employee_age_distribution() -> list:
	"""
	Returns employee age distribution
	"""
	try:
		age_stats = frappe.db.sql("""
			SELECT 
				CASE 
					WHEN TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) < 25 THEN '18-24'
					WHEN TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) < 35 THEN '25-34'
					WHEN TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) < 45 THEN '35-44'
					WHEN TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) < 55 THEN '45-54'
					ELSE '55+'
				END as age_group,
				COUNT(*) as count
			FROM `tabEmployee`
			WHERE status = 'Active' AND date_of_birth IS NOT NULL
			GROUP BY age_group
			ORDER BY 
				CASE age_group
					WHEN '18-24' THEN 1
					WHEN '25-34' THEN 2
					WHEN '35-44' THEN 3
					WHEN '45-54' THEN 4
					WHEN '55+' THEN 5
				END
		""", as_dict=1)
		
		return age_stats
	except Exception as e:
		frappe.logger().error(f"Error in get_employee_age_distribution: {str(e)}")
		frappe.logger().error(frappe.get_traceback())
		return []


# Custom Doctypes API Functions for Work Mission Request and Petty Cash

@frappe.whitelist(allow_guest=True)
def get_work_mission_requests(filters=None, fields=None, limit=None):
	"""
	Fetch all Work Mission Request records with their details using SQL
	"""
	try:
		# Build SQL query
		limit_clause = f"LIMIT {limit}" if limit else ""
		
		records = frappe.db.sql(f"""
			SELECT 
				name, naming_series, workflow_state, mission_type, 
				employee, employee_name, date, posting_date, place, 
				street, subject, notes, progress, superior, 
				transportation_wage, operation, finance, price, 
				name1, sign, amended_from, creation, modified, 
				owner, modified_by, docstatus
			FROM `tabWork Mission Request`
			ORDER BY creation DESC
			{limit_clause}
		""", as_dict=True)
		
		return {
			'success': True,
			'data': records,
			'count': len(records),
			'message': f'Successfully fetched {len(records)} Work Mission Request records'
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_work_mission_requests: {str(e)}")
		return {
			'success': False,
			'error': str(e),
			'message': 'Failed to fetch Work Mission Request records'
		}


@frappe.whitelist(allow_guest=True)
def get_petty_cash_records(filters=None, fields=None, limit=None):
	"""
	Fetch all Petty Cash records with their details and child table data using SQL
	"""
	try:
		# Build SQL query for main records
		limit_clause = f"LIMIT {limit}" if limit else ""
		
		records = frappe.db.sql(f"""
			SELECT 
				name, naming_series, no, received_date, statement,
				total_amount, total_transportations, total_phones_and_internet,
				total_utilities, total_hospitality_and_puffah, total_fuel,
				total_stationery, total_guards, total_others,
				previous_balance, last_reimbursement_transferred, returns_amounts,
				total_amount_of_petty_cash, amount_expenses_of_petty_cash,
				remaining_amount_of_petty_cash, amount_reimbursement_of_petty_cash,
				received_the_amounts, invoices_and_purchase_orders, amended_from,
				creation, modified, owner, modified_by, docstatus
			FROM `tabPetty Cash`
			ORDER BY creation DESC
			{limit_clause}
		""", as_dict=True)
		
		# Get child table data for each record
		for record in records:
			details = frappe.db.sql("""
				SELECT 
					statement, date, amount, transportations, phones_and_net,
					utilities, hospitality_and_puffah, fuel, stationery,
					guards, others, remark
				FROM `tabPetty Cash Table`
				WHERE parent = %s
				ORDER BY idx
			""", (record.name,), as_dict=True)
			record['details'] = details
		
		return {
			'success': True,
			'data': records,
			'count': len(records),
			'message': f'Successfully fetched {len(records)} Petty Cash records'
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_petty_cash_records: {str(e)}")
		return {
			'success': False,
			'error': str(e),
			'message': 'Failed to fetch Petty Cash records'
		}


@frappe.whitelist(allow_guest=True)
def get_combined_dashboard_data():
	"""
	Get combined dashboard data for both doctypes
	"""
	try:
		# Get Work Mission Request summary
		wmr_total = frappe.db.count('Work Mission Request')
		wmr_status_counts = frappe.db.sql("""
			SELECT workflow_state, COUNT(*) as count
			FROM `tabWork Mission Request`
			GROUP BY workflow_state
		""", as_dict=True)
		
		# Get Petty Cash summary
		pc_total = frappe.db.count('Petty Cash')
		pc_totals = frappe.db.sql("""
			SELECT 
				SUM(total_amount) as total_amount,
				SUM(remaining_amount_of_petty_cash) as total_remaining
			FROM `tabPetty Cash`
		""", as_dict=True)
		
		return {
			'success': True,
			'data': {
				'work_mission_requests': {
					'total_count': wmr_total,
					'status_distribution': wmr_status_counts
				},
				'petty_cash': {
					'total_count': pc_total,
					'totals': pc_totals[0] if pc_totals else {}
				}
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



