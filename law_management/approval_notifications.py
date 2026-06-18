import frappe
from frappe.utils import get_url_to_form


APPROVAL_CONFIG = {
	"Leave Application": {
		"approver_field": "leave_approver",
		"department_parentfield": "leave_approvers",
		"label": "Leave Application",
	},
	"Expense Claim": {
		"approver_field": "expense_approver",
		"department_parentfield": "expense_approvers",
		"label": "Expense Claim",
	},
}


def _get_employee_info(employee):
	if not employee:
		return frappe._dict()

	return frappe.db.get_value(
		"Employee",
		employee,
		["user_id", "department", "employee_name"],
		as_dict=True,
	) or frappe._dict()


def _unique(values):
	seen = set()
	result = []

	for value in values:
		if value and value not in seen:
			seen.add(value)
			result.append(value)

	return result


def _get_configured_approvers(doc):
	config = APPROVAL_CONFIG.get(doc.doctype)
	if not config:
		return []

	approvers = []
	explicit_approver = doc.get(config["approver_field"])
	if explicit_approver:
		approvers.append(explicit_approver)

	employee_info = _get_employee_info(doc.get("employee"))
	department = doc.get("department") or employee_info.get("department")

	if department:
		approvers.extend(
			row.approver
			for row in frappe.get_all(
				"Department Approver",
				filters={
					"parent": department,
					"parentfield": config["department_parentfield"],
				},
				fields=["approver"],
				order_by="idx asc",
			)
		)

	employee_user = employee_info.get("user_id")
	return [user for user in _unique(approvers) if user != employee_user]


def _get_enabled_user_emails(users):
	if not users:
		return []

	user_rows = frappe.get_all(
		"User",
		filters={"name": ["in", users], "enabled": 1},
		fields=["name", "email"],
	)
	email_by_user = {
		row.name: row.email or (row.name if "@" in row.name else None)
		for row in user_rows
	}

	return _unique(email_by_user.get(user) for user in users)


def _share_with_approvers(doc, approvers):
	for user in approvers:
		frappe.share.add_docshare(
			doc.doctype,
			doc.name,
			user,
			read=1,
			write=1,
			submit=1,
			flags={"ignore_share_permission": True},
		)


def _format_approval_message(doc):
	employee_info = _get_employee_info(doc.get("employee"))
	employee_name = doc.get("employee_name") or employee_info.get("employee_name") or doc.get("employee")
	department = doc.get("department") or employee_info.get("department") or "-"
	link = get_url_to_form(doc.doctype, doc.name)

	lines = [
		f"<p>{employee_name} created a {doc.doctype} that needs approval.</p>",
		"<ul>",
		f"<li><b>Document:</b> {doc.name}</li>",
		f"<li><b>Department:</b> {department}</li>",
	]

	if doc.doctype == "Leave Application":
		lines.extend(
			[
				f"<li><b>Leave Type:</b> {doc.get('leave_type') or '-'}</li>",
				f"<li><b>From:</b> {doc.get('from_date') or '-'}</li>",
				f"<li><b>To:</b> {doc.get('to_date') or '-'}</li>",
				f"<li><b>Total Leave Days:</b> {doc.get('total_leave_days') or '-'}</li>",
			]
		)
	else:
		lines.extend(
			[
				f"<li><b>Total Claimed Amount:</b> {doc.get('grand_total') or doc.get('total_claimed_amount') or '-'}</li>",
				f"<li><b>Approval Status:</b> {doc.get('approval_status') or '-'}</li>",
			]
		)

	lines.extend(
		[
			"</ul>",
			f'<p><a href="{link}">Open {doc.doctype}</a></p>',
			"<p>This message was sent to all configured approvers for the employee's department.</p>",
		]
	)

	return "\n".join(lines)


def _notify_all_configured_approvers(doc):
	approvers = _get_configured_approvers(doc)
	if not approvers:
		return

	_share_with_approvers(doc, approvers)

	recipients = _get_enabled_user_emails(approvers)
	if not recipients:
		return

	employee_name = doc.get("employee_name") or doc.get("employee")
	frappe.sendmail(
		recipients=recipients,
		subject=f"{doc.doctype} {doc.name} needs approval - {employee_name}",
		message=_format_approval_message(doc),
		reference_doctype=doc.doctype,
		reference_name=doc.name,
	)


def notify_leave_application_approvers(doc, method=None):
	_notify_all_configured_approvers(doc)


def notify_expense_claim_approvers(doc, method=None):
	_notify_all_configured_approvers(doc)


def share_leave_application_with_approvers(doc, method=None):
	_share_with_approvers(doc, _get_configured_approvers(doc))


def share_expense_claim_with_approvers(doc, method=None):
	_share_with_approvers(doc, _get_configured_approvers(doc))
