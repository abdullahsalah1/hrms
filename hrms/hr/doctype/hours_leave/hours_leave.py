# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day, getdate, now_datetime, time_diff_in_hours
from datetime import datetime

@frappe.whitelist()
def get_uncalculated_records(employee):
	records = frappe.get_list(
		"Hours Leave",
		filters={
			"employee": employee,
			"docstatus": ["<", 2],
			"leave_balance": ["in", ["", None]],
			"counted_in_leave": ["!=", 1]
		},
		fields=["name", "date", "total_time"],
		order_by="creation asc"
	)
	return records

class HoursLeave(Document):
	def validate(self):
		self.validate_times()
		self.calculate_total_time()
		self.validate_total_hours()
		self.validate_allowed_hour_increments()
		
	def on_update(self):
		self.process_accumulated_hours()
		
	def before_save(self):
		self.set_balance_before()
		
	def validate_times(self):
		if self.from_time and self.to_time:
			# Normalize both times to HH:MM:00 (seconds always 00)
			for fieldname in ['from_time', 'to_time']:
				value = getattr(self, fieldname)
				parts = value.split(':')
				if len(parts) == 2:
					# Add seconds if missing
					value = f"{parts[0]}:{parts[1]}:00"
				elif len(parts) == 3:
					# Force seconds to 00
					value = f"{parts[0]}:{parts[1]}:00"
				else:
					frappe.throw(f"{fieldname.replace('_', ' ').title()} must be in HH:MM or HH:MM:SS format.")
				setattr(self, fieldname, value)
			from_time = datetime.strptime(self.from_time, "%H:%M:%S")
			to_time = datetime.strptime(self.to_time, "%H:%M:%S")
			if to_time < from_time:
				frappe.throw("⚠️ The 'To Time' cannot be earlier than 'From Time'.")
				
	def calculate_total_time(self):
		if self.from_time and self.to_time:
			# Always use seconds=00 for calculation
			from_time = datetime.strptime(self.from_time, "%H:%M:%S")
			to_time = datetime.strptime(self.to_time, "%H:%M:%S")
			hours = (to_time - from_time).total_seconds() / 3600
			self.total_time = round(hours, 2)
			
	def set_balance_before(self):
		if not self.employee:
			self.balance_before = 0
			return

		# Only include uncalculated records (counted_in_leave != 1)
		records = frappe.get_list(
			"Hours Leave",
			filters={
				"employee": self.employee,
				"docstatus": ["<", 2],
				"leave_balance": ["in", ["", None]],
				"counted_in_leave": ["!=", 1],
				"name": ["!=", self.name]  # Exclude current document
			},
			fields=["total_time"],
			order_by="creation asc"
		)

		# Sum all uncalculated previous records
		total = 0
		for rec in records:
			try:
				time = float(rec.total_time) if rec.total_time is not None else 0
			except (ValueError, TypeError):
				time = 0
			total += time
		self.balance_before = total

	def validate_total_hours(self):
		# Only consider uncalculated records
		records = frappe.get_list(
			"Hours Leave",
			filters={
				"employee": self.employee,
				"docstatus": ["<", 2],
				"leave_balance": ["in", ["", None]],
				"counted_in_leave": ["!=", 1],
				"is_calculated": ["!=", 1]
			},
			fields=["name", "date", "total_time"],
			order_by="creation asc"
		)

		# Only add the current record if it is not already marked as calculated
		if not self.is_calculated and not any(rec["name"] == self.name for rec in records):
			records.append({
				"name": self.name,
				"date": self.date,
				"total_time": self.total_time
			})

		max_limit = 4
		total_hours = sum(float(rec["total_time"] or 0) for rec in records)

		if total_hours > max_limit:
			frappe.throw(
				f"You cannot take more than {max_limit} hours per day, check your previous hour leave records.",
				title="Error"
			)
		# If less than or equal to 4, allow saving as a new uncalculated record

	def process_accumulated_hours(self):
		if not self.date:
			return
		# Change accumulation period to yearly
		year = self.date.year if hasattr(self.date, 'year') else int(str(self.date)[:4])
		year_start = f"{year}-01-01"
		year_end = f"{year}-12-31"
		records = frappe.get_list(
			"Hours Leave",
			filters={
				"employee": self.employee,
				"docstatus": ["<", 2],
				"date": ["between", [year_start, year_end]],
				"counted_in_leave": ["!=", 1],
				"leave_balance": ["in", ["", None]]
			},
			fields=["name", "date", "total_time"],
			order_by="creation asc"
		)
		if not records:
			return
		total_hours = 0
		records_to_update = []
		leave_details = []
		considered_records = set()
		for record in records:
			if record.name in considered_records:
				continue
			try:
				time = float(record.total_time) if record.total_time is not None else 0
			except (ValueError, TypeError):
				time = 0
			total_hours += time
			records_to_update.append(record.name)
			leave_details.append(f"{record.date}: {time} hours")
			considered_records.add(record.name)
			if total_hours >= 4:
				break
		if total_hours >= 4:
			description_text = f"Leave for accumulated hours:\n{chr(10).join(leave_details)}\nTotal: {total_hours} hours"
			try:
				leave_application = frappe.get_doc({
					"doctype": "Leave Application",
					"employee": self.employee,
					"employee_name": self.employee_name,
					"leave_type": "Annual Leave",
					"from_date": getdate(),
					"to_date": getdate(),
					"description": description_text,
					"half_day": 1,
					"status": "Approved"
				})
				leave_application.insert()
				for record_name in records_to_update:
					frappe.db.set_value(
						"Hours Leave",
						record_name,
						{
							"counted_in_leave": 1,
							"leave_balance": "Approved",
							"is_calculated": 1
						},
						update_modified=False
					)
				frappe.msgprint("Leave Application created successfully!")
			except Exception as e:
				frappe.msgprint("Error creating Leave Application")
				frappe.log_error(f"Error in Hours Leave processing: {str(e)}")

	def validate_allowed_hour_increments(self):
		allowed_increments = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
		try:
			value = round(float(self.total_time), 2)
		except (ValueError, TypeError):
			frappe.throw(f"Invalid leave duration: {self.total_time}", title="Invalid Leave Duration")
		if value not in allowed_increments:
			frappe.throw(
				f"You can only request leave for 0.5, 1, 1.5, 2, 2.5, 3, 3.5, or 4 hours.🚫 Your request: {self.total_time} hours.",
				title="Invalid Leave Duration"
			)
