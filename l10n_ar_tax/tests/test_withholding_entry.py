# © ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.addons.l10n_ar_tax.tests.common import WithholdingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestWithholdingEntry(WithholdingCommon):
    """The entry of a payment with withholdings: one pair of base journal items per base amount, as in 19.0,
    and a posted receipt that goes back to draft without falling out of balance.
    """

    def _posted_payment(self, withholdings):
        payment = self._payment(withholdings=withholdings)
        payment.action_post()
        return payment

    def _posted_receipt(self, amount=1000.0, withholding_base=1000.0, journal=None):
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[amount], taxes=[], post=True)
        payment = self._payment(
            withholding_base=withholding_base,
            tax=self.sale_withholding_tax,
            partner_type="customer",
            payment_type="inbound",
            amount=amount,
            journal_id=(journal or self.bank_journal).id,
            to_pay_move_line_ids=[
                Command.set(
                    invoice.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable").ids
                )
            ],
        )
        payment.action_post()
        return payment

    def test_two_withholdings_over_the_same_base_leave_one_pair(self):
        payment = self._posted_payment([(self.withholding_tax_3, 1000.0), (self.withholding_tax, 1000.0)])

        base_lines = self._base_lines(payment)

        self.assertEqual(len(base_lines), 2, "one base journal item and its counterpart, not one pair per tax")
        self.assertEqual(sorted(base_lines.mapped("balance")), [-1000.0, 1000.0])
        self.assertEqual(len(payment.move_id.line_ids), 6, "bank, payable, two withholdings and the base pair")

    def test_withholdings_over_different_bases_keep_their_own_pair(self):
        payment = self._posted_payment([(self.withholding_tax_3, 1000.0), (self.withholding_tax, 400.0)])

        base_lines = self._base_lines(payment)

        self.assertEqual(len(base_lines), 4, "a different base is a different pair, as in 19.0")
        self.assertEqual(sorted(base_lines.mapped("balance")), [-1000.0, -400.0, 400.0, 1000.0])

    def test_a_single_withholding_still_leaves_its_pair(self):
        payment = self._posted_payment([(self.withholding_tax_3, 1000.0)])

        self.assertEqual(len(self._base_lines(payment)), 2)

    def test_a_posted_receipt_with_a_withholding_goes_back_to_draft(self):
        payment = self._posted_receipt()
        self.assertEqual(payment.move_id.state, "posted")

        payment.action_draft()

        self.assertEqual(payment.state, "draft")
        self.assertEqual(
            sum(payment.move_id.line_ids.mapped("balance")), 0.0, "the entry of the draft payment is balanced"
        )

    def test_the_draft_receipt_can_be_posted_again(self):
        payment = self._posted_receipt()
        payment.action_draft()

        payment.action_post()

        self.assertEqual(payment.move_id.state, "posted")
        self.assertEqual(sum(payment.move_id.line_ids.mapped("balance")), 0.0)

    def test_a_receipt_paid_in_cash_also_goes_back_to_draft(self):
        cash_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company.id), ("type", "=", "cash")], limit=1
        )
        payment = self._posted_receipt(journal=cash_journal)

        payment.action_draft()

        self.assertEqual(payment.state, "draft")
        self.assertEqual(sum(payment.move_id.line_ids.mapped("balance")), 0.0)
