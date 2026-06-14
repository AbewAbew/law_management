import frappe


DEFAULT_CURRENCY = "USD"


def execute():
	for doctype in ("Case", "Legal Bill"):
		if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, "currency"):
			continue

		frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET currency = %s
			WHERE currency IS NULL
			OR currency = ''
			OR currency NOT IN (SELECT name FROM `tabCurrency`)
			""",
			DEFAULT_CURRENCY,
		)
