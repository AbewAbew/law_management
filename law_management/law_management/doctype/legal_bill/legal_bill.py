# Copyright (c) 2024, Law Firm and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import nowdate, getdate, add_days


LEGAL_INVOICE_PREFIX = "TBeST/INV"
LEGAL_INVOICE_DIGITS = 3
LEGAL_INVOICE_MAX_PER_YEAR = 999
DEFAULT_CURRENCY = "USD"
ACCOUNTS_DEPARTMENT_NAME = "Accounts"
EXCLUDED_USER_LINKS = ("Administrator", "Guest")


def _get_row_value(row, fieldname, default=None):
	if hasattr(row, "get"):
		return row.get(fieldname, default)
	return getattr(row, fieldname, default)


def _get_invoice_year(bill_date=None):
	return str(getdate(bill_date or nowdate()).year)


def _get_invoice_series_key(year):
	return f"{LEGAL_INVOICE_PREFIX}/{year}/"


def _format_invoice_name(year, sequence):
	return f"{LEGAL_INVOICE_PREFIX}/{sequence}/{year}"


def _generate_invoice_name(year):
	series_key = _get_invoice_series_key(year)
	current = frappe.db.get_value("Series", series_key, "current", order_by="name", for_update=True)

	if int(current or 0) >= LEGAL_INVOICE_MAX_PER_YEAR:
		frappe.throw(f"Invoice numbering for {year} has reached {LEGAL_INVOICE_MAX_PER_YEAR}.")

	internal_name = make_autoname(f"{series_key}.{'#' * LEGAL_INVOICE_DIGITS}")
	sequence = internal_name.replace(series_key, "", 1)
	return _format_invoice_name(year, sequence)


def _is_enabled_user(user):
	return bool(user and user not in EXCLUDED_USER_LINKS and frappe.db.get_value("User", user, "enabled"))


def _user_has_role(user, role):
	return bool(
		frappe.db.exists(
			"Has Role",
			{
				"parent": user,
				"parenttype": "User",
				"role": role,
			},
		)
	)


def _get_escalation_contact_users(escalation_contact):
	if not escalation_contact:
		return []

	if isinstance(escalation_contact, str):
		return [escalation_contact]

	users = []
	for row in escalation_contact:
		user = _get_row_value(row, "user")
		if user and user not in users:
			users.append(user)

	return users


class LegalBill(Document):
	def autoname(self):
		self.name = _generate_invoice_name(_get_invoice_year(self.bill_date))

	def validate(self):
		self.set_default_currency()
		self.validate_escalation_contact()
		self.calculate_due_date()
		self.set_item_currency_and_totals()

	def before_save(self):
		self.calculate_days_open()
		self.set_status()
		self.check_overdue_on_save()

	def before_insert(self):
		if not self.finance_contact:
			finance_user = get_accounts_department_finance_user()
			if finance_user:
				self.finance_contact = finance_user

	def calculate_days_open(self):
		if self.bill_date:
			self.days_open = (getdate(nowdate()) - getdate(self.bill_date)).days
		else:
			self.days_open = 0

	def set_default_currency(self):
		if not self.currency:
			self.currency = DEFAULT_CURRENCY

		if not self.conversion_rate:
			self.conversion_rate = 1.0

	def set_item_currency_and_totals(self):
		total = 0.0
		items = self.get("items") if hasattr(self, "get") else getattr(self, "items", None)
		for item in items or []:
			item.currency = self.currency

			if item.amount is None and item.rate is not None:
				item.amount = (item.qty or 1) * item.rate

			if item.rate is None and item.amount is not None:
				item.rate = item.amount

			item.etb_amount = (item.amount or 0) * (self.conversion_rate or 1.0)
			total += item.amount or 0

		self.grand_total = total

	def validate_escalation_contact(self):
		escalation_users = _get_escalation_contact_users(self.escalation_contact)
		if not escalation_users:
			return

		invalid_users = [
			user for user in escalation_users if not (_is_enabled_user(user) and _user_has_role(user, "Legal Partner"))
		]

		if invalid_users:
			frappe.throw(
				"Escalation Contacts must only contain enabled users with the Legal Partner role: {0}".format(
					", ".join(invalid_users)
				)
			)

	def calculate_due_date(self):
		if self.bill_date:
			expected_due = add_days(self.bill_date, 15)
			if getdate(self.due_date) != getdate(expected_due):
				self.due_date = expected_due

	def set_status(self):
		if self.status == "Paid":
			self.workflow_state = "Settled"
			return

		today = getdate(nowdate())
		due = getdate(self.due_date)

		if today > due:
			overdue_days = (today - due).days
			self.workflow_state = f"Overdue by {overdue_days} days"
		else:
			self.workflow_state = "Pending"

	def check_overdue_on_save(self):
		today = getdate(nowdate())
		due_date = getdate(self.due_date)

		if today <= due_date:
			return

		overdue_days = (today - due_date).days

		# 2. Escalation (15 days overdue)
		if overdue_days >= 15 and self.status in ["Unpaid", "Reminder Sent"]:
			self.status = "Escalated"
			self.notify_partners()

		# 1. First Reminder (1 day overdue)
		elif overdue_days >= 1 and self.status == "Unpaid":
			self.status = "Reminder Sent"
			self.send_reminder_email()

	def send_reminder_email(self):
		# Logic to send email to Finance Contact to forward to client
		if self.finance_contact:
			finance_email = frappe.db.get_value("User", self.finance_contact, "email")
			if finance_email:
				sender = frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id")
				frappe.sendmail(
					recipients=[finance_email],
					sender=sender,
					subject=f"[Action Required] Overdue Invoice: {self.name}",
					message=f"The due date for bill {self.name} has passed. Please send the invoice to the client again.",
					reference_doctype=self.doctype,
					reference_name=self.name
				)

	def notify_partners(self):
		# Logic to notify partners or specific escalation contact
		recipients = []
		for user in _get_escalation_contact_users(self.escalation_contact):
			email = frappe.db.get_value("User", user, "email")
			if email:
				recipients.append(email)

		recipients = sorted(set(recipients))

		if recipients:
			sender = frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id")
			frappe.sendmail(
				recipients=recipients,
				sender=sender,
				subject=f"Escalation: Invoice {self.name} Overdue > 30 Days",
				message=f"The bill {self.name} for {self.customer} remains unpaid after 30 days overdue. Enhanced collection measures may be needed.",
				reference_doctype=self.doctype,
				reference_name=self.name
			)

def check_automation_rules():
	"""
	Scheduled job to check for overdue bills and send reminders.
	"""
	bills = frappe.get_all("Legal Bill", filters={"status": ["in", ["Unpaid", "Reminder Sent"]]}, fields=["name", "due_date", "status", "customer", "bill_date"])

	for bill_data in bills:
		bill = frappe.get_doc("Legal Bill", bill_data.name)
		today = getdate(nowdate())
		due = getdate(bill.due_date)

		if today > due:
			overdue_days = (today - due).days

			# 2. Escalation (15 days overdue)
			if overdue_days >= 15 and bill.status in ["Unpaid", "Reminder Sent"]:
				bill.status = "Escalated"
				bill.save(ignore_permissions=True)
				bill.notify_partners()

			# 1. First Reminder (1 day overdue)
			elif overdue_days >= 1 and bill.status == "Unpaid":
				bill.status = "Reminder Sent"
				bill.save(ignore_permissions=True)
				bill.send_reminder_email()

def _get_legal_finance_role_user():
	has_role = frappe.qb.DocType("Has Role")
	user = frappe.qb.DocType("User")

	query = (
		frappe.qb.from_(has_role)
		.join(user).on(has_role.parent == user.name)
		.select(user.name)
		.where(
			(has_role.role == "Legal Finance") &
			(user.enabled == 1) &
			(user.name != "Legal Desk") &
			(user.first_name != "Legal Desk") # Check names too just in case
		)
		.limit(1)
	)

	result = query.run()
	if result:
		return result[0][0]
	return None


def _get_accounts_department_user_rows(txt="", start=0, page_len=20):
	if not (
		frappe.db.table_exists("Employee")
		and frappe.db.table_exists("Department")
		and frappe.db.has_column("Employee", "user_id")
		and frappe.db.has_column("Employee", "department")
	):
		return []

	txt = txt or ""
	return frappe.db.sql(
		"""
		SELECT DISTINCT u.name, u.full_name
		FROM `tabEmployee` e
		INNER JOIN `tabUser` u
			ON u.name = e.user_id
		LEFT JOIN `tabDepartment` d
			ON d.name = e.department
		WHERE e.status = 'Active'
			AND e.user_id IS NOT NULL
			AND e.user_id != ''
			AND u.enabled = 1
			AND u.name NOT IN ('Administrator', 'Guest')
			AND (
				d.department_name = %(department)s
				OR d.name = %(department)s
				OR d.name LIKE %(department_prefix)s
				OR e.department = %(department)s
				OR e.department LIKE %(department_prefix)s
			)
			AND (
				%(txt)s = ''
				OR u.name LIKE %(like_txt)s
				OR u.full_name LIKE %(like_txt)s
				OR e.employee_name LIKE %(like_txt)s
			)
		ORDER BY u.full_name ASC, u.name ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"department": ACCOUNTS_DEPARTMENT_NAME,
			"department_prefix": f"{ACCOUNTS_DEPARTMENT_NAME} -%",
			"txt": txt,
			"like_txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
def get_accounts_department_finance_user():
	accounts_users = _get_accounts_department_user_rows(page_len=1)
	if accounts_users:
		return accounts_users[0][0]

	return _get_legal_finance_role_user()


@frappe.whitelist()
def get_legal_finance_user():
	return get_accounts_department_finance_user()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_accounts_department_users(doctype, txt, searchfield, start, page_len, filters):
	return _get_accounts_department_user_rows(txt=txt, start=start, page_len=page_len)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_legal_partner_users(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT DISTINCT u.name, u.full_name
		FROM `tabUser` u
		JOIN `tabHas Role` hr ON hr.parent = u.name
		WHERE hr.role = 'Legal Partner'
		AND hr.parenttype = 'User'
		AND u.enabled = 1
		AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.full_name ASC
		LIMIT %(start)s, %(page_len)s
	""", {
		"txt": "%" + (txt or "") + "%",
		"start": start,
		"page_len": page_len,
	})
