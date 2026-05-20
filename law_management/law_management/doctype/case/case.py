# Copyright (c) 2025, Tbest and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import today, getdate, add_months, add_days

class Case(Document):
	def validate(self):
		if self.billing_type == "Retainer":
			# Only regenerate if configuration changes or table is empty
			if not self.retainer_schedules or \
			   self.has_value_changed("retainer_amount") or \
			   self.has_value_changed("retainer_duration") or \
			   self.has_value_changed("payment_frequency") or \
			   self.has_value_changed("total_retainer_hours") or \
			   self.has_value_changed("payment_start_date"):
				self.generate_retainer_schedule()

		if self.billing_type == "Retainer":
			self.update_retainer_hours_from_logs()

	def update_retainer_hours_from_logs(self):
		if not self.retainer_schedules:
			return

		# 1. Fetch Member Rates
		# stored as {user: rate}
		member_rates = {}
		members = frappe.get_all("Case Member", filters={"parent": self.name}, fields=["user", "billing_rate"])
		for m in members:
			member_rates[m.user] = m.billing_rate or 0

		# 2. Reset Schedules
		for s in self.retainer_schedules:
			s.used_hours = 0
			s.excess_hours = 0
			s.excess_amount = 0.0

		if not self.time_logs:
			return

		# 3. Process logs per schedule period
		# We need to process chronologically to determine WHO pushed it over the limit

		# Sort logs by date and creation (if available) for accurate timeline
		sorted_logs = sorted(self.time_logs, key=lambda x: (getdate(x.date), x.creation or ""))

		for s in self.retainer_schedules:
			period_start = getdate(s.start_date)
			period_end = getdate(s.end_date)
			allocated = s.allocated_hours or 0
			current_used = 0.0

			for log in sorted_logs:
				log_date = getdate(log.date)

				if period_start <= log_date <= period_end:
					# Calculate duration
					h = log.log_hours or 0
					m = log.log_minutes or 0
					duration = h + (m / 60.0)

					if duration <= 0:
						continue

					# Determine if this log contributes to excess
					# Scenario 1: Already over limit -> Entire log is excess
					if current_used >= allocated:
						excess_part = duration
						normal_part = 0.0

					# Scenario 2: This log crosses the limit -> Split
					elif (current_used + duration) > allocated:
						normal_part = allocated - current_used
						excess_part = duration - normal_part

					# Scenario 3: Under limit -> All normal
					else:
						normal_part = duration
						excess_part = 0.0

					# Update totals
					current_used += duration
					s.used_hours += duration

					if excess_part > 0:
						s.excess_hours += excess_part
						rate = member_rates.get(log.user, 0)
						s.excess_amount += (excess_part * rate)

	@frappe.whitelist()
	def generate_retainer_schedule(self):
		if not (self.retainer_amount and self.retainer_duration and self.payment_frequency and self.payment_start_date):
			return

		# Frequency map: (months per period, number of periods per year)
		frequency_map = {
			"Quarterly": 3,
			"Semi-Annually": 6,
			"Annually": 12,
			"Monthly": 1
		}

		months_per_period = frequency_map.get(self.payment_frequency)
		if not months_per_period:
			return

		# Calculate total periods
		total_periods = int(self.retainer_duration * (12 / months_per_period))

		# Calculate amounts per period
		amount_per_period = self.retainer_amount / total_periods
		hours_per_period = (self.total_retainer_hours or 0) / total_periods

		# Clear existing schedule to regenerate
		self.retainer_schedules = []

		current_date = getdate(self.payment_start_date)

		for i in range(total_periods):
			end_date = add_months(current_date, months_per_period)
			period_end_date = add_days(end_date, -1)

			self.append("retainer_schedules", {
				"schedule_name": f"Period {i+1}",
				"start_date": current_date,
				"end_date": period_end_date,
				"amount": amount_per_period,
				"allocated_hours": hours_per_period,
				"used_hours": 0,
				"excess_amount": 0
			})

			# Update current date for next iteration
			current_date = end_date

		# Set Case Payment End Date to the end of the last period
		if self.retainer_schedules:
			# The last row's end_date is actually what we want.
			last_row = self.retainer_schedules[-1]
			self.payment_end_date = last_row.end_date

		return [d.as_dict() for d in self.retainer_schedules]

@frappe.whitelist()
def get_member_rate(case, user):
	# Helper to fetch rate for Timesheet
	rate = frappe.db.get_value("Case Member", {"parent": case, "user": user}, "billing_rate")
	return rate or 0

@frappe.whitelist()
def get_legal_team_users(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT distinct t1.name, t1.full_name
		FROM `tabUser` t1, `tabHas Role` t2
		WHERE t2.parent = t1.name
		AND t2.role IN ('Legal Partner', 'Legal Associate', 'Legal Paralegal')
		AND t1.enabled = 1
		AND (t1.name LIKE %(txt)s OR t1.full_name LIKE %(txt)s)
		ORDER BY t1.full_name ASC
		LIMIT %(start)s, %(page_len)s
	""", {
		"txt": "%" + (txt or "") + "%",
		"start": start,
		"page_len": page_len
	})


@frappe.whitelist()
def get_user_role_mapping(user):
	if not user: return ""

	roles = frappe.get_roles(user)

	if "Legal Partner" in roles:
		return "Partner"
	elif "Legal Associate" in roles:
		return "Associate"
	elif "Legal Paralegal" in roles:
		return "Paralegal"

	return ""

@frappe.whitelist()
def get_member_query(doctype, txt, searchfield, start, page_len, filters):
	if isinstance(filters, str):
		filters = json.loads(filters)

	return frappe.db.sql("""
		SELECT t1.user, t2.full_name
		FROM `tabCase Member` t1
		LEFT JOIN `tabUser` t2 ON t1.user = t2.name
		WHERE t1.parent = %(case_name)s
		AND (t1.user LIKE %(txt)s OR t2.full_name LIKE %(txt)s)
	""", {
		"case_name": filters.get("case_name"),
		"txt": "%" + txt + "%"
	})

@frappe.whitelist()
def create_retainer_invoice(case_name, schedule_name):
	case = frappe.get_doc("Case", case_name)

	schedule_row = next((s for s in case.retainer_schedules if s.schedule_name == schedule_name), None)
	if not schedule_row:
		frappe.throw("Invalid Schedule Period selected")

	# 1. Find or Create Default Service Item
	service_item_name = "Retainer Fee"
	if not frappe.db.exists("Legal Service Item", service_item_name):
		try:
			item = frappe.new_doc("Legal Service Item")
			item.service_name = service_item_name
			item.standard_description = "Default Retainer Fee Service"
			item.flags.ignore_permissions = True
			item.save()
		except Exception:
			# Fallback if creation fails (unlikely, but handling race or perms)
			# Try to get ANY item
			service_item_name = frappe.db.get_value("Legal Service Item")
			if not service_item_name:
				frappe.throw("Could not find or auto-create a 'Retainer Fee' Service Item. Please create one manually.")

	service_item = service_item_name

	invoice = frappe.new_doc("Legal Bill")
	invoice.customer = case.client
	invoice.reference_doctype = "Case"
	invoice.case_reference = case.name
	invoice.bill_date = today()
	invoice.due_date = today() # Or based on payment terms

	# Add Line Item
	invoice.append("items", {
		"service": service_item,
		"description": f"Retainer Fee for {schedule_row.schedule_name} ({schedule_row.start_date} - {schedule_row.end_date})",
		"qty": 1,
		"rate": schedule_row.amount,
		"amount": schedule_row.amount
	})

	# Check for Excess Amount
	if schedule_row.excess_amount > 0:
		excess_item_name = "Retainer Excess Fee"
		if not frappe.db.exists("Legal Service Item", excess_item_name):
			try:
				item = frappe.new_doc("Legal Service Item")
				item.service_name = excess_item_name
				item.standard_description = "Fee for hours used beyond retainer allocation"
				item.flags.ignore_permissions = True
				item.save()
			except Exception:
				pass # Fallback or skip if fails

		invoice.append("items", {
			"service": excess_item_name if frappe.db.exists("Legal Service Item", excess_item_name) else service_item,
			"description": f"Excess Hours Fee for {schedule_row.schedule_name}",
			"qty": 1,
			"rate": schedule_row.excess_amount,
			"amount": schedule_row.excess_amount
		})

	invoice.save()
	return invoice.name

@frappe.whitelist()
def create_milestone_invoice(case_name, milestone_name):
	case = frappe.get_doc("Case", case_name)

	milestone_row = next((m for m in case.milestones if m.milestone_name == milestone_name), None)
	if not milestone_row:
		frappe.throw("Invalid Milestone selected")

	# 1. Find or Create Default Service Item
	service_item_name = "Milestone Fee"
	if not frappe.db.exists("Legal Service Item", service_item_name):
		try:
			item = frappe.new_doc("Legal Service Item")
			item.service_name = service_item_name
			item.standard_description = "Default Milestone Fee Service"
			item.flags.ignore_permissions = True
			item.save()
		except Exception:
			service_item_name = frappe.db.get_value("Legal Service Item")

	service_item = service_item_name

	invoice = frappe.new_doc("Legal Bill")
	invoice.customer = case.client
	invoice.reference_doctype = "Case"
	invoice.case_reference = case.name
	invoice.bill_date = today()
	invoice.due_date = today()

	# Add Line Item
	invoice.append("items", {
		"service": service_item,
		"description": f"Milestone Payment: {milestone_row.milestone_name}",
		"qty": 1,
		"rate": milestone_row.amount,
		"amount": milestone_row.amount
	})

	invoice.save()
	return invoice.name

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user

	# 1. Partners and System Managers see everything
	roles = frappe.get_roles(user)
	if "Legal Partner" in roles or "System Manager" in roles:
		return ""

	# 2. Associates and Paralegals see only cases where they are a member
	return f"""(`tabCase`.name in (select parent from `tabCase Member` where user = '{user}'))"""

def has_permission(doc, user):
	if not user: user = frappe.session.user
	roles = frappe.get_roles(user)

	# 1. Partners and System Managers have full access
	if "Legal Partner" in roles or "System Manager" in roles:
		return True

	# 2. Associates and Paralegals:
	# - Create: Blocked for Paralegals (handled here or via Role Permissions)
	if doc.is_new():
		if "Paralegal" in roles and "Legal Associate" not in roles:
			return False
		return True

	# - Read/Write: Must be a team member
	is_member = frappe.db.exists("Case Member", {"parent": doc.name, "user": user})
	return True if is_member else False
