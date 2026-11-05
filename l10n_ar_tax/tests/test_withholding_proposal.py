from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestWithholdingProposal(L10nArTaxPaymentCommon):
    """A draft supplier payment proposes its withholdings from its fiscal position, with the base over the debt it
    pays. The expected numbers were taken from 19.0 with the same fixtures (company RI, 2023-01-01, ARS)."""

    def test_earnings_scale(self):
        bill = self._create_bill(1000000.0, "1-1")
        payment = self._create_payment(bill, self.tax_earnings_scale, post=False)
        self._assert_withholding(payment, self.tax_earnings_scale, 1000000.0, 295780.0)
        self.assertEqual(payment.state, "draft")

    def test_earnings_two_payments_same_month(self):
        payment_1 = self._create_payment(
            self._create_bill(500000.0, "1-1", tax_ids=self.tax_no_gravado_purchase), self.tax_earnings
        )
        self._assert_withholding(payment_1, self.tax_earnings, 500000.0, 29527.80)

        payment_2 = self._create_payment(
            self._create_bill(500000.0, "1-2", tax_ids=self.tax_no_gravado_purchase), self.tax_earnings, post=False
        )
        self._assert_withholding(payment_2, self.tax_earnings, 500000.0, 30000.0)

    def test_ratio(self):
        self.tax_iibb_untaxed.ratio = 50.0
        payment = self._create_payment(self._create_bill(1000.0, "1-1"), self.tax_iibb_untaxed, post=False)
        self._assert_withholding(payment, self.tax_iibb_untaxed, 500.0, 15.0)

    def test_iibb_total_and_untaxed(self):
        bill = self._create_bill(1000.0, "1-1")
        payment = self._create_payment(bill, self.tax_iibb_untaxed, post=False)
        self._assert_withholding(payment, self.tax_iibb_untaxed, 1000.0, 30.0)

        self.tax_iibb_untaxed.l10n_ar_withholding_tax_type = "iibb_total"
        payment = self._create_payment(bill, self.tax_iibb_untaxed, post=False)
        self._assert_withholding(payment, self.tax_iibb_untaxed, 1210.0, 36.30)

    def test_payment_entry_is_gross(self):
        """The payment amount is the debt (gross): the bank pays the net, the withholding goes to its account."""
        bill = self._create_bill(1000.0, "1-1")
        payment = self._create_payment(bill, self.tax_iibb_untaxed)
        line = self._assert_withholding(payment, self.tax_iibb_untaxed, 1000.0, 30.0)
        self.assertTrue(line.name and line.name != "/")
        self.assertAlmostEqual(payment.amount, 1210.0)
        self.assertAlmostEqual(payment.withholding_net_amount, 1180.0)
        self.assertEqual(payment.withhold, "withhold_pay")
        moves = payment.move_id.line_ids
        self.assertAlmostEqual(
            sum(moves.filtered(lambda x: x.account_id == self.withholding_account).mapped("balance")), -30.0
        )
        self.assertAlmostEqual(
            sum(moves.filtered(lambda x: x.account_id.account_type == "liability_payable").mapped("balance")), 1210.0
        )
        self.assertTrue(bill.currency_id.is_zero(bill.amount_residual))

    def test_zero_withholding_line_dropped_on_post(self):
        self.tax_iibb_untaxed.l10n_ar_payment_minimum_threshold = 5000.0
        payment = self._create_payment(self._create_bill(1000.0, "1-1"), self.tax_iibb_untaxed, post=False)
        self._assert_withholding(payment, self.tax_iibb_untaxed, 1000.0, 0.0)
        payment.action_post()
        self.assertFalse(payment.withholding_line_ids)
        self.assertAlmostEqual(payment.amount, 1210.0)

    def test_earnings_accumulation_by_legal_entity(self):
        """The head office and a branch share the CUIT, so each one sees what the other paid and withheld this month."""
        head_office = self.env.company
        branch = self.env["res.company"].create(
            {"name": "Sucursal", "parent_id": head_office.id, "country_id": head_office.country_id.id}
        )
        branch.withholding_tax_base_account_id = head_office.withholding_tax_base_account_id
        self.res_partner_adhoc.with_company(
            branch
        ).property_account_payable_id = self.res_partner_adhoc.property_account_payable_id
        branch_journal = self.env["account.journal"].create(
            {"name": "Bank Branch", "type": "bank", "code": "BKBR", "company_id": branch.id}
        )
        self.env.user.company_ids |= branch
        branch_bill = self._create_bill(500000.0, "1-2", tax_ids=self.tax_no_gravado_purchase, company=branch)

        payment = self._create_payment(
            self._create_bill(500000.0, "1-1", tax_ids=self.tax_no_gravado_purchase), self.tax_earnings
        )
        self._assert_withholding(payment, self.tax_earnings, 500000.0, 29527.80)

        payment = self._create_payment(branch_bill, self.tax_earnings, journal=branch_journal)
        self.assertEqual(payment.company_id, branch)
        self._assert_withholding(payment, self.tax_earnings, 500000.0, 30000.0)

        payment = self._create_payment(
            self._create_bill(500000.0, "1-3", tax_ids=self.tax_no_gravado_purchase), self.tax_earnings, post=False
        )
        self._assert_withholding(payment, self.tax_earnings, 500000.0, 30000.0)

    def test_certificate_and_receipt_show_the_withholding(self):
        payment = self._create_payment(self._create_bill(1000.0, "1-1"), self.tax_iibb_untaxed)
        line = self._assert_withholding(payment, self.tax_iibb_untaxed, 1000.0, 30.0)

        certificate = (
            self.env["ir.actions.report"]
            ._render_qweb_html("l10n_ar_tax.action_report_withholding_certificate", line.ids)[0]
            .decode()
        )
        self.assertIn(line.name, certificate)
        self.assertIn('<span class="oe_currency_value">30.00</span>', certificate)
        self.assertIn('<span class="oe_currency_value">1,000.00</span>', certificate)

        receipt = (
            self.env["ir.actions.report"]
            ._render_qweb_html("account.action_report_payment_receipt", payment.ids)[0]
            .decode()
        )
        self.assertIn(self.tax_iibb_untaxed.name, receipt)
