# © ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestWithholdingRedraft(L10nArTaxPaymentCommon):
    """A supplier payment whose earnings withholding is 0 (under the non taxable amount) goes back to draft and is
    posted again, with the entry as the payment computed it."""

    def setUp(self):
        super().setUp()
        bill = self._create_bill(5000.0, "1-764361")
        self.payment = self._create_payment(bill, self.tax_iibb_untaxed | self.tax_earnings)
        self._assert_withholding(self.payment, self.tax_earnings, 5000.0, 0.0)

    def _earnings_tax_lines(self):
        return self.payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.tax_earnings)

    def test_the_draft_entry_does_not_withhold_the_zero_earnings(self):
        self.payment.action_draft()

        self.assertFalse(self._earnings_tax_lines(), "the tax engine must not rebuild the earnings line at its rate")
        self.assertEqual(sum(self.payment.move_id.line_ids.mapped("balance")), 0.0)

    def test_the_draft_payment_can_be_posted_again(self):
        self.payment.action_draft()

        self.payment.action_post()

        self.assertEqual(self.payment.move_id.state, "posted")
        self.assertFalse(self._earnings_tax_lines())
        self._assert_entry_withholding(self.payment, self.tax_iibb_untaxed, 150.0)
