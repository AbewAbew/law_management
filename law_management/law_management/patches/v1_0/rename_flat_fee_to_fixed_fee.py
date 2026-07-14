import frappe


def execute():
	if not frappe.db.table_exists("Case") or not frappe.db.has_column("Case", "billing_type"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabCase`
		SET billing_type = 'Fixed Fee'
		WHERE billing_type = 'Flat Fee'
		"""
	)
