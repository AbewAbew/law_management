import frappe


FIXED_FEE_OPTIONS = "Hourly\nFixed Fee\nRetainer\nContingency"
FIXED_FEE_SECTION_DEPENDS_ON = "eval:doc.billing_type == 'Fixed Fee'\r\n"
MILESTONES_DEPENDS_ON = "eval:doc.billing_type == 'Fixed Fee' && doc.payment_structure == 'Milestones'"


def execute():
	_sync_case_doctype_metadata()
	_rename_existing_case_values()
	frappe.clear_cache(doctype="Case")


def _sync_case_doctype_metadata():
	if not frappe.db.table_exists("DocField"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET options = %s
		WHERE parent = 'Case'
		AND fieldname = 'billing_type'
		""",
		FIXED_FEE_OPTIONS,
	)

	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET depends_on = %s
		WHERE parent = 'Case'
		AND fieldname = 'milestones'
		""",
		MILESTONES_DEPENDS_ON,
	)

	if not _has_case_docfield("fixed_fee_configuration_section"):
		frappe.db.sql(
			"""
			UPDATE `tabDocField`
			SET fieldname = 'fixed_fee_configuration_section',
				label = 'Fixed Fee Configuration',
				depends_on = %s
			WHERE parent = 'Case'
			AND fieldname = 'flat_fee_configuration_section'
			""",
			FIXED_FEE_SECTION_DEPENDS_ON,
		)

	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET label = 'Fixed Fee Configuration',
			depends_on = %s
		WHERE parent = 'Case'
		AND fieldname = 'fixed_fee_configuration_section'
		""",
		FIXED_FEE_SECTION_DEPENDS_ON,
	)

	if frappe.db.table_exists("Property Setter"):
		frappe.db.sql(
			"""
			UPDATE `tabProperty Setter`
			SET value = %s
			WHERE doc_type = 'Case'
			AND field_name = 'billing_type'
			AND property = 'options'
			""",
			FIXED_FEE_OPTIONS,
		)


def _rename_existing_case_values():
	if not frappe.db.table_exists("Case") or not frappe.db.has_column("Case", "billing_type"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabCase`
		SET billing_type = 'Fixed Fee'
		WHERE billing_type = 'Flat Fee'
		"""
	)


def _has_case_docfield(fieldname):
	return bool(
		frappe.db.sql(
			"""
			SELECT name
			FROM `tabDocField`
			WHERE parent = 'Case'
			AND fieldname = %s
			LIMIT 1
			""",
			fieldname,
		)
	)
