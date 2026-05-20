
frappe.ui.form.on('Leave Application', {
    refresh: function (frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: {
                        user_id: frappe.session.user,
                        status: "Active"
                    },
                    fieldname: "name"
                },
                callback: function (r) {
                    if (r.message && r.message.name) {
                        frm.set_value('employee', r.message.name);
                    }
                }
            });
        }

        // Restrict Status field for non-approvers
        if (!frm.is_new()) {
            let is_approver = frm.doc.leave_approver && frappe.session.user === frm.doc.leave_approver;
            let has_hr_role = frappe.user.has_role('HR Manager') || frappe.user.has_role('System Manager') || frappe.user.has_role('Leave Approver');

            if (!is_approver && !has_hr_role) {
                frm.set_df_property('status', 'read_only', 1);
            }
        } else {
            // On new form, status is Open and should be read-only for applicant
            frm.set_df_property('status', 'read_only', 1);
        }
    }
});
