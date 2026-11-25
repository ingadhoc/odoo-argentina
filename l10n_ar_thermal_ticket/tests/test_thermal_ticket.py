from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged

ARCA_REPORT = "l10n_ar_thermal_ticket.report_thermal_invoice_html"
GENERIC_REPORT = "account_thermal_ticket.report_thermal_invoice_html"


@tagged("post_install", "-at_install")
class TestArThermalTicket(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.arca_journal = cls._create_journal("wsfe", {"l10n_ar_afip_pos_number": "1"})
        cls.aux_journal = cls.env["account.journal"].create(
            {
                "name": "Auxiliary",
                "type": "sale",
                "code": "AUX",
                "company_id": cls.company_ri.id,
                "l10n_latam_use_documents": False,
            }
        )
        cls.invoice = cls._make_invoice(cls.arca_journal)

    @classmethod
    def _make_invoice(cls, journal):
        return cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner_cf.id,
                "journal_id": journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_iva_21.id,
                            "quantity": 2.0,
                            "price_unit": 100.0,
                            "discount": 10.0,
                        }
                    )
                ],
            }
        )

    def test_report_name_arca_journal(self):
        self.assertEqual(self.invoice._get_thermal_receipt_report_name(), ARCA_REPORT)

    def test_report_name_journal_without_pos_number(self):
        invoice = self._make_invoice(self.aux_journal)
        self.assertEqual(invoice._get_thermal_receipt_report_name(), GENERIC_REPORT)

    def test_header_partner_is_pos_partner(self):
        pos_partner = self.env["res.partner"].create({"name": "Point of sale", "street": "Another 456"})
        self.arca_journal.l10n_ar_afip_pos_partner_id = pos_partner
        self.assertEqual(self.invoice._get_thermal_header_partner(), pos_partner)

    def test_header_partner_falls_back_to_company(self):
        invoice = self._make_invoice(self.aux_journal)
        self.assertEqual(invoice._get_thermal_header_partner(), self.company_ri.partner_id)

    def test_include_taxes_follows_localization(self):
        for value in (True, False):
            with patch.object(type(self.invoice), "_l10n_ar_include_vat", return_value=value):
                self.assertEqual(self.invoice._thermal_prices_include_taxes(), value)

    def test_line_prices_follow_localization_helper(self):
        line = self.invoice.invoice_line_ids
        for value in (True, False):
            with patch.object(type(self.invoice), "_l10n_ar_include_vat", return_value=value):
                expected = line._l10n_ar_prices_and_taxes()
                prices = line._thermal_line_prices()
            self.assertEqual(prices["price_unit"], expected["price_unit"])
            self.assertEqual(prices["amount"], expected["price_subtotal"])
            self.assertEqual(prices["discount"], 10.0)

    def test_render_arca_ticket(self):
        html, _ = self.env["ir.actions.report"]._render_qweb_html(ARCA_REPORT, self.invoice.ids)
        self.assertIn(self.company_ri.name, html.decode())
