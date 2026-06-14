import frappe


def execute():
	if not frappe.db.table_exists("Case") or not frappe.db.has_column("Case", "currency"):
		return

	frappe.db.sql("ALTER TABLE `tabCase` MODIFY COLUMN `currency` varchar(140)")
