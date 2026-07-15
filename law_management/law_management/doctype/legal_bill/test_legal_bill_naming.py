import unittest
from unittest.mock import Mock, patch

import frappe
from law_management.law_management.doctype.legal_bill import legal_bill

from law_management.law_management.doctype.legal_bill.legal_bill import (
	DEFAULT_CURRENCY,
	DEFAULT_RECEIVING_BANK,
	DEFAULT_VAT_RATE,
	LegalBill,
	_format_invoice_name,
	_generate_invoice_name,
	_get_invoice_series_key,
	_get_invoice_year,
	_get_customer_invoice_details,
	_get_wire_account_details,
)


def _test_flt(value, precision=None):
	number = float(value or 0)
	return round(number, precision) if precision is not None else number


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
		bill = frappe._dict(currency=None, conversion_rate=None, vat_rate=None)

		LegalBill.set_default_currency(bill)

		self.assertEqual(bill.currency, DEFAULT_CURRENCY)
		self.assertEqual(bill.conversion_rate, 1.0)
		self.assertEqual(bill.vat_rate, DEFAULT_VAT_RATE)

	def test_customer_invoice_details_use_primary_address_and_contact(self):
		customer = frappe._dict(
			customer_name="Acme PLC",
			customer_primary_address="Acme-Billing",
			primary_address="Fallback address",
			customer_primary_contact="CONTACT-001",
			email_id="accounts@acme.test",
		)
		contact = frappe._dict(full_name="Almaz Tesfaye", email_id="almaz@acme.test")
		db = Mock()
		db.get_value.return_value = customer

		with (
			patch.dict(legal_bill.frappe.__dict__, {"db": db}),
			patch.object(legal_bill, "get_address_display", return_value="Addis Ababa<br>Ethiopia"),
			patch.object(legal_bill.frappe, "get_cached_doc", return_value=contact),
		):
			details = _get_customer_invoice_details("CUST-001")

		self.assertEqual(details["customer_name"], "Acme PLC")
		self.assertEqual(details["billing_address"], "Acme-Billing")
		self.assertEqual(details["billing_address_display"], "Addis Ababa<br>Ethiopia")
		self.assertEqual(details["attention_to"], "Almaz Tesfaye")
		self.assertEqual(details["attention_email"], "almaz@acme.test")

	def test_wire_account_follows_bank_and_currency(self):
		awash_usd = _get_wire_account_details("Awash Bank", "USD")
		self.assertEqual(awash_usd["bank_account_name"], "TBeST Law USD Account")
		self.assertEqual(awash_usd["bank_account_number"], "021141025627100")

		awash_etb = _get_wire_account_details("Awash Bank", "ETB")
		self.assertEqual(awash_etb["bank_account_name"], "TBeST Law Birr Account")
		self.assertEqual(awash_etb["bank_account_number"], "013041025627100")

		sinqee_usd = _get_wire_account_details("Sinqee Bank", "USD")
		self.assertEqual(sinqee_usd["bank_account_number"], "2051130081315")

		sinqee_etb = _get_wire_account_details("Sinqee Bank", "ETB")
		self.assertEqual(sinqee_etb["bank_account_number"], "1051130080113")

	def test_awash_wire_account_includes_invoice_details(self):
		details = _get_wire_account_details("Awash Bank", "ETB")

		self.assertEqual(details["bank_swift_code"], "AWINETAA XXX")
		self.assertEqual(details["bank_name_and_address"], "AWASH BANK S.C")
		self.assertEqual(details["bank_branch"], "Millennium Akababi")
		self.assertEqual(details["bank_account_holder"], "TBeST Law LLP")
		self.assertEqual(details["bank_account_holder_tin"], "0081829025")

	def test_legal_bill_sets_wire_account_details(self):
		bill = frappe._dict(
			receiving_bank=None,
			currency="USD",
			bank_account_name=None,
			bank_account_number=None,
			bank_name_and_address=None,
			bank_branch=None,
			bank_swift_code=None,
			bank_account_holder=None,
			bank_account_holder_tin=None,
		)

		LegalBill.set_wire_transfer_details(bill)

		self.assertEqual(bill.receiving_bank, DEFAULT_RECEIVING_BANK)
		self.assertEqual(bill.bank_account_name, "TBeST Law USD Account")
		self.assertEqual(bill.bank_account_number, "021141025627100")
		self.assertEqual(bill.bank_swift_code, "AWINETAA XXX")
		self.assertEqual(bill.bank_name_and_address, "AWASH BANK S.C")
		self.assertEqual(bill.bank_branch, "Millennium Akababi")
		self.assertEqual(bill.bank_account_holder, "TBeST Law LLP")
		self.assertEqual(bill.bank_account_holder_tin, "0081829025")

	def test_legal_bill_items_follow_invoice_currency(self):
		bill = frappe._dict(
			currency="USD",
			conversion_rate=1.0,
			items=[
				frappe._dict(currency="ETB", qty=1, rate=250, amount=250, etb_amount=None),
				frappe._dict(currency=None, qty=1, rate=100, amount=100, etb_amount=None),
			],
			apply_vat=1,
			vat_rate=15,
			subtotal=0,
			vat_amount=0,
			grand_total=0,
			in_words=None,
		)

		with (
			patch.object(legal_bill, "flt", side_effect=_test_flt),
			patch.object(legal_bill, "money_in_words", return_value="USD Four Hundred Two and Fifty Cents"),
		):
			LegalBill.set_item_currency_and_totals(bill)

		self.assertEqual([item.currency for item in bill.get("items")], ["USD", "USD"])
		self.assertEqual(bill.subtotal, 350)
		self.assertEqual(bill.vat_amount, 52.5)
		self.assertEqual(bill.grand_total, 402.5)

	def test_legal_bill_can_disable_vat(self):
		bill = frappe._dict(
			currency="USD",
			conversion_rate=1.0,
			items=[frappe._dict(currency="USD", qty=1, rate=100, amount=100, etb_amount=None)],
			apply_vat=0,
			vat_rate=15,
			subtotal=0,
			vat_amount=0,
			grand_total=0,
			in_words=None,
		)

		with (
			patch.object(legal_bill, "flt", side_effect=_test_flt),
			patch.object(legal_bill, "money_in_words", return_value="USD One Hundred only"),
		):
			LegalBill.set_item_currency_and_totals(bill)

		self.assertEqual(bill.subtotal, 100)
		self.assertEqual(bill.vat_amount, 0)
		self.assertEqual(bill.grand_total, 100)
