import unittest
from unittest.mock import patch

import frappe

from law_management.law_management.doctype.legal_bill.legal_bill import (
	LegalBill,
	_format_invoice_name,
	_get_invoice_series_key,
	_get_invoice_year,
)


class TestLegalBillNaming(unittest.TestCase):
	def test_invoice_name_uses_requested_format(self):
		self.assertEqual(_format_invoice_name("2026", "001"), "TBeST/INV/001/2026")

	def test_invoice_year_comes_from_bill_date(self):
		self.assertEqual(_get_invoice_year("2027-01-01"), "2027")

	def test_invoice_series_key_includes_year_for_annual_reset(self):
		self.assertEqual(_get_invoice_series_key("2026"), "TBeST/INV/2026/")

	def test_autoname_sets_invoice_number_from_bill_date_year(self):
		bill = frappe._dict(bill_date="2026-06-14")

		with patch(
			"law_management.law_management.doctype.legal_bill.legal_bill._generate_invoice_name",
			return_value="TBeST/INV/001/2026",
		) as generate_invoice_name:
			LegalBill.autoname(bill)

		generate_invoice_name.assert_called_once_with("2026")
		self.assertEqual(bill.name, "TBeST/INV/001/2026")
