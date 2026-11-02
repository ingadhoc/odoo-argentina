from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestWithholdingProposal(TestArCommon):
    """A draft supplier payment proposes its withholdings from its fiscal position, with the base over the debt it
    pays. The expected numbers were taken from 19.0 with the same fixtures (company RI, 2023-01-01, ARS)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.use_payment_pro = True
        cls.env.company.withholding_tax_base_account_id = cls.env.ref(
            "account.%i_base_tax_account" % cls.env.company.id
        )
        cls.tax_21 = cls.env.ref("account.%s_ri_tax_vat_21_ventas" % cls.env.company.id)
        cls.tax_21_purchase = cls.env.ref("account.%s_ri_tax_vat_21_compras" % cls.env.company.id)
        cls.withholding_account = cls.env["account.account"].create(
            {"name": "Withholdings to pay", "code": "WTH.001", "account_type": "liability_current"}
        )
        cls.withholding_sequence = cls.env["ir.sequence"].create(
            {"implementation": "standard", "name": "tax wth test", "padding": 8, "number_increment": 1}
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]

        cls.tax_earnings_scale = cls._create_withholding_tax(
            "Test Profits WTH regimen 110",
            -1,
            l10n_ar_withholding_tax_type="earnings_scale",
            l10n_ar_scale_id=cls.env.ref("l10n_ar_withholding.normal_scale").id,
            l10n_ar_code="110",
            l10n_ar_non_taxable_amount=10000.0,
        )
        cls.tax_earnings = cls._create_withholding_tax(
            "Test Profits WTH regimen 35",
            -6,
            l10n_ar_withholding_tax_type="earnings",
            l10n_ar_code="35",
            l10n_ar_non_taxable_amount=7870.0,
        )
        cls.tax_iibb_untaxed = cls._create_withholding_tax(
            "Test IIBB WTH 3%",
            -3,
            l10n_ar_withholding_tax_type="iibb_untaxed",
            l10n_ar_state_id=cls.env.ref("base.state_ar_c").id,
        )

    @classmethod
    def _create_withholding_tax(cls, name, amount, **tax_vals):
        return cls.env["account.tax"].create(
            {
                "name": name,
                "amount_type": "percent",
                "amount": amount,
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "withholding_sequence_id": cls.withholding_sequence.id,
                "company_id": cls.env.company.id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.withholding_account.id}),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.withholding_account.id}),
                ],
                **tax_vals,
            }
        )

    def _fiscal_position(self, tax):
        fiscal_position = self.env["account.fiscal.position"].create(
            {"name": "Withholding %s" % tax.name, "company_id": self.env.company.id}
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_position.id,
                "default_tax_id": tax.id,
                "tax_type": "withholding",
                "webservice": False,
            }
        )
        return fiscal_position

    def _create_bill(self, price_unit, document_number, tax_ids=None, company=None, **vals):
        bill = (
            self.env["account.move"]
            .with_company(company or self.env.company)
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": self.res_partner_adhoc.id,
                    "invoice_date": "2023-01-01",
                    "l10n_latam_document_number": document_number,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "price_unit": price_unit,
                                "tax_ids": [Command.set((tax_ids or self.tax_21_purchase).ids)],
                            }
                        )
                    ],
                    **vals,
                }
            )
        )
        bill.action_post()
        return bill

    def _create_payment(self, bill, tax, post=True, journal=None):
        """A supplier payment pro payment of the whole bill, as the register payment action opens it."""
        context = bill.line_ids.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**context)
            .create({"journal_id": (journal or self.bank_journal).id, "date": "2023-01-01"})
        )
        payment.l10n_ar_fiscal_position_id = self._fiscal_position(tax)
        if post:
            payment.action_post()
        return payment

    def _assert_withholding(self, payment, tax, base_amount, amount, ref=None):
        line = payment.withholding_line_ids.filtered(lambda x: x.tax_id == tax)
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.base_amount, base_amount, places=2)
        self.assertAlmostEqual(line.amount, amount, places=2)
        if ref is not None:
            self.assertEqual(line.ref, ref)
        return line

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
