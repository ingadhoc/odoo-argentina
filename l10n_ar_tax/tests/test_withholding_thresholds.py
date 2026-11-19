from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestWithholdingThresholds(L10nArTaxPaymentCommon):
    """The minimum thresholds of a withholding, on the payment registered from a bill of 100 + 21% VAT.

    Non earnings regimes go through three gates, in this order: the payment amount
    (l10n_ar_payment_minimum_threshold), the base (l10n_ar_base_minimum_threshold) and the withholding amount
    (l10n_ar_minimum_threshold). Earnings only deduct the non taxable amount, accumulated over the month.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_iibb_half = cls._create_withholding_tax(
            "Test IIBB WTH 0.5%",
            -0.5,
            l10n_ar_withholding_tax_type="iibb_untaxed",
            l10n_ar_state_id=cls.env.ref("base.state_ar_c").id,
        )
        cls.tax_earnings_10 = cls._create_withholding_tax(
            "Test Profits WTH 10%",
            -10,
            l10n_ar_withholding_tax_type="earnings",
            l10n_ar_code="EARN_THR_TEST",
            l10n_ar_non_taxable_amount=100.0,
        )

    def _draft_payment(self, tax, price_unit=100.0, document_number="1-1"):
        return self._create_payment(self._create_bill(price_unit, document_number), tax, post=False)

    def test_01_iibb_payment_threshold_applies(self):
        """The payment (121) is over the payment threshold (105): 3% over the untaxed base of 100."""
        self.tax_iibb_untaxed.l10n_ar_payment_minimum_threshold = 105
        self._assert_withholding(self._draft_payment(self.tax_iibb_untaxed), self.tax_iibb_untaxed, 100.0, 3.0)

    def test_02_iibb_payment_threshold_blocks(self):
        """The payment (121) does not reach the payment threshold (130): nothing is withheld."""
        self.tax_iibb_untaxed.l10n_ar_payment_minimum_threshold = 130
        self._assert_withholding(self._draft_payment(self.tax_iibb_untaxed), self.tax_iibb_untaxed, 100.0, 0.0)

    def test_03_iibb_base_threshold_blocks(self):
        """The base (100) does not reach the base threshold (105): nothing is withheld."""
        self.tax_iibb_untaxed.l10n_ar_base_minimum_threshold = 105
        self._assert_withholding(self._draft_payment(self.tax_iibb_untaxed), self.tax_iibb_untaxed, 100.0, 0.0)

    def test_04_minimum_amount_threshold_blocks(self):
        """The payment and the base pass their gates, but 0.5% of 100 is under the minimum withholding (10)."""
        self.tax_iibb_half.l10n_ar_base_minimum_threshold = 1
        self.tax_iibb_half.l10n_ar_minimum_threshold = 10
        self._assert_withholding(self._draft_payment(self.tax_iibb_half), self.tax_iibb_half, 100.0, 0.0)

    def test_05_earnings_non_taxable_amount_accumulated(self):
        """Earnings 10% with a non taxable amount of 100. The first payment (base 80) does not reach it and withholds
        nothing; the second one of the month adds the first base: (80 + 80 - 100) * 10% = 6."""
        payment_1 = self._draft_payment(self.tax_earnings_10, price_unit=80.0)
        self._assert_withholding(payment_1, self.tax_earnings_10, 80.0, 0.0)
        payment_1.action_post()
        self.assertTrue(payment_1.withholding_line_ids, "an earnings line is kept at 0: its base accumulates")

        payment_2 = self._draft_payment(self.tax_earnings_10, price_unit=80.0, document_number="1-2")
        self._assert_withholding(payment_2, self.tax_earnings_10, 80.0, 6.0)

    def test_06_zero_withholding_line_removed_on_confirm(self):
        """A line left at 0 by the base threshold is dropped when the payment is confirmed."""
        self.tax_iibb_untaxed.l10n_ar_base_minimum_threshold = 105
        payment = self._draft_payment(self.tax_iibb_untaxed)
        self._assert_withholding(payment, self.tax_iibb_untaxed, 100.0, 0.0)
        payment.action_post()
        self.assertFalse(payment.withholding_line_ids)

    def test_07_nonzero_withholding_line_kept(self):
        """A line that withholds survives the confirmation, with its number."""
        payment = self._draft_payment(self.tax_iibb_untaxed)
        payment.action_post()
        line = self._assert_withholding(payment, self.tax_iibb_untaxed, 100.0, 3.0)
        self.assertTrue(line.name and line.name != "/")
