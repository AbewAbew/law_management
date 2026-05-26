# Copyright (c) 2025, Tbest and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import today, getdate, add_months, add_days, flt


def _get_row_value(row, fieldname, default=None):
	if hasattr(row, "get"):
		return row.get(fieldname, default)
	return getattr(row, fieldname, default)


def _get_case_member_rates(case_name):
	member_rates = {}
	members = frappe.get_all(
		"Case Member",
		filters={
			"parent": case_name,
			"parenttype": "Case",
			"parentfield": "team_members",
		},
		fields=["user", "billing_rate"],
	)

	for member in members:
		member_rates[member.user] = flt(member.billing_rate)

	return member_rates


def _get_log_sort_key(log):
	log_date = _get_row_value(log, "date")
	return (
		getdate(log_date) if log_date else getdate("1900-01-01"),
		str(_get_row_value(log, "creation") or ""),
		flt(_get_row_value(log, "idx") or 0),
	)


def _calculate_retainer_schedule_usage(retainer_schedules, time_logs, member_rates):
	usage_by_schedule = {}
	sorted_logs = sorted(time_logs or [], key=_get_log_sort_key)

	for schedule in retainer_schedules or []:
		schedule_name = _get_row_value(schedule, "schedule_name")
		period_start = _get_row_value(schedule, "start_date")
		period_end = _get_row_value(schedule, "end_date")

		usage = frappe._dict(
			used_hours=0.0,
			excess_hours=0.0,
			excess_amount=0.0,
			missing_rate_users=[],
		)

		if not schedule_name:
			continue

		if not (period_start and period_end):
			usage_by_schedule[schedule_name] = usage
			continue

		period_start = getdate(period_start)
		period_end = getdate(period_end)
		allocated = flt(_get_row_value(schedule, "allocated_hours"))
		current_used = 0.0
		missing_rate_users = set()

		for log in sorted_logs:
			log_date = _get_row_value(log, "date")
			if not log_date:
				continue

			log_date = getdate(log_date)
			if not (period_start <= log_date <= period_end):
				continue

			duration = flt(_get_row_value(log, "log_hours")) + (flt(_get_row_value(log, "log_minutes")) / 60.0)
			if duration <= 0:
				continue

			if current_used >= allocated:
				excess_part = duration
			elif (current_used + duration) > allocated:
				excess_part = (current_used + duration) - allocated
			else:
				excess_part = 0.0

			current_used += duration
			usage.used_hours += duration

			if excess_part > 0:
				usage.excess_hours += excess_part
				user = _get_row_value(log, "user")
				rate = flt(member_rates.get(user))

				if not rate:
					missing_rate_users.add(user)

				usage.excess_amount += excess_part * rate

		usage.missing_rate_users = sorted(user for user in missing_rate_users if user)
		usage_by_schedule[schedule_name] = usage

	return usage_by_schedule

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

		member_rates = _get_case_member_rates(self.name)
		usage_by_schedule = _calculate_retainer_schedule_usage(self.retainer_schedules, self.time_logs, member_rates)

		for schedule in self.retainer_schedules:
			usage = usage_by_schedule.get(schedule.schedule_name) or frappe._dict()
			schedule.used_hours = usage.get("used_hours", 0.0)
			schedule.excess_hours = usage.get("excess_hours", 0.0)
			schedule.excess_amount = usage.get("excess_amount", 0.0)

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
				"excess_hours": 0,
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
	member_rates = _get_case_member_rates(case.name)
	usage_by_schedule = _calculate_retainer_schedule_usage(case.retainer_schedules, case.time_logs, member_rates)

	for schedule in case.retainer_schedules:
		usage = usage_by_schedule.get(schedule.schedule_name) or frappe._dict()
		schedule.used_hours = usage.get("used_hours", 0.0)
		schedule.excess_hours = usage.get("excess_hours", 0.0)
		schedule.excess_amount = usage.get("excess_amount", 0.0)

	schedule_row = next((s for s in case.retainer_schedules if s.schedule_name == schedule_name), None)
	if not schedule_row:
		frappe.throw("Invalid Schedule Period selected")

	schedule_usage = usage_by_schedule.get(schedule_name) or frappe._dict()
	missing_rate_users = schedule_usage.get("missing_rate_users") or []
	if missing_rate_users:
		frappe.throw(
			"Cannot invoice excess retainer hours because billing rates are missing for: {0}. "
			"Set billing rates in the Case Team Members table and try again.".format(", ".join(missing_rate_users))
		)

	for schedule in case.retainer_schedules:
		if schedule.name:
			schedule.db_update()

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
	if flt(schedule_row.excess_amount) > 0:
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
