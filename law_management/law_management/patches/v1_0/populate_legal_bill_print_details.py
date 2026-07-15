import frappe
from frappe.utils import flt, money_in_words

from law_management.law_management.doctype.legal_bill.legal_bill import (
	DEFAULT_RECEIVING_BANK,
	_get_customer_invoice_details,
	_get_wire_account_details,
)


DEFAULT_VAT_RATE = 15.0
DEFAULT_SIGNATORY_NAME = "Tibebe Zewdu"
DEFAULT_SIGNATORY_TITLE = "Managing Partner"


def execute():
	if not frappe.db.table_exists("Legal Bill"):
		return

	for bill_name in frappe.get_all("Legal Bill", pluck="name"):
		bill = frappe.get_doc("Legal Bill", bill_name)
		subtotal = sum(flt(item.amount) for item in bill.items)
		vat_amount = flt(subtotal * DEFAULT_VAT_RATE / 100, 2)
		grand_total = flt(subtotal + vat_amount, 2)

		values = {
			"apply_vat": 1,
			"vat_rate": DEFAULT_VAT_RATE,
			"subtotal": subtotal,
			"vat_amount": vat_amount,
			"grand_total": grand_total,
			"in_words": money_in_words(grand_total, bill.currency),
			"signatory_name": DEFAULT_SIGNATORY_NAME,
			"signatory_title": DEFAULT_SIGNATORY_TITLE,
		}
		receiving_bank = bill.receiving_bank or DEFAULT_RECEIVING_BANK
		values["receiving_bank"] = receiving_bank
		values.update(_get_wire_account_details(receiving_bank, bill.currency) or {})
		values.update(
			_get_customer_invoice_details(
				bill.customer,
				bill.billing_address,
				bill.attention_contact,
			)
		)
		frappe.db.set_value("Legal Bill", bill.name, values, update_modified=False)
