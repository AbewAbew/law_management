import frappe


def execute():
	annual_leave_types = frappe.get_all(
		"Leave Type",
		filters={"name": ("like", "Annual Leave%")},
		pluck="name",
	)

	for leave_type in annual_leave_types:
		# A value of 0 means no hard cap. The Ethiopian annual leave entitlement
		# increases with service years, so a fixed cap of 16 blocks valid allocations.
		frappe.db.set_value(
			"Leave Type",
			leave_type,
			"max_leaves_allowed",
			0,
			update_modified=False,
		)

	frappe.clear_cache(doctype="Leave Type")
