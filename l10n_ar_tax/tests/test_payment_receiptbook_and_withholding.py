from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentReceiptbookAndWithholding(L10nArTaxPaymentCommon):
    """The journal entry of a supplier payment with withholdings: amounts, currencies, rounding, and the cycle of
    reset to draft, edit and post again."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1 USD = 100 ARS on the date of the tests
        cls.usd = cls.setup_other_currency("USD", rates=[("2022-12-31", 0.01)])
        cls.usd_bank_journal = cls.env["account.journal"].create(
            {"name": "Bank USD", "type": "bank", "code": "BUSD", "currency_id": cls.usd.id}
        )

    def _assert_no_balancing_line(self, payment):
        self.assertTrue(payment.move_id.currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))))
        self.assertFalse(
            payment.move_id.line_ids.filtered(lambda x: "automatic balancing" in (x.name or "").lower()),
            "The entry must balance by itself, without an automatic balancing line",
        )

    def test_custom_accounting_rate_with_withholdings(self):
        """A USD bill paid from a USD journal at a rate the user edits: the whole entry is valued at that rate, the
        bank pays the net amount and the debt is settled for the gross one."""
        bill = self._create_bill(1000.0, "1-100", currency_id=self.usd.id)
        payment = self._create_payment(
            bill, self.tax_iibb_untaxed, post=False, journal=self.usd_bank_journal, amount=bill.amount_total
        )
        self._assert_withholding(payment, self.tax_iibb_untaxed, 1000.0, 30.0)

        payment.accounting_rate *= 0.9999
        rate = payment.accounting_rate
        payment.action_post()

        lines = payment.move_id.line_ids
        liquidity = lines.filtered(lambda x: x.account_id == payment.outstanding_account_id)
        payable = lines.filtered(lambda x: x.account_type == "liability_payable")
        self.assertAlmostEqual(liquidity.amount_currency, -1180.0, places=2)
        self.assertAlmostEqual(liquidity.balance, payment.company_currency_id.round(-1180.0 / rate), places=2)
        self.assertAlmostEqual(payable.amount_currency, 1210.0, places=2)
        self.assertAlmostEqual(
            sum(lines.filtered(lambda x: x.tax_line_id == self.tax_iibb_untaxed).mapped("amount_currency")),
            -30.0,
            places=2,
        )
        self._assert_no_balancing_line(payment)

    def test_foreign_currency_withholding_balance_precision(self):
        """The withholding of a USD payment goes in USD (the payment currency, as account_payment_pro decided) and its
        ARS balance is the one of the line at the payment rate, without the rounding loss of a USD -> ARS round trip.
        Before, a balance like 84,894.75 came back as 60 USD -> 84,900 and needed a balancing line."""
        bill = self._create_bill(500.0, "1-200", currency_id=self.usd.id)
        payment = self._create_payment(
            bill, self.tax_iibb_untaxed, post=False, journal=self.usd_bank_journal, amount=bill.amount_total
        )
        line = self._assert_withholding(payment, self.tax_iibb_untaxed, 500.0, 15.0)
        self.assertEqual(line.l10n_ar_amount, 1500.0)
        payment.action_post()

        tax_lines = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id == self.tax_iibb_untaxed)
        self.assertEqual(tax_lines.currency_id, self.usd)
        self.assertAlmostEqual(sum(tax_lines.mapped("amount_currency")), -15.0, places=2)
        self.assertAlmostEqual(sum(tax_lines.mapped("balance")), -1500.0, places=2)
        self._assert_no_balancing_line(payment)

    def test_create_vendor_payment_with_receiptbook_and_withholdings(self):
        """A draft payment has no entry name yet. Posted, the bank pays the net amount (605,000 - 50,000), the debt
        is settled for the gross one and the withholding base goes in and out of its account."""
        self.tax_iibb_untaxed.amount = -10
        bill = self._create_bill(500000.0, "1-2")
        payment = self._create_payment(bill, self.tax_iibb_untaxed, post=False)
        self.assertFalse(payment.move_id.name)
        payment.action_post()
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {"debit": 0.0, "credit": 555000.0},
                {"debit": 0.0, "credit": 500000.0},
                {"debit": 0.0, "credit": 50000.0},
                {"debit": 500000.0, "credit": 0.0},
                {"debit": 605000.0, "credit": 0.0},
            ],
        )

    def test_withholding_amounts(self):
        """Under 'round_globally', 391,683 * 4.5% = 17,625.735 is withheld as 17,625.74, on the line and on the entry."""
        self.env.company.sudo().tax_calculation_rounding_method = "round_globally"
        self.tax_iibb_untaxed.amount = -4.5
        payment = self._create_payment(self._create_bill(391683.0, "2-5"), self.tax_iibb_untaxed)
        self._assert_withholding(payment, self.tax_iibb_untaxed, 391683.0, 17625.74)
        self._assert_entry_withholding(payment, self.tax_iibb_untaxed, 17625.74)

    def _check_draft_delete_entry_and_post(self, tax, document_number, amount):
        """Reset a posted payment to draft, delete its entry and post it again, as support fixes a wrong entry: the
        draft keeps the withholding, and posting generates a new entry with the withholding on its account, balanced
        by itself, and the bill stays paid."""
        bill = self._create_bill(500000.0, document_number)
        payment = self._create_payment(bill, tax)
        self._assert_entry_withholding(payment, tax, amount)
        old_move_id = payment.move_id.id

        payment.action_draft()
        # back in draft the entry keeps the withholding as computed, without a balancing line
        self.assertEqual(payment.move_id.state, "draft")
        self._assert_entry_withholding(payment, tax, amount)
        self._assert_no_balancing_line(payment)

        payment.move_id.unlink()
        self.assertEqual(payment.state, "draft")
        self.assertFalse(payment.move_id)

        payment.action_post()
        self.assertEqual(payment.move_id.state, "posted")
        self.assertNotEqual(payment.move_id.id, old_move_id)
        self._assert_entry_withholding(payment, tax, amount)
        self._assert_no_balancing_line(payment)
        self.assertIn(bill.payment_state, ("paid", "in_payment"))

    def test_draft_delete_entry_and_post_iibb(self):
        """IIBB 3% on 500,000."""
        self._check_draft_delete_entry_and_post(self.tax_iibb_untaxed, "1-3001", 15000.0)

    def test_draft_delete_entry_and_post_earnings_scale(self):
        """Earnings with scale (regimen 110) on 500,000."""
        self._check_draft_delete_entry_and_post(self.tax_earnings_scale, "1-3002", 140780.0)
