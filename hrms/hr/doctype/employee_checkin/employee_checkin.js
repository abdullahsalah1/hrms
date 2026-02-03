// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Checkin", {
	refresh: function(frm) {
		evaluate_late_time(frm);
		if (frm.doc.offshift) {
			frm.dashboard.set_headline(
				__(
					"This check-in is outside assigned shift hours and will not be considered for attendance. If a shift is assigned, adjust its time window and Fetch Shift again.",
				),
			);
		}
		if (!frm.doc.__islocal) frm.trigger("add_fetch_shift_button");

		frappe.db.get_single_value(
			"HR Settings",
			"allow_geolocation_tracking",
		).then((allow_geolocation_tracking) => {
			if (!allow_geolocation_tracking) {
				hide_field(["fetch_geolocation", "latitude", "longitude", "geolocation"]);
				return;
			}
		});
	},

	time: function(frm) {
		evaluate_late_time(frm);
	},

	log_type: function(frm) {
		evaluate_late_time(frm);
	},

	fetch_geolocation: (frm) => {
		hrms.fetch_geolocation(frm);
	},

	create_hours_leave_btn: function(frm) {
		frappe.call({
			method: "hrms.hr.doctype.employee_checkin.employee_checkin.create_hours_leave_from_checkin",
			args: {
				checkin_name: frm.doc.name
			},
			freeze: true,
			freeze_message: __("Creating Hours Leave..."),
			callback: function(r) {
				if (r.exc) {
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Hours Leave: {0}", [r.exc]),
						indicator: "red"
					});
				} else {
					frappe.msgprint({
						title: __("Success"),
						message: __("Hours Leave created successfully: {0}", [r.message]),
						indicator: "green"
					});
					// Refresh the form to show any updates
					frm.refresh();
				}
			}
		});
	},

	add_fetch_shift_button(frm) {
		if (frm.doc.attendace) return;
		frm.add_custom_button(__("Fetch Shift"), function () {
			frappe.call({
				method: "fetch_shift",
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Fetching Shift"),
				callback: function () {
					if (frm.doc.shift) {
						frappe.show_alert({
							message: __("Shift has been successfully updated to {0}.", [
								frm.doc.shift,
							]),
							indicator: "green",
						});
						frm.dirty();
						frm.save();
					} else {
						frappe.show_alert({
							message: __("No valid shift found for log time"),
							indicator: "orange",
						});
					}
				},
			});
		});
	},
});

function evaluate_late_time(frm) {
	if (frm.doc.time && frm.doc.log_type) {
		let timeObj = frappe.datetime.str_to_obj(frm.doc.time);
		let hours = timeObj.getHours();
		let minutes = timeObj.getMinutes();
		if (frm.doc.log_type === 'IN' && (hours > 8 || (hours === 8 && minutes >= 35))) {
			frm.set_value('late_time', 'Yes');
		} else {
			frm.set_value('late_time', 'No');
		}
	} else {
		frm.set_value('late_time', 'No');
	}
}
