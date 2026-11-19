from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentWithholdingKeptOnPost(L10nArTaxPaymentCommon):
    """Regression of ticket 113171 (task 65423): posting a supplier payment with the withholdings proposed from its
    fiscal position dropped both the withholdings and the fiscal position.

    The fiscal position is applied by itself from the delivery address of the bill (CABA) and the aliquot comes from
    the one registered on the supplier (2.5%).
    """

    def test_withholding_and_fiscal_position_kept_after_post(self):
        state_caba = self.env.ref("base.state_ar_c")
        fiscal_position = self._auto_fiscal_position(self.tax_iibb_untaxed, state_caba)
        partner_tax = self._set_partner_aliquot(self.tax_iibb_untaxed, -2.5)
        bill = self._create_bill(500000.0, "1-113171", partner_shipping_id=self._create_delivery_address(state_caba).id)

        payment = self._create_payment(bill, post=False)
        self.assertEqual(payment.l10n_ar_fiscal_position_id, fiscal_position)
        line = self._assert_withholding(payment, partner_tax, 500000.0, 12500.0)

        payment.action_post()
        # the deferred constraints of account_payment_pro run on flush, as at the end of a request
        self.env.flush_all()

        self.assertEqual(payment.move_id.state, "posted")
        self.assertEqual(payment.withholding_line_ids, line)
        self._assert_withholding(payment, partner_tax, 500000.0, 12500.0)
        self.assertEqual(payment.l10n_ar_fiscal_position_id, fiscal_position)
        self._assert_entry_withholding(payment, partner_tax, 12500.0)
