from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestRefundReport(TestArCommon):
    """Refunds that share the ARCA document code with the invoice they reverse (e.g. code 60) must show
    their amounts in negative on the printed report (port of odoo/odoo#234040)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_60_lp_a = cls.env.ref("l10n_ar.dc_a_cvl")

    def _create_credit_note_60(self):
        credit_note = self._create_invoice_ar(
            ref="Credit note with document type 60 for refund test",
            move_type="out_refund",
            partner_id=self.res_partner_adhoc,
            company_id=self.company_ri,
            invoice_date="2021-03-20",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_21, price_unit=100.0, quantity=1, tax_ids=self.tax_21
                ),
            ],
        )
        credit_note.l10n_latam_document_type_id = self.doc_60_lp_a
        return credit_note

    def test_get_invoice_totals_for_report_refund_with_same_code(self):
        credit_note = self._create_credit_note_60()
        self.assertTrue(credit_note._l10n_ar_is_refund_invoice())

        self._assert_tax_totals_summary(
            credit_note._l10n_ar_get_invoice_totals_for_report(),
            {
                "same_tax_base": True,
                "currency_id": credit_note.currency_id.id,
                "base_amount_currency": -100.0,
                "tax_amount_currency": -21.0,
                "total_amount_currency": -121.0,
                "subtotals": [
                    {
                        "name": "Untaxed Amount",
                        "base_amount_currency": -100.0,
                        "tax_amount_currency": -21.0,
                        "tax_groups": [
                            {
                                "id": self.tax_21.tax_group_id.id,
                                "base_amount_currency": -100.0,
                                "tax_amount_currency": -21.0,
                                "display_base_amount_currency": -100.0,
                            },
                        ],
                    },
                ],
            },
        )
        # The computed field cache must not be altered by the report adjustments
        self.assertEqual(credit_note.tax_totals["total_amount_currency"], 121.0)

    def test_prices_and_taxes_refund_with_same_code(self):
        credit_note = self._create_credit_note_60()
        values = credit_note.invoice_line_ids._l10n_ar_prices_and_taxes()
        self.assertEqual(values["price_unit"], -100.0)
        self.assertEqual(values["price_net"], -100.0)
        self.assertEqual(values["price_subtotal"], -100.0)

    def test_regular_refund_keeps_positive_amounts(self):
        """A regular credit note (its own document code) keeps positive amounts on the report."""
        credit_note = self._create_invoice_ar(
            move_type="out_refund",
            partner_id=self.res_partner_adhoc,
            company_id=self.company_ri,
            invoice_date="2021-03-20",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_21, price_unit=100.0, quantity=1, tax_ids=self.tax_21
                ),
            ],
        )
        self.assertFalse(credit_note._l10n_ar_is_refund_invoice())
        self.assertEqual(credit_note._l10n_ar_get_invoice_totals_for_report()["total_amount_currency"], 121.0)
        self.assertEqual(credit_note.invoice_line_ids._l10n_ar_prices_and_taxes()["price_subtotal"], 100.0)
