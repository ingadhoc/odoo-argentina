"""Withholdings of supplier payments in foreign currency, one test per case of the payment pro spec (oba-project,
specs/20_ready/pagos/payment-pro-pagos-divisa-retenciones.md).

The base and the amount are computed in company currency (C, ARS), where the AR rules apply, over the debt at the rate
of the payment. Since 20.0 the line keeps them in the payment currency (A), as account_payment_pro decided, and
stores the ARS ones too: the entry, the certificate and the receipt read those, without converting the line back.

Rates: 1 USD = 1200 ARS, 1 EUR = 1320 ARS.
"""

from odoo import Command, fields
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestPaymentWithholdingMultimoneda(TestArCommon):
    """Withholdings of supplier payments in foreign currency."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()

        cls.company = cls.company_ri
        cls.company.use_payment_pro = True

        # Monedas
        cls.ars = cls.company.currency_id
        cls.usd = cls.env["res.currency"].with_context(active_test=False).search([("name", "=", "USD")])
        cls.usd.active = True
        cls.eur = cls.env["res.currency"].with_context(active_test=False).search([("name", "=", "EUR")])
        cls.eur.active = True

        # Rates: 1 USD = 1200 ARS, 1 EUR = 1320 ARS
        cls.env["res.currency.rate"].create(
            [
                {
                    "name": cls.today,
                    "currency_id": cls.usd.id,
                    "company_id": cls.company.id,
                    "inverse_company_rate": 1200.0,
                },
                {
                    "name": cls.today,
                    "currency_id": cls.eur.id,
                    "company_id": cls.company.id,
                    "inverse_company_rate": 1320.0,
                },
            ]
        )

        # Diarios
        cls.bank_ars = cls._make_bank_journal("BARS", cls.ars)
        cls.bank_usd = cls._make_bank_journal("BUSD", cls.usd)
        cls.bank_eur = cls._make_bank_journal("BEUR", cls.eur)
        cls.purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Compras Test",
                "type": "purchase",
                "code": "PTEST",
                "company_id": cls.company.id,
                "l10n_latam_use_documents": False,
            }
        )

        # Partner y cuentas
        cls.partner = cls.res_partner_adhoc
        cls.account_payable = cls.company_data["default_account_payable"]
        cls.account_expense = cls.company_data["default_account_revenue"]  # reutilizamos revenue como expense

        # Cuenta para retenciones
        cls.account_tax_wth = cls.env["account.account"].create(
            {
                "name": "Retenciones Sufridas",
                "code": "TWTH",
                "account_type": "liability_current",
                "company_ids": [Command.set([cls.company.id])],
            }
        )
        cls.account_tax_base = cls.env["account.account"].create(
            {
                "name": "Base Retención",
                "code": "TBASE",
                "account_type": "asset_current",
                "company_ids": [Command.set([cls.company.id])],
            }
        )
        cls.company.withholding_tax_base_account_id = cls.account_tax_base

        # --- Impuestos de retención ---

        wth_repartition = [
            Command.create({"factor_percent": 100, "repartition_type": "base"}),
            Command.create({"factor_percent": 100, "repartition_type": "tax", "account_id": cls.account_tax_wth.id}),
        ]

        # Retención IIBB 3%
        cls.tax_ret_iibb = cls.env["account.tax"].create(
            {
                "name": "Ret IIBB 3%",
                "amount": -3.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "company_id": cls.company.id,
                "l10n_ar_withholding_tax_type": "iibb_untaxed",
                "l10n_ar_code": "RET_IIBB_TEST",
                "invoice_repartition_line_ids": wth_repartition,
                "refund_repartition_line_ids": wth_repartition,
            }
        )

        # Retención Ganancias 7%
        cls.tax_ret_ganancias = cls.env["account.tax"].create(
            {
                "name": "Ret Ganancias 7%",
                "amount": -7.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "company_id": cls.company.id,
                "l10n_ar_withholding_tax_type": "earnings",
                "l10n_ar_code": "RET_GAN_TEST",
                "l10n_ar_non_taxable_amount": 100_000,
                "invoice_repartition_line_ids": wth_repartition,
                "refund_repartition_line_ids": wth_repartition,
            }
        )

        # Secuencias
        for tax, prefix in [(cls.tax_ret_iibb, "RET-IIBB-"), (cls.tax_ret_ganancias, "RET-GAN-")]:
            tax.withholding_sequence_id = cls.env["ir.sequence"].create(
                {
                    "name": f"Seq {tax.name}",
                    "prefix": prefix,
                    "padding": 8,
                    "company_id": cls.company.id,
                }
            )

        # Posiciones fiscales
        cls.fp_iibb = cls.env["account.fiscal.position"].create(
            {
                "name": "FP IIBB Test",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [Command.create({"default_tax_id": cls.tax_ret_iibb.id, "tax_type": "withholding"})],
            }
        )
        cls.fp_ganancias = cls.env["account.fiscal.position"].create(
            {
                "name": "FP Ganancias Test",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": cls.tax_ret_ganancias.id, "tax_type": "withholding"})
                ],
            }
        )

    @classmethod
    def _make_bank_journal(cls, code, currency):
        return cls.env["account.journal"].create(
            {
                "name": f"Banco {currency.name}",
                "type": "bank",
                "code": code,
                "company_id": cls.company.id,
                "currency_id": currency.id,
            }
        )

    def _create_invoice(self, net_amount, currency):
        """A posted supplier bill of ``net_amount`` plus 21% VAT."""
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "invoice_date": self.today,
                "date": self.today,
                "move_type": "in_invoice",
                "journal_id": self.purchase_journal.id,
                "currency_id": currency.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test",
                            "quantity": 1,
                            "price_unit": net_amount,
                            "account_id": self.account_expense.id,
                            "tax_ids": [Command.set(self.tax_21_purchase.ids)],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _create_payment(self, journal, invoices, fiscal_position=None, to_pay_amount=None):
        """The payment of the bills as the user registers it: the form converts the debt to the journal currency and
        proposes the withholdings. Returns it in draft."""
        context = invoices.line_ids.action_register_payment()["context"]
        with Form(self.env["account.payment"].with_context(**context)) as form:
            form.journal_id = journal
            form.date = self.today
            form.l10n_ar_fiscal_position_id = fiscal_position or self.fp_iibb
            if to_pay_amount is not None:
                form.to_pay_amount = to_pay_amount
        return form.record

    def _set_usd_rate(self, inverse_company_rate):
        rate = self.env["res.currency.rate"].search(
            [("currency_id", "=", self.usd.id), ("name", "=", self.today), ("company_id", "=", self.company.id)]
        )
        rate.inverse_company_rate = inverse_company_rate

    def _assert_withholding(self, payment, base_amount, amount, base_ars, amount_ars):
        """The line in the payment currency, and its value in ARS (what the certificate shows)."""
        line = payment.withholding_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.comodel_currency_id, payment.currency_id)
        self.assertAlmostEqual(line.base_amount, base_amount, places=2)
        self.assertAlmostEqual(line.amount, amount, places=2)
        self.assertAlmostEqual(line.l10n_ar_base_amount, base_ars, places=2)
        self.assertAlmostEqual(line.l10n_ar_amount, amount_ars, places=2)
        return line

    def _assert_entry(self, payment, amount, amount_ars):
        """Posted: the withholding line of the entry in the payment currency and its ARS balance, and the entry
        balances by itself."""
        payment.action_post()
        lines = payment.move_id.line_ids
        wth = lines.filtered(lambda x: x.account_id == self.account_tax_wth)
        self.assertEqual(len(wth), 1)
        self.assertEqual(wth.currency_id, payment.currency_id)
        self.assertAlmostEqual(wth.amount_currency, -amount, places=2)
        self.assertAlmostEqual(wth.balance, -amount_ars, places=2)
        self.assertTrue(self.ars.is_zero(sum(lines.mapped("balance"))))
        self.assertFalse(lines.filtered(lambda x: "automatic balancing" in (x.name or "").lower()))
        return lines

    def test_t1_pago_local(self):
        """R.1, A=B=C=ARS: a bill of 1,000 + VAT withholds 3% of 1,000 and the bank pays the net amount."""
        payment = self._create_payment(self.bank_ars, self._create_invoice(1_000, self.ars))
        self.assertEqual(payment.destination_currency_id, self.ars)
        self._assert_withholding(payment, 1_000, 30, 1_000, 30)
        self.assertAlmostEqual(payment.amount, 1_210, places=2)
        self.assertAlmostEqual(payment.withholding_net_amount, 1_180, places=2)
        self._assert_entry(payment, 30, 30)

    def test_t2_divisa_pura(self):
        """R.2, A=B=USD: a bill of 1,000 USD + VAT has a base of 1,200,000 ARS and withholds 36,000 ARS, that is
        30 USD on the line and on the entry."""
        payment = self._create_payment(self.bank_usd, self._create_invoice(1_000, self.usd))
        self.assertAlmostEqual(payment._get_withholding_rate(), 1_200, places=2)
        self._assert_withholding(payment, 1_000, 30, 1_200_000, 36_000)
        self.assertAlmostEqual(payment.amount, 1_210, places=2)
        self.assertAlmostEqual(payment.withholding_net_amount, 1_180, places=2)
        self._assert_entry(payment, 30, 36_000)

    def test_t3_compra_divisa(self):
        """R.3, A=C=ARS, B=USD at 1,500: a bill of 1,000 USD + VAT has a base of 1,500,000 ARS and withholds
        45,000 ARS. The debt is settled in USD and the bank pays the net amount in ARS."""
        self._set_usd_rate(1_500)
        payment = self._create_payment(self.bank_ars, self._create_invoice(1_000, self.usd))
        self.assertAlmostEqual(payment._get_withholding_rate(), 1_500, places=2)
        self._assert_withholding(payment, 1_500_000, 45_000, 1_500_000, 45_000)
        self.assertAlmostEqual(payment.amount, 1_815_000, places=2)
        self.assertAlmostEqual(payment.withholding_net_amount, 1_770_000, places=2)
        lines = self._assert_entry(payment, 45_000, 45_000)
        payable = lines.filtered(lambda x: x.account_id == self.account_payable)
        self.assertEqual(payable.currency_id, self.usd)
        self.assertAlmostEqual(payable.amount_currency, 1_210, places=2)

    def test_t4_dos_facturas_rate_distinto(self):
        """Two bills of 1,000 USD + VAT paid in ARS at 1,500: the base is the debt at the rate of the payment
        (3,000,000 ARS), not at the rates of the bills."""
        self._set_usd_rate(1_500)
        invoices = self._create_invoice(1_000, self.usd) | self._create_invoice(1_000, self.usd)
        payment = self._create_payment(self.bank_ars, invoices)
        self.assertAlmostEqual(payment.selected_debt_untaxed, 2_000, places=2)
        self._assert_withholding(payment, 3_000_000, 90_000, 3_000_000, 90_000)

    def test_t5_pago_parcial(self):
        """A=C=ARS, B=USD at 1,500: of a bill of 2,000 USD + VAT the user pays 500 USD. The base is the untaxed
        part of what is paid: (2,000 - 1,920 * 2,000 / 2,420) USD at 1,500."""
        self._set_usd_rate(1_500)
        invoice = self._create_invoice(2_000, self.usd)
        payment = self._create_payment(self.bank_ars, invoice, to_pay_amount=500)
        self.assertAlmostEqual(payment.withholdable_advanced_amount, -1_920, places=2)
        base = self.ars.round((2_000 - 1_920 * 2_000 / 2_420) * 1_500)
        amount = self.ars.round(base * 0.03)
        self._assert_withholding(payment, base, amount, base, amount)

    def test_t6_arbitraje(self):
        """R.5, A=USD, B=EUR: a bill of 1,000 EUR + VAT has a base of 1,320,000 ARS and withholds 39,600 ARS, that is
        33 USD on the line (30 EUR of the debt)."""
        payment = self._create_payment(self.bank_usd, self._create_invoice(1_000, self.eur))
        self.assertEqual(payment.destination_currency_id, self.eur)
        self.assertAlmostEqual(payment._get_withholding_rate(), 1_320, places=2)
        self._assert_withholding(payment, 1_100, 33, 1_320_000, 39_600)
        self._assert_entry(payment, 33, 39_600)

    def test_t7_ganancias_acumulado(self):
        """Earnings 7%, non taxable 100,000 ARS, bills in USD paid in ARS at 1,500: the second payment of the month
        adds the base of the first one and discounts what it withheld."""
        self._set_usd_rate(1_500)
        first = self._create_payment(self.bank_ars, self._create_invoice(500, self.usd), self.fp_ganancias)
        # (750,000 - 100,000) * 7%
        self._assert_withholding(first, 750_000, 45_500, 750_000, 45_500)
        first.action_post()

        second = self._create_payment(self.bank_ars, self._create_invoice(1_000, self.usd), self.fp_ganancias)
        # (1,500,000 + 750,000 - 100,000) * 7% - 45,500
        self._assert_withholding(second, 1_500_000, 105_000, 1_500_000, 105_000)

    def test_t8_reconcile_ars_journal_usd_invoice(self):
        """Case 8, reconcile on company currency, A=C=ARS, B1=USD, B2=ARS: the debt is settled in ARS, so a bill of
        1,000 USD + VAT at 1,200 has a base of 1,200,000 ARS and withholds 36,000 ARS."""
        self.company.reconcile_on_company_currency = True
        payment = self._create_payment(self.bank_ars, self._create_invoice(1_000, self.usd))
        payment.counterpart_currency_id = self.usd
        self.assertEqual(payment.destination_currency_id, self.ars)
        self.assertAlmostEqual(payment._get_withholding_rate(), 1.0, places=6)
        self._assert_withholding(payment, 1_200_000, 36_000, 1_200_000, 36_000)
        self.assertAlmostEqual(payment.amount, 1_452_000, places=2)
        self.assertAlmostEqual(payment.withholding_net_amount, 1_416_000, places=2)
        self._assert_entry(payment, 36_000, 36_000)

    def test_t9_reconcile_usd_journal_ars_invoice(self):
        """Case 9, reconcile on company currency, A=USD, B1=B2=ARS: a bill of 1,000 ARS + VAT paid from USD withholds
        30 ARS. The line keeps it in USD (a base of 0.83 USD, that goes back as 996 ARS), and the certificate and the
        entry must still say 30 ARS on a base of 1,000 ARS."""
        self.company.reconcile_on_company_currency = True
        payment = self._create_payment(self.bank_usd, self._create_invoice(1_000, self.ars))
        self.assertEqual(payment.destination_currency_id, self.ars)
        self.assertAlmostEqual(payment._get_withholding_rate(), 1.0, places=6)
        line = payment.withholding_line_ids
        self.assertEqual(len(line), 1)
        payment.action_post()
        wth = payment.move_id.line_ids.filtered(lambda x: x.account_id == self.account_tax_wth)
        self.assertAlmostEqual(wth.balance, -30, places=2)
        amounts = line._get_company_currency_amounts()
        self.assertAlmostEqual(amounts["base_amount"], 1_000, places=2)
        self.assertAlmostEqual(amounts["amount"], 30, places=2)

    def test_t10_certificate_reads_the_ars_of_the_line(self):
        """A=USD, B=C=ARS at a rate that does not divide the withholding: 30,000 ARS is 20.58 USD on the line, which
        would go back as 29,995.35 ARS. The line keeps the 30,000 ARS it computed, and the entry, the certificate and
        the receipt show them."""
        self.company.reconcile_on_company_currency = True
        self._set_usd_rate(1_457.5)
        payment = self._create_payment(self.bank_usd, self._create_invoice(1_000_000, self.ars))
        line = payment.withholding_line_ids
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.amount, 20.58, places=2)
        self.assertEqual(line._get_company_currency_amounts(), {"base_amount": 1_000_000, "amount": 30_000})

        payment.action_post()
        wth = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id == line.tax_id)
        self.assertAlmostEqual(wth.balance, -30_000, places=2)
        self.assertAlmostEqual(abs(wth.tax_base_amount), 1_000_000, places=2)

        certificate = (
            self.env["ir.actions.report"]
            ._render_qweb_html("l10n_ar_tax.action_report_withholding_certificate", line.ids)[0]
            .decode()
        )
        self.assertIn('<span class="oe_currency_value">%s</span>' % f"{abs(wth.balance):,.2f}", certificate)
        self.assertIn('<span class="oe_currency_value">%s</span>' % f"{abs(wth.tax_base_amount):,.2f}", certificate)

    def test_t11_customer_receipt_withholding_typed_in_ars(self):
        """A USD receipt with a withholding the customer made: the user types it in ARS, as in the certificate, and the
        line gets it in the payment currency at the payment rate. The entry books the ARS that were typed."""
        tax_sale = self.tax_ret_iibb.copy({"name": "Ret IIBB sufrida 3%", "type_tax_use": "sale"})
        with Form(
            self.env["account.payment"]
            .with_company(self.company)
            .with_context(default_payment_type="inbound", default_partner_type="customer")
        ) as form:
            form.partner_id = self.partner
            form.journal_id = self.bank_usd
            form.date = self.today
            form.amount = 100.0
            with form.withholding_line_ids.new() as line:
                line.tax_id = tax_sale
                line.l10n_ar_base_amount = 120_000
                line.l10n_ar_amount = 3_601
        payment = form.record
        line = payment.withholding_line_ids
        self.assertAlmostEqual(line.base_amount, 100.0, places=2)
        self.assertAlmostEqual(line.amount, 3.0, places=2)
        self.assertEqual(line._get_company_currency_amounts(), {"base_amount": 120_000, "amount": 3_601})

        payment.action_post()
        self.assertEqual(line._get_company_currency_amounts(), {"base_amount": 120_000, "amount": 3_601})
        wth = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id == tax_sale)
        self.assertAlmostEqual(wth.balance, 3_601, places=2)
