// Copyright (c) 2025, Tbest and contributors
// For license information, please see license.txt

const STANDARD_BILLING_RATES_USD = {
    "Partner": 250,
    "Senior Associate": 230,
    "Associate": 200,
    "Junior Associate": 150
};

frappe.ui.form.on("Case", {
    setup(frm) {
        frm.set_query("currency", function () {
            return {
                filters: {
                    enabled: 1
                }
            };
        });

        frm.set_query("case_lead", function () {
            return {
                query: "law_management.law_management.doctype.case.case.get_lawyer_users"
            };
        });
    },

    onload(frm) {
        if (frm.is_new() && !frm.doc.currency) {
            frm.set_value("currency", "USD");
        }
    },

    refresh(frm) {
        // Show button for Flat Fee (Milestones OR Upfront/Completion)
        // Billing logic removed as per new Legal Bill workflow

        // Filter "Assign To" Sidebar to only show Case Members
        // Logic moved to global patch below

        // Filter Team Members to only show Legal Team
        frm.set_query("user", "team_members", function () {
            return {
                query: "law_management.law_management.doctype.case.case.get_legal_team_users"
            };
        });

        // Make Time Log User field Read-only
        frm.fields_dict['time_logs'].grid.update_docfield_property('user', 'read_only', 1);

        // Retainer Schedule Generation Button
        if (frm.doc.billing_type === "Retainer") {
            frm.fields_dict['generate_retainer_schedule_btn'].$wrapper.find('button').off("click").on('click', () => {
                frm.call({
                    method: "generate_retainer_schedule",
                    doc: frm.doc,
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            frm.set_value("retainer_schedules", r.message);

                            // Determine End Date from the last row if exists
                            if (r.message.length > 0) {
                                let last_row = r.message[r.message.length - 1];
                                frm.set_value("payment_end_date", last_row.end_date);
                            }

                            frappe.msgprint(__("Retainer Schedule Generated"));
                        }
                    }
                });
            });
        }


        // Create Invoice Button
        frm.add_custom_button(__('Create Invoice'), function () {
            if (frm.is_dirty()) {
                frappe.msgprint(__("Please save the Case before creating an invoice so the latest time logs and retainer usage are included."));
                return;
            }

            if (frm.doc.billing_type === "Retainer") {
                // Retainer Invoice Logic
                if (!frm.doc.retainer_schedules || frm.doc.retainer_schedules.length === 0) {
                    frappe.msgprint(__("Please Generate Retainer Schedule first."));
                    return;
                }

                let options = frm.doc.retainer_schedules.map(d => {
                    return {
                        label: `${d.schedule_name} (${d.start_date} - ${d.end_date}) : ${format_currency(d.amount, frm.doc.currency || "USD")}`,
                        value: d.schedule_name
                    }
                });

                let d = new frappe.ui.Dialog({
                    title: 'Create Retainer Invoice',
                    fields: [
                        {
                            label: 'Select Period',
                            fieldname: 'schedule_name',
                            fieldtype: 'Select',
                            options: options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Create',
                    primary_action(values) {
                        frm.call({
                            method: "law_management.law_management.doctype.case.case.create_retainer_invoice",
                            args: {
                                case_name: frm.doc.name,
                                schedule_name: values.schedule_name
                            },
                            freeze: true,
                            callback: function (r) {
                                if (!r.exc && r.message) {
                                    d.hide();
                                    frappe.set_route("Form", "Legal Bill", r.message);
                                }
                            }
                        });
                    }
                });
                d.show();

            } else if (frm.doc.billing_type === "Flat Fee" && frm.doc.payment_structure === "Milestones") {
                // Milestone Invoice Logic
                if (!frm.doc.milestones || frm.doc.milestones.length === 0) {
                    frappe.msgprint(__("No Milestones defined."));
                    return;
                }

                let options = frm.doc.milestones.map(m => {
                    return {
                        label: `${m.milestone_name} : ${format_currency(m.amount, frm.doc.currency || "USD")}`,
                        value: m.milestone_name
                    }
                });

                let d = new frappe.ui.Dialog({
                    title: 'Create Milestone Invoice',
                    fields: [
                        {
                            label: 'Select Milestone',
                            fieldname: 'milestone_name',
                            fieldtype: 'Select',
                            options: options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Create',
                    primary_action(values) {
                        frm.call({
                            method: "law_management.law_management.doctype.case.case.create_milestone_invoice",
                            args: {
                                case_name: frm.doc.name,
                                milestone_name: values.milestone_name
                            },
                            freeze: true,
                            callback: function (r) {
                                if (!r.exc && r.message) {
                                    d.hide();
                                    frappe.set_route("Form", "Legal Bill", r.message);
                                }
                            }
                        });
                    }
                });
                d.show();

            } else {
                // Standard Invoice Logic (Hourly, Flat Fee Upfront etc)
                frappe.new_doc('Legal Bill', {
                    case_reference: frm.doc.name,
                    customer: frm.doc.client,
                    currency: frm.doc.currency || "USD"
                });
            }
        });

        // Add "Export Timesheets" button
        if (frm.doc.time_logs && frm.doc.time_logs.length > 0) {
            frm.add_custom_button(__('Export Timesheets'), function () {

                let export_csv = function (logs, period_name) {
                    if (!logs || logs.length === 0) {
                        frappe.msgprint("No timesheets found for selection.");
                        return;
                    }
                    let csvContent = "Date,User,Activity Type,Hours,Minutes,Calculated Hours,Description\n";

                    logs.forEach(function (row) {
                        let date = row.date || "";
                        let user = row.user || "";
                        let activity = row.activity_type || "";
                        let hours = row.log_hours || 0;
                        let minutes = row.log_minutes || 0;
                        let calculated_hours = (hours + (minutes / 60)).toFixed(2);
                        let description = (row.description || "").replace(/,/g, " "); // Basic CSV escape

                        let rowString = [date, user, activity, hours, minutes, calculated_hours, description].join(",");
                        csvContent += rowString + "\n";
                    });

                    let blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                    let link = document.createElement("a");
                    let url = URL.createObjectURL(blob);
                    link.setAttribute("href", url);
                    link.setAttribute("download", `Timesheets_${frm.doc.case_title || "Case"}_${period_name || "All"}.csv`);
                    link.style.visibility = 'hidden';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                };

                if (frm.doc.billing_type === "Retainer" && frm.doc.retainer_schedules && frm.doc.retainer_schedules.length > 0) {
                    let options = [
                        { label: "All Periods", value: "All" }
                    ];

                    frm.doc.retainer_schedules.forEach(d => {
                        options.push({
                            label: `${d.schedule_name} (${d.start_date} - ${d.end_date})`,
                            value: d.schedule_name
                        });
                    });

                    let d = new frappe.ui.Dialog({
                        title: 'Export Timesheets',
                        fields: [
                            {
                                label: 'Select Period',
                                fieldname: 'schedule_name',
                                fieldtype: 'Select',
                                options: options,
                                default: "All",
                                reqd: 1
                            }
                        ],
                        primary_action_label: 'Export',
                        primary_action(values) {
                            d.hide();
                            if (values.schedule_name === "All") {
                                export_csv(frm.doc.time_logs, "All");
                            } else {
                                let schedule = frm.doc.retainer_schedules.find(s => s.schedule_name === values.schedule_name);
                                if (schedule) {
                                    let filtered_logs = frm.doc.time_logs.filter(log => {
                                        return log.date >= schedule.start_date && log.date <= schedule.end_date;
                                    });
                                    export_csv(filtered_logs, schedule.schedule_name);
                                }
                            }
                        }
                    });
                    d.show();
                } else {
                    // Default behavior
                    export_csv(frm.doc.time_logs, "All");
                }
            });
        }
    },
});

frappe.ui.form.on('Case Time Log', {
    time_logs_add: function (frm, cdt, cdn) {
        if (!is_case_team_member(frm, frappe.session.user)) {
            remove_time_log_row(frm, cdt, cdn);
            frappe.msgprint(__("Only case team members can log time on this case."));
            return;
        }

        // Auto-fill User with current session user
        frappe.model.set_value(cdt, cdn, 'user', frappe.session.user);
    }
});

frappe.ui.form.on('Case Member', {
    user: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.user) {
            frappe.call({
                method: "law_management.law_management.doctype.case.case.get_user_role_mapping",
                args: { user: row.user },
                callback: function (r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'role', r.message);
                    }
                }
            });
        }
    },

    role: function (frm, cdt, cdn) {
        set_standard_billing_rate(cdt, cdn);
    }
});

function set_standard_billing_rate(cdt, cdn) {
    let row = locals[cdt][cdn];
    let rate = STANDARD_BILLING_RATES_USD[row.role];

    if (rate) {
        frappe.model.set_value(cdt, cdn, 'billing_rate', rate);
    }
}

function is_case_team_member(frm, user) {
    return (frm.doc.team_members || []).some(member => member.user === user);
}

function remove_time_log_row(frm, cdt, cdn) {
    frm.doc.time_logs = (frm.doc.time_logs || []).filter(row => row.name !== cdn);
    frappe.model.clear_doc(cdt, cdn);
    frm.refresh_field('time_logs');
}

// Patch AssignToDialog to filter users for Case doctype
if (frappe.ui.form.AssignToDialog && !frappe.ui.form.AssignToDialog.prototype._case_filter_patched) {
    const original_get_fields = frappe.ui.form.AssignToDialog.prototype.get_fields;

    frappe.ui.form.AssignToDialog.prototype.get_fields = function () {
        let fields = original_get_fields.call(this);

        if (this.frm && this.frm.doctype === 'Case') {
            const assign_field = fields.find(f => f.fieldname === 'assign_to');
            if (assign_field) {
                // Capture frm for use in the closure
                let frm = this.frm;

                assign_field.get_data = function (txt) {
                    return frappe.call({
                        method: "law_management.law_management.doctype.case.case.get_member_query",
                        args: {
                            doctype: "User",
                            txt: txt || "",
                            searchfield: "full_name",
                            start: 0,
                            page_len: 20,
                            filters: {
                                case_name: frm.doc.name
                            }
                        }
                    }).then(r => {
                        if (r.message) {
                            return r.message.map(d => ({
                                value: d[0],
                                label: d[1] ? `${d[1]} (${d[0]})` : d[0]
                            }));
                        }
                        return [];
                    });
                };
            }
        }
        return fields;
    };

    frappe.ui.form.AssignToDialog.prototype._case_filter_patched = true;
}
