import unittest
from unittest.mock import Mock, patch

import frappe
from law_management.law_management.doctype.legal_bill import legal_bill

from law_management.law_management.doctype.legal_bill.legal_bill import (
	DEFAULT_CURRENCY,
	LegalBill,
	_format_invoice_name,
	_generate_invoice_name,
	_get_invoice_series_key,
	_get_invoice_year,
)


class TestLegalBillNaming(unittest.TestCase):
	def test_invoice_name_uses_requested_format(self):
		self.assertEqual(_format_invoice_name("2026", "001"), "TBeST/INV/001/2026")

	def test_invoice_year_uses_ethiopian_fiscal_year_boundary(self):
		self.assertEqual(_get_invoice_year("2026-07-07"), "2026")
		self.assertEqual(_get_invoice_year("2026-07-08"), "2027")
		self.assertEqual(_get_invoice_year("2027-01-01"), "2027")

	def test_invoice_series_key_includes_year_for_annual_reset(self):
		self.assertEqual(_get_invoice_series_key("2026"), "TBeST/INV/2026/")

	def test_invoice_series_lookup_uses_name_ordering(self):
		db = Mock()
		db.get_value.return_value = 0

		with (
			patch.dict(legal_bill.frappe.__dict__, {"db": db}),
			patch("law_management.law_management.doctype.legal_bill.legal_bill.make_autoname", return_value="TBeST/INV/2026/001"),
		):
			self.assertEqual(_generate_invoice_name("2026"), "TBeST/INV/001/2026")

		db.get_value.assert_called_once_with("Series", "TBeST/INV/2026/", "current", order_by="name", for_update=True)

	def test_autoname_sets_invoice_number_from_bill_date_fiscal_year(self):
		bill = frappe._dict(bill_date="2026-07-08")

		with patch(
			"law_management.law_management.doctype.legal_bill.legal_bill._generate_invoice_name",
			return_value="TBeST/INV/001/2027",
		) as generate_invoice_name:
			LegalBill.autoname(bill)

		generate_invoice_name.assert_called_once_with("2027")
		self.assertEqual(bill.name, "TBeST/INV/001/2027")

	def test_legal_bill_defaults_to_usd(self):
		bill = frappe._dict(currency=None, conversion_rate=None)

		LegalBill.set_default_currency(bill)

		self.assertEqual(bill.currency, DEFAULT_CURRENCY)
		self.assertEqual(bill.conversion_rate, 1.0)

	def test_legal_bill_items_follow_invoice_currency(self):
		bill = frappe._dict(
			currency="USD",
			conversion_rate=1.0,
			items=[
				frappe._dict(currency="ETB", qty=1, rate=250, amount=250, etb_amount=None),
				frappe._dict(currency=None, qty=1, rate=100, amount=100, etb_amount=None),
			],
			grand_total=0,
		)

		LegalBill.set_item_currency_and_totals(bill)

		self.assertEqual([item.currency for item in bill.get("items")], ["USD", "USD"])
		self.assertEqual(bill.grand_total, 350)
