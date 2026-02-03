// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hours Leave', {
	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "hrms.hr.doctype.hours_leave.hours_leave.get_uncalculated_records",
				args: { employee: frm.doc.employee },
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						let html = "<ul>";
						r.message.forEach(function(rec) {
							html += `<li>${rec.date}: ${rec.total_time || 0} hours (Record: ${rec.name})</li>`;
						});
						html += "<ul style='color:rgb(4, 0, 20); font-size: 2px;'>";
						frm.set_df_property("uncalculated_records", "options", html);
					} else {
						frm.set_df_property("uncalculated_records", "options", "<h3 style='color:rgb(4, 0, 20);'>you do not have recorded hours 😊</h3>");
					}
				}
			});
		} else {
			frm.set_df_property("uncalculated_records", "options", "<h1>No employee selected.</h1>");
		}
	},

	refresh: function(frm) {
		// Also update on refresh if employee is already set
		if (frm.doc.employee) {
			frm.events.employee(frm);
		}
	}
});
