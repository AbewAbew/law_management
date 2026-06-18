import frappe


DEFAULT_CURRENCY = "USD"


def _valid_currency_expression(column):
	return f"({column} IS NOT NULL AND {column} != '' AND {column} IN (SELECT name FROM `tabCurrency`))"


def execute():
	if frappe.db.table_exists("Case Member") and frappe.db.has_column("Case Member", "currency"):
		frappe.db.sql(
			"""
			UPDATE `tabCase Member`
			SET currency = %s
			WHERE currency IS NULL
			OR currency = ''
			OR currency NOT IN (SELECT name FROM `tabCurrency`)
			""",
			DEFAULT_CURRENCY,
		)

	if (
		frappe.db.table_exists("Retainer Schedule")
		and frappe.db.has_column("Retainer Schedule", "currency")
		and frappe.db.table_exists("Case")
		and frappe.db.has_column("Case", "currency")
	):
		frappe.db.sql(
			f"""
			UPDATE `tabRetainer Schedule` rs
			INNER JOIN `tabCase` c ON c.name = rs.parent
			SET rs.currency = CASE
				WHEN {_valid_currency_expression("c.currency")} THEN c.currency
				ELSE %s
			END
			WHERE rs.parenttype = 'Case'
			""",
			DEFAULT_CURRENCY,
		)

	if (
		frappe.db.table_exists("Case Milestone")
		and frappe.db.has_column("Case Milestone", "currency")
		and frappe.db.table_exists("Case")
		and frappe.db.has_column("Case", "currency")
	):
		frappe.db.sql(
			f"""
			UPDATE `tabCase Milestone` cm
			INNER JOIN `tabCase` c ON c.name = cm.parent
			SET cm.currency = CASE
				WHEN {_valid_currency_expression("c.currency")} THEN c.currency
				ELSE %s
			END
			WHERE cm.parenttype = 'Case'
			""",
			DEFAULT_CURRENCY,
		)

	if (
		frappe.db.table_exists("Legal Bill Item")
		and frappe.db.has_column("Legal Bill Item", "currency")
		and frappe.db.table_exists("Legal Bill")
		and frappe.db.has_column("Legal Bill", "currency")
	):
		frappe.db.sql(
			f"""
			UPDATE `tabLegal Bill Item` lbi
			INNER JOIN `tabLegal Bill` lb ON lb.name = lbi.parent
			SET lbi.currency = CASE
				WHEN {_valid_currency_expression("lb.currency")} THEN lb.currency
				ELSE %s
			END
			WHERE lbi.parenttype = 'Legal Bill'
			""",
			DEFAULT_CURRENCY,
		)
