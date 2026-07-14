frappe.ui.form.on("Leave Policy Assignment", {
	refresh(frm) {
		set_joining_date_work_year(frm);
	},

	employee(frm) {
		set_joining_date_work_year(frm);
	},

	assignment_based_on(frm) {
		set_joining_date_work_year(frm);
	},
});

function set_joining_date_work_year(frm) {
	if (frm.doc.assignment_based_on !== "Joining Date" || !frm.doc.employee) {
		return;
	}

	frappe.call({
		method: "law_management.hr.leave_policy_assignment.get_joining_date_work_year",
		args: {
			employee: frm.doc.employee,
		},
		callback(r) {
			if (!r.message) {
				return;
			}

			frm.set_value("effective_from", r.message.effective_from);
			frm.set_value("effective_to", r.message.effective_to);
		},
	});
}
