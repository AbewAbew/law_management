frappe.listview_settings['Legal Bill'] = {
    add_fields: ['status', 'due_date', 'bill_date'],
    get_indicator: function (doc) {
        // Logic for the colored dots
        if (doc.status === "Paid") return [__("Paid"), "green", "status,=,Paid"];
        if (doc.status === "Escalated") return [__("Escalated"), "red", "status,=,Escalated"];

        // Calculate days overdue
        const today = frappe.datetime.now_date();
        if (doc.status !== "Paid" && doc.due_date < today) {
            return [__("Overdue"), "orange", "status,!=,Paid"];
        }

        if (doc.status === "Reminder Sent") return [__("Reminder Sent"), "orange", "status,=,Reminder Sent"];

        return [__("Unpaid"), "gray", "status,=,Unpaid"];
    },
    formatters: {
        // Custom column to show "Days Since"
        bill_date: function (value, doc) {
            if (value) {
                const days = frappe.datetime.get_diff(frappe.datetime.now_date(), value);
                return value + ` <span style="color:gray; font-size:10px">(${days} days ago)</span>`;
            }
            return value;
        }
    }
};
