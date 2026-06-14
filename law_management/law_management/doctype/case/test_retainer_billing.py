import unittest
from unittest.mock import patch

import frappe

from law_management.law_management.doctype.case.case import (
	Case,
	_calculate_retainer_schedule_usage,
	_get_invalid_time_log_users,
	_get_member_billing_rate,
)


class TestRetainerBilling(unittest.TestCase):
	def test_standard_role_rates_are_used_when_custom_rate_is_missing(self):
		self.assertEqual(_get_member_billing_rate(frappe._dict(role="Partner", billing_rate=0)), 250)
		self.assertEqual(_get_member_billing_rate(frappe._dict(role="Senior Associate", billing_rate=0)), 230)
		self.assertEqual(_get_member_billing_rate(frappe._dict(role="Associate", billing_rate=0)), 200)
		self.assertEqual(_get_member_billing_rate(frappe._dict(role="Junior Associate", billing_rate=0)), 150)

	def test_custom_rate_overrides_standard_role_rate(self):
		rate = _get_member_billing_rate(frappe._dict(role="Associate", billing_rate=175))

		self.assertEqual(rate, 175)

	def test_time_log_users_must_be_case_team_members(self):
		invalid_users = _get_invalid_time_log_users(
			team_members=[
				frappe._dict(user="member@example.com"),
			],
			time_logs=[
				frappe._dict(user="member@example.com"),
				frappe._dict(user="outsider@example.com"),
			],
		)

		self.assertEqual(invalid_users, ["outsider@example.com"])

	def test_time_log_users_allow_multiple_logs_by_team_members(self):
		invalid_users = _get_invalid_time_log_users(
			team_members=[
				frappe._dict(user="member@example.com"),
				frappe._dict(user="second@example.com"),
			],
			time_logs=[
				frappe._dict(user="member@example.com"),
				frappe._dict(user="second@example.com"),
				frappe._dict(user="member@example.com"),
			],
		)

		self.assertEqual(invalid_users, [])

	def test_case_validation_rejects_time_log_users_outside_team(self):
		case = frappe._dict(
			team_members=[frappe._dict(user="member@example.com")],
			time_logs=[frappe._dict(user="outsider@example.com")],
		)

		with patch(
			"law_management.law_management.doctype.case.case.frappe.throw",
			side_effect=frappe.ValidationError("Only case team members can log time on this case."),
		) as throw:
			with self.assertRaises(frappe.ValidationError):
				Case.validate_time_log_users(case)

		throw.assert_called_once()
		self.assertIn("Only case team members can log time on this case.", throw.call_args.args[0])

	def test_excess_hours_are_split_and_billed(self):
		usage_by_schedule = _calculate_retainer_schedule_usage(
			retainer_schedules=[
				frappe._dict(
					schedule_name="Period 1",
					start_date="2026-01-01",
					end_date="2026-03-31",
					allocated_hours=10,
				)
			],
			time_logs=[
				frappe._dict(date="2026-01-05", user="lawyer@example.com", log_hours=6, log_minutes=0, idx=1),
				frappe._dict(date="2026-01-06", user="lawyer@example.com", log_hours=5, log_minutes=0, idx=2),
			],
			member_rates={"lawyer@example.com": 100},
		)

		usage = usage_by_schedule["Period 1"]
		self.assertEqual(usage.used_hours, 11)
		self.assertEqual(usage.excess_hours, 1)
		self.assertEqual(usage.excess_amount, 100)
		self.assertEqual(usage.missing_rate_users, [])

	def test_missing_rate_is_reported_for_excess_time(self):
		usage_by_schedule = _calculate_retainer_schedule_usage(
			retainer_schedules=[
				frappe._dict(
					schedule_name="Period 1",
					start_date="2026-01-01",
					end_date="2026-03-31",
					allocated_hours=1,
				)
			],
			time_logs=[
				frappe._dict(date="2026-01-05", user="missing@example.com", log_hours=2, log_minutes=0, idx=1)
			],
			member_rates={},
		)

		usage = usage_by_schedule["Period 1"]
		self.assertEqual(usage.used_hours, 2)
		self.assertEqual(usage.excess_hours, 1)
		self.assertEqual(usage.excess_amount, 0)
		self.assertEqual(usage.missing_rate_users, ["missing@example.com"])
