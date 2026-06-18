# Copyright (c) 2025, Tbest and Contributors
# See license.txt

import unittest
from unittest.mock import Mock, patch

from law_management.law_management.doctype.case import case as case_controller


class TestCase(unittest.TestCase):
	def test_legal_associate_cannot_create_case(self):
		doc = Mock()
		doc.is_new.return_value = True

		with patch.object(case_controller.frappe, "get_roles", return_value=["Legal Associate"]):
			self.assertFalse(case_controller.has_permission(doc, "associate@example.com"))

	def test_legal_partner_can_create_case(self):
		doc = Mock()
		doc.is_new.return_value = True

		with patch.object(case_controller.frappe, "get_roles", return_value=["Legal Partner"]):
			self.assertTrue(case_controller.has_permission(doc, "partner@example.com"))
