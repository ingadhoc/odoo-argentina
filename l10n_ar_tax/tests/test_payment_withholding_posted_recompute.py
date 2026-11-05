from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentWithholdingPostedRecompute(L10nArTaxPaymentCommon):
    """The withholdings of a posted payment keep their base and amount when something forces their recompute.

    Case: a bill is paid one cent short and a second payment pays that cent. The first payment carries a negative
    advance (-0.01) and the bill residual is 0 by now, so recomputing its withholding base used to raise the
    "selected debt" UserError (and, without the advance, to rewrite the base from the current residual).
    """

    def setUp(self):
        super().setUp()
        state_caba = self.env.ref("base.state_ar_c")
        self._auto_fiscal_position(self.tax_iibb_untaxed, state_caba)
        self.partner_tax = self._set_partner_aliquot(self.tax_iibb_untaxed, -2.5)
        self.delivery_address = self._create_delivery_address(state_caba)

    def _bill(self, document_number):
        return self._create_bill(500000.0, document_number, partner_shipping_id=self.delivery_address.id)

    def _force_recompute(self, line):
        # what a raw SQL re-map does from an upgrade script: flag the dependents of tax_id and flush them. The cache
        # is dropped first, as in a fresh upgrade process
        self.env.invalidate_all()
        line.modified(["tax_id"])
        self.env.flush_all()

    def test_posted_partial_payment_keeps_withholding_on_recompute(self):
        bill = self._bill("1-130058")
        payment = self._create_payment(bill, to_pay_amount=bill.amount_total - 0.01)
        line = payment.withholding_line_ids
        self.assertEqual(line.tax_id, self.partner_tax)
        self.assertAlmostEqual(payment.withholdable_advanced_amount, -0.01)
        base_amount, amount = line.base_amount, line.amount

        self._create_payment(bill, to_pay_amount=bill.amount_residual)
        self.assertTrue(bill.currency_id.is_zero(bill.amount_residual))

        self._force_recompute(line)
        self.assertEqual(line.base_amount, base_amount)
        self.assertEqual(line.amount, amount)
        self._assert_entry_withholding(payment, self.partner_tax, amount)

    def test_posted_full_payment_keeps_withholding_on_recompute(self):
        """Without an advance nothing raises: the base used to be silently rewritten from the residual, now 0."""
        bill = self._bill("1-130059")
        payment = self._create_payment(bill)
        line = payment.withholding_line_ids
        self._assert_withholding(payment, self.partner_tax, 500000.0, 12500.0)
        self.assertTrue(bill.currency_id.is_zero(payment.withholdable_advanced_amount))
        self.assertTrue(bill.currency_id.is_zero(bill.amount_residual))

        self._force_recompute(line)
        self._assert_withholding(payment, self.partner_tax, 500000.0, 12500.0)
        self._assert_entry_withholding(payment, self.partner_tax, 12500.0)
