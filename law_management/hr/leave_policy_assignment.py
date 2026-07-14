import frappe
from frappe import _
from frappe.utils import add_days, add_years, flt, getdate, nowdate

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	LeavePolicyAssignment,
)

ETHIOPIAN_ANNUAL_LEAVE_BASE_DAYS = 16
ETHIOPIAN_ANNUAL_LEAVE_INCREMENT_YEARS = 2


class LawManagementLeavePolicyAssignment(LeavePolicyAssignment):
	def set_dates(self):
		if self.assignment_based_on == "Joining Date":
			self.effective_from, self.effective_to = get_current_work_year_dates(self.employee)
			return

		super().set_dates()

	def get_new_leaves(self, annual_allocation, leave_details, date_of_joining):
		if is_ethiopian_annual_leave_type(leave_details.name):
			from frappe.model.meta import get_field_precision

			precision = get_field_precision(
				frappe.get_meta("Leave Allocation").get_field("new_leaves_allocated")
			)
			return flt(
				get_ethiopian_annual_leave_entitlement(
					self.employee,
					self.effective_from,
					annual_allocation=annual_allocation,
				),
				precision,
			)

		return super().get_new_leaves(annual_allocation, leave_details, date_of_joining)


@frappe.whitelist()
def get_joining_date_work_year(employee, as_of_date=None):
	effective_from, effective_to = get_current_work_year_dates(employee, as_of_date=as_of_date)
	return {
		"effective_from": effective_from,
		"effective_to": effective_to,
		"work_year": get_work_year_number(employee, effective_from),
	}


@frappe.whitelist()
def get_ethiopian_annual_leave_entitlement(employee, effective_from=None, annual_allocation=None):
	work_year = get_work_year_number(employee, effective_from)
	base_days = max(flt(annual_allocation), ETHIOPIAN_ANNUAL_LEAVE_BASE_DAYS)
	service_increments = max(work_year - 1, 0) // ETHIOPIAN_ANNUAL_LEAVE_INCREMENT_YEARS
	return base_days + service_increments


def get_current_work_year_dates(employee, as_of_date=None):
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not date_of_joining:
		frappe.throw(_("Date of Joining is required for Employee {0}.").format(frappe.bold(employee)))

	joining_date = getdate(date_of_joining)
	as_of = getdate(as_of_date or getattr(frappe.flags, "current_date", None) or nowdate())

	if joining_date > as_of:
		return joining_date, getdate(add_days(add_years(joining_date, 1), -1))

	effective_from = _same_month_day(joining_date, as_of.year)
	if effective_from > as_of:
		effective_from = _same_month_day(joining_date, as_of.year - 1)

	effective_to = getdate(add_days(add_years(effective_from, 1), -1))
	return effective_from, effective_to


def get_work_year_number(employee, effective_from=None):
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not date_of_joining:
		return None

	joining_date = getdate(date_of_joining)
	effective_from = getdate(effective_from) if effective_from else get_current_work_year_dates(employee)[0]
	return max(effective_from.year - joining_date.year + 1, 1)


def is_ethiopian_annual_leave_type(leave_type):
	return (leave_type or "").strip().lower().startswith("annual leave")


def _same_month_day(source_date, year):
	try:
		return source_date.replace(year=year)
	except ValueError:
		return source_date.replace(year=year, day=28)
