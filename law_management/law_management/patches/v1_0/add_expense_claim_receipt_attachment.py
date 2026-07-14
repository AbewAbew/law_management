import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Expense Claim Detail": [
				{
					"fieldname": "custom_receipt_attachment",
					"fieldtype": "Attach",
					"label": "Receipt Attachment",
					"insert_after": "description",
					"in_list_view": 1,
					"allow_on_submit": 1,
					"description": "Attach the receipt or supporting document for this expense line.",
				}
			]
		},
		update=True,
	)

	frappe.clear_cache(doctype="Expense Claim Detail")
