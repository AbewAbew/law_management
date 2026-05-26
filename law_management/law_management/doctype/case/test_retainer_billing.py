import unittest

import frappe

from law_management.law_management.doctype.case.case import _calculate_retainer_schedule_usage


class TestRetainerBilling(unittest.TestCase):
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

