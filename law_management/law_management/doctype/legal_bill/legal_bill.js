// Copyright (c) 2024, Law Firm and contributors
// For license information, please see license.txt

const LEGAL_BILL_BANK_ACCOUNTS = {
    'Awash Bank': {
        bank_name_and_address: 'AWASH BANK S.C',
        bank_branch: 'Millennium Akababi',
        bank_swift_code: 'AWINETAA XXX',
        accounts: {
            USD: ['TBeST Law USD Account', '021141025627100'],
            ETB: ['TBeST Law Birr Account', '013041025627100']
        }
    },
    'Sinqee Bank': {
        bank_name_and_address: '',
        bank_branch: '',
        bank_swift_code: '',
        accounts: {
            USD: ['TBeST Law USD Account', '2051130081315'],
            ETB: ['TBeST Law Birr Account', '1051130080113']
        }
    }
};

const LEGAL_BILL_ACCOUNT_HOLDER = 'TBeST Law LLP';
const LEGAL_BILL_ACCOUNT_HOLDER_TIN = '0081829025';

frappe.ui.form.on('Legal Bill', {
    setup: function (frm) {
        frm.set_query('currency', function () {
            return {
                filters: {
                    'enabled': 1,
                    'name': ['in', ['USD', 'ETB']]
                }
            };
        });

        frm.set_query('print_format', function () {
            return {
                filters: {
                    'doc_type': 'Legal Bill'
                }
            };
        });

        frm.set_query('finance_contact', function () {
            return {
                query: 'law_management.law_management.doctype.legal_bill.legal_bill.get_accounts_department_users'
            };
        });

        frm.set_query('escalation_contact', function () {
            return {
                query: 'law_management.law_management.doctype.legal_bill.legal_bill.get_legal_partner_users'
            };
        });
    },

    onload: function (frm) {
        if (frm.is_new() && !frm.doc.finance_contact) {
            frappe.call({
                method: "law_management.law_management.doctype.legal_bill.legal_bill.get_accounts_department_finance_user",
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("finance_contact", r.message);
                    }
                }
            });
        }

        sync_item_currencies(frm);
        sync_wire_transfer_details(frm);

        // Enforce Due Date calculation for mapped items
        if (frm.doc.bill_date) {
            var due_date = frappe.datetime.add_days(frm.doc.bill_date, 15);
            frm.set_value('due_date', due_date);
        }
    },

    refresh: function (frm) {
        sync_item_currencies(frm);
        sync_wire_transfer_details(frm);

        if (frm.doc.print_format) {
            frm.meta.default_print_format = frm.doc.print_format;
        }

        // Buttons
        if (frm.doc.status !== "Paid") {
            frm.add_custom_button(__('Mark as Paid'), function () {
                frm.set_value('status', 'Paid');
                frm.save();
            }).addClass('btn-primary');

            frm.add_custom_button(__('Send Invoice Email'), function () {
                frm.email_doc();
            });
        }

        // Read Only if Paid
        if (frm.doc.status === "Paid") {
            frm.set_read_only(true);
        }
    },

    currency: function (frm) {
        if (frm.doc.currency) {
            sync_wire_transfer_details(frm);
            // Update child table currency for display
            sync_item_currencies(frm);

            if (frm.doc.currency !== "ETB") {
                frappe.call({
                    method: "erpnext.setup.utils.get_exchange_rate",
                    args: {
                        from_currency: frm.doc.currency,
                        to_currency: "ETB"
                    },
                    callback: function (r) {
                        if (!r.exc) {
                            frm.set_value('conversion_rate', r.message);
                            // Recalculate all row rates on conversion update
                            calculate_all_rates(frm);
                        }
                    }
                });
            } else {
                frm.set_value('conversion_rate', 1.0);
                calculate_all_rates(frm);
            }
        }
    },

    receiving_bank: function (frm) {
        sync_wire_transfer_details(frm);
    },

    validate: function (frm) {
        calculate_totals(frm);
    },

    bill_date: function (frm) {
        if (frm.doc.bill_date) {
            var due_date = frappe.datetime.add_days(frm.doc.bill_date, 15);
            frm.set_value('due_date', due_date);
        }
    }
});

var sync_wire_transfer_details = function (frm) {
    const bank = frm.doc.receiving_bank || 'Awash Bank';
    const bankDetails = LEGAL_BILL_BANK_ACCOUNTS[bank] || {};
    const accountDetails = (bankDetails.accounts || {})[frm.doc.currency || 'USD'];

    if (!frm.doc.receiving_bank) {
        frm.set_value('receiving_bank', bank);
    }

    frm.set_value('bank_account_name', accountDetails ? accountDetails[0] : '');
    frm.set_value('bank_account_number', accountDetails ? accountDetails[1] : '');
    frm.set_value('bank_name_and_address', bankDetails.bank_name_and_address || '');
    frm.set_value('bank_branch', bankDetails.bank_branch || '');
    frm.set_value('bank_swift_code', bankDetails.bank_swift_code || '');
    frm.set_value('bank_account_holder', accountDetails ? LEGAL_BILL_ACCOUNT_HOLDER : '');
    frm.set_value('bank_account_holder_tin', accountDetails ? LEGAL_BILL_ACCOUNT_HOLDER_TIN : '');
};

frappe.ui.form.on('Legal Bill Item', {
    items_add: function (frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency || "USD");
    },
    qty: function (frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },
    // Rate is now calculated from Amount, so typically we don't edit it, but if we did, we might reverse calc?
    // User asked "Rate column to show amount * conversion". Amount is editable.
    amount: function (frm, cdt, cdn) {
        calculate_rate_from_amount(frm, cdt, cdn);
    },
    service: function (frm, cdt, cdn) {
        // Fetch standard details
        var row = locals[cdt][cdn];
        if (row.service) {
            frappe.db.get_value("Legal Service Item", row.service, ["standard_description", "standard_rate"], function (r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "description", r.standard_description);
                    frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency || "USD");

                    // Standard Rate might be in ETB? Or USD? Assuming standard rate is a base suggestion.
                    // If we treat it as Amount (foreign), we set Amount.
                    // Let's assume standard_rate is just a default Amount.
                    frappe.model.set_value(cdt, cdn, "amount", r.standard_rate);
                    calculate_rate_from_amount(frm, cdt, cdn);
                }
            });
        }
    }
});

var sync_item_currencies = function (frm) {
    const currency = frm.doc.currency || "USD";

    (frm.doc.items || []).forEach(function (row) {
        if (row.currency !== currency) {
            frappe.model.set_value(row.doctype, row.name, "currency", currency);
        }
    });

    refresh_field("items");
};

var calculate_rate_from_amount = function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];

    // Rate is Foreign Currency
    var rate_foreign = row.amount; // Assuming Qty=1 or user inputs "Amount" as lump sum
    frappe.model.set_value(cdt, cdn, "rate", rate_foreign);

    // ETB Amount is for internal reference
    var etb_amount = row.amount * (frm.doc.conversion_rate || 1.0);
    frappe.model.set_value(cdt, cdn, "etb_amount", etb_amount);

    calculate_totals(frm);
};

var calculate_all_rates = function (frm) {
    $.each(frm.doc.items || [], function (i, row) {
        // Recalculate based on current Amount and new Conversion Rate
        var rate_foreign = row.amount;
        frappe.model.set_value(row.doctype, row.name, "rate", rate_foreign);

        var etb_amount = row.amount * (frm.doc.conversion_rate || 1.0);
        frappe.model.set_value(row.doctype, row.name, "etb_amount", etb_amount);
    });
    calculate_totals(frm);
};

var calculate_row_total = function (frm, cdt, cdn) {
    // Legacy / Safety: If Qty changes, maybe Amount changes?
    // Usually Amount = Qty * UnitPrice.
    // Here Amount IS the foreign price.
    // If Qty changes, does Amount (Total Foreign) change?
    // Often "Amount" means "Line Total". "Rate" means "Unit Price".
    // User said "Rate column should show amount * conversion rate".
    // This implies "Rate" column is hijacking the meaning to be "ETB Total Value".
    // And "Amount" is "Foreign Total Value".
    // If Qty=2, Amount=$100, then Rate(ETB)=100*Rate.
    // Does Qty affect Amount? If I type Amount=$100 manually, Qty doesn't matter for calc.
    // So Qty is just informational or for the invoice print.
    var row = locals[cdt][cdn];
    calculate_rate_from_amount(frm, cdt, cdn);
};

var calculate_totals = function (frm) {
    var grand_total = 0.0;
    (frm.doc.items || []).forEach(function (item) {
        grand_total += item.amount;
    });
    frm.set_value("grand_total", grand_total);
    // In words logic could go here or server side
};
