import unittest
from unittest.mock import patch

import frappe

from law_management import approval_notifications


class TestApprovalNotifications(unittest.TestCase):
	def test_unique_keeps_order_and_removes_empty_values(self):
		values = ["a@example.com", "", "b@example.com", "a@example.com", None, "c@example.com"]

		self.assertEqual(
			approval_notifications._unique(values),
			["a@example.com", "b@example.com", "c@example.com"],
		)

	def test_get_configured_leave_approvers_uses_department_list(self):
		doc = frappe._dict(
			doctype="Leave Application",
			employee="EMP-0001",
			department="Legal - TLL",
			leave_approver="partner-a@example.com",
		)

		with (
			patch.object(
				approval_notifications,
				"_get_employee_info",
				return_value=frappe._dict(user_id="employee@example.com", department="Legal - TLL"),
			),
			patch.object(
				approval_notifications.frappe,
				"get_all",
				return_value=[
					frappe._dict(approver="partner-a@example.com"),
					frappe._dict(approver="partner-b@example.com"),
					frappe._dict(approver="employee@example.com"),
				],
			) as get_all,
		):
			approvers = approval_notifications._get_configured_approvers(doc)

		self.assertEqual(approvers, ["partner-a@example.com", "partner-b@example.com"])
		get_all.assert_called_once_with(
			"Department Approver",
			filters={"parent": "Legal - TLL", "parentfield": "leave_approvers"},
			fields=["approver"],
			order_by="idx asc",
		)

	def test_get_configured_expense_approvers_uses_department_list(self):
		doc = frappe._dict(
			doctype="Expense Claim",
			employee="EMP-0002",
			department="Administration - TLL",
			expense_approver="office@example.com",
		)

		with (
			patch.object(
				approval_notifications,
				"_get_employee_info",
				return_value=frappe._dict(user_id="driver@example.com", department="Administration - TLL"),
			),
			patch.object(
				approval_notifications.frappe,
				"get_all",
				return_value=[frappe._dict(approver="office@example.com")],
			) as get_all,
		):
			approvers = approval_notifications._get_configured_approvers(doc)

		self.assertEqual(approvers, ["office@example.com"])
		get_all.assert_called_once_with(
			"Department Approver",
			filters={"parent": "Administration - TLL", "parentfield": "expense_approvers"},
			fields=["approver"],
			order_by="idx asc",
		)

	def test_get_enabled_user_emails_keeps_configured_order(self):
		users = ["partner-b@example.com", "partner-a@example.com", "disabled@example.com"]

		with patch.object(
			approval_notifications.frappe,
			"get_all",
			return_value=[
				frappe._dict(name="partner-a@example.com", email="partner-a@example.com"),
				frappe._dict(name="partner-b@example.com", email="partner-b@example.com"),
			],
		):
			recipients = approval_notifications._get_enabled_user_emails(users)

		self.assertEqual(recipients, ["partner-b@example.com", "partner-a@example.com"])


if __name__ == "__main__":
	unittest.main()
