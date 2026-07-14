import frappe


ESCALATION_CONTACT_DOCTYPE = "Legal Bill Escalation Contact"


def execute():
	_sync_legal_bill_contact_fields()
	_migrate_existing_escalation_contacts()
	frappe.clear_cache(doctype="Legal Bill")


def _sync_legal_bill_contact_fields():
	if not frappe.db.table_exists("DocField"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET fieldtype = 'Table MultiSelect',
			label = 'Escalation Contacts',
			options = %s,
			description = 'Partners to notify if the bill is overdue by 30 days.'
		WHERE parent = 'Legal Bill'
		AND fieldname = 'escalation_contact'
		""",
		ESCALATION_CONTACT_DOCTYPE,
	)

	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET description = 'Auto-filled with the active user linked to the Accounts department.'
		WHERE parent = 'Legal Bill'
		AND fieldname = 'finance_contact'
		"""
	)

	if frappe.db.table_exists("Property Setter"):
		_update_property_setter("escalation_contact", "fieldtype", "Table MultiSelect")
		_update_property_setter("escalation_contact", "label", "Escalation Contacts")
		_update_property_setter("escalation_contact", "options", ESCALATION_CONTACT_DOCTYPE)


def _update_property_setter(fieldname, property_name, value):
	frappe.db.sql(
		"""
		UPDATE `tabProperty Setter`
		SET value = %s
		WHERE doc_type = 'Legal Bill'
		AND field_name = %s
		AND property = %s
		""",
		(value, fieldname, property_name),
	)


def _migrate_existing_escalation_contacts():
	if not (
		frappe.db.table_exists("Legal Bill")
		and frappe.db.table_exists(ESCALATION_CONTACT_DOCTYPE)
		and frappe.db.has_column("Legal Bill", "escalation_contact")
	):
		return

	rows = frappe.db.sql(
		"""
		SELECT name, escalation_contact
		FROM `tabLegal Bill`
		WHERE escalation_contact IS NOT NULL
		AND escalation_contact != ''
		""",
		as_dict=True,
	)

	for row in rows:
		if _escalation_contact_exists(row.name, row.escalation_contact):
			continue

		_insert_escalation_contact(row.name, row.escalation_contact)


def _escalation_contact_exists(parent, user):
	return bool(
		frappe.db.exists(
			ESCALATION_CONTACT_DOCTYPE,
			{
				"parent": parent,
				"parenttype": "Legal Bill",
				"parentfield": "escalation_contact",
				"user": user,
			},
		)
	)


def _insert_escalation_contact(parent, user):
	frappe.db.sql(
		f"""
		INSERT INTO `tab{ESCALATION_CONTACT_DOCTYPE}`
			(name, creation, modified, modified_by, owner, docstatus, parent, parentfield, parenttype, idx, user)
		VALUES
			(%s, NOW(), NOW(), 'Administrator', 'Administrator', 0, %s, 'escalation_contact', 'Legal Bill', 1, %s)
		""",
		(frappe.generate_hash(length=10), parent, user),
	)
