from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged

TAX_AMOUNT_KEYS = (
    "not_vat_taxes_amount",
    "iibb_perc_amount",
    "mun_perc_amount",
    "intern_tax_amount",
    "other_taxes_amount",
    "vat_perc_amount",
    "profits_perc_amount",
)


@tagged("post_install", "-at_install")
class TestL10nArGetAmounts(TestArCommon):
    """Posted documents report the taxes amounts booked, even if the tax definition changed afterwards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls._create_journal("preprinted")

    def _create_posted_move(self, move_type):
        move = self._create_invoice_ar(
            move_type=move_type,
            partner_id=self.res_partner_adhoc,
            journal_id=self.journal,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_21, price_unit=1000.0, tax_ids=self.tax_21 + self.tax_perc_iibb
                )
            ],
        )
        self._post(move)
        return move

    def _get_amounts(self, move):
        base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
        return move._l10n_ar_get_amounts(base_lines=base_lines)

    def _archive_perception_tax(self):
        """Same state a migration leaves the old tax: archived and fixed in 0."""
        self.tax_perc_iibb.write({"amount_type": "fixed", "amount": 0.0, "active": False})

    def test_invoice_keeps_booked_perception_after_tax_change(self):
        invoice = self._create_posted_move("out_invoice")
        before = self._get_amounts(invoice)
        self.assertTrue(before["iibb_perc_amount"] > 0, "The invoice must have an IIBB perception")

        self._archive_perception_tax()

        after = self._get_amounts(invoice)
        for key in TAX_AMOUNT_KEYS:
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(after["vat_amount"], before["vat_amount"])

    def test_credit_note_keeps_booked_perception_after_tax_change(self):
        refund = self._create_posted_move("out_refund")
        before = self._get_amounts(refund)
        self.assertTrue(before["iibb_perc_amount"] < 0, "A credit note reports its perception as negative")

        self._archive_perception_tax()

        after = self._get_amounts(refund)
        for key in TAX_AMOUNT_KEYS:
            self.assertEqual(after[key], before[key], key)

    def test_draft_invoice_uses_current_tax_definition(self):
        invoice = self._create_invoice_ar(
            partner_id=self.res_partner_adhoc,
            journal_id=self.journal,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_21, price_unit=1000.0, tax_ids=self.tax_21 + self.tax_perc_iibb
                )
            ],
        )
        self.assertTrue(self._get_amounts(invoice)["iibb_perc_amount"] > 0)

        self._archive_perception_tax()

        self.assertEqual(self._get_amounts(invoice)["iibb_perc_amount"], 0.0)
