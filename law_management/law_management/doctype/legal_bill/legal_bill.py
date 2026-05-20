# Copyright (c) 2024, Law Firm and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, add_days

class LegalBill(Document):
	def validate(self):
		self.calculate_due_date()

	def before_save(self):
		self.calculate_days_open()
		self.set_status()
		self.check_overdue_on_save()

	def before_insert(self):
		if not self.finance_contact:
			# Auto-fill with a user having 'Legal Finance' role
			finance_user = get_legal_finance_user()
			if finance_user:
				self.finance_contact = finance_user

	def calculate_days_open(self):
		if self.bill_date:
			self.days_open = (getdate(nowdate()) - getdate(self.bill_date)).days
		else:
			self.days_open = 0

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
		if self.escalation_contact:
			email = frappe.db.get_value("User", self.escalation_contact, "email")
			if email:
				recipients.append(email)



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

@frappe.whitelist()
def get_legal_finance_user():
	# fetch users with the role
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
