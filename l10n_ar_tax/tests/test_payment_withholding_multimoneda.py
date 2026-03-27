"""
Tests para retenciones en pagos multimoneda (l10n_ar_tax)
=========================================================

Validan los 7 casos de uso de spec_l10n_ar_tax.md.

Principio fiscal:
    Las retenciones se calculan y almacenan SIEMPRE en ARS (C).
    La base imponible se convierte B→C usando el rate del pago.

Convención de rates (formato Odoo nativo):
    accounting_rate  = _get_conversion_rate(C, A)  = A/C
    counterpart_rate = _get_conversion_rate(A, B1) = B1/A

    _get_withholding_rate() = (1/accounting_rate) / counterpart_rate = C/B
        Devuelve multiplicador: base_B × rate = base_C

Rates de referencia:
    1 USD = 1 200 ARS  →  accounting_rate(C→USD) ≈ 0.000833
    1 EUR = 1 320 ARS  →  accounting_rate(C→EUR) ≈ 0.000758
"""

from odoo import Command, fields
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentWithholdingMultimoneda(TestArCommon):
    """Tests de retenciones en pagos multimoneda."""

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

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
        cls.company.l10n_ar_tax_base_account_id = cls.account_tax_base

        # --- Impuestos de retención ---

        wth_repartition = [
            Command.create({"factor_percent": 100, "repartition_type": "base"}),
            Command.create({"factor_percent": 100, "repartition_type": "tax", "account_id": cls.account_tax_wth.id}),
        ]

        # Retención IIBB 3%
        cls.tax_ret_iibb = cls.env["account.tax"].create(
            {
                "name": "Ret IIBB 3%",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "company_id": cls.company.id,
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_code": "RET_IIBB_TEST",
                "invoice_repartition_line_ids": wth_repartition,
                "refund_repartition_line_ids": wth_repartition,
            }
        )

        # Retención Ganancias 7%
        cls.tax_ret_ganancias = cls.env["account.tax"].create(
            {
                "name": "Ret Ganancias 7%",
                "amount": 7.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "company_id": cls.company.id,
                "l10n_ar_tax_type": "earnings",
                "l10n_ar_code": "RET_GAN_TEST",
                "l10n_ar_non_taxable_amount": 100_000,
                "invoice_repartition_line_ids": wth_repartition,
                "refund_repartition_line_ids": wth_repartition,
            }
        )

        # Secuencias
        for tax, prefix in [(cls.tax_ret_iibb, "RET-IIBB-"), (cls.tax_ret_ganancias, "RET-GAN-")]:
            tax.l10n_ar_withholding_sequence_id = cls.env["ir.sequence"].create(
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        """Crea y postea factura proveedor.  ``net_amount`` es *sin* IVA."""
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

    def _create_payment_with_wth(self, journal, invoice, fiscal_position=None, **kw):
        """Crea pago proveedor con retenciones.  Devuelve pago en borrador."""
        fp = fiscal_position or self.fp_iibb
        debt = invoice.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        vals = {
            "journal_id": journal.id,
            "partner_id": self.partner.id,
            "partner_type": "supplier",
            "payment_type": "outbound",
            "date": self.today,
            "l10n_ar_fiscal_position_id": fp.id,
            "to_pay_move_line_ids": [Command.set(debt.ids)],
        }
        vals.update(kw)
        payment = self.env["account.payment"].create(vals)
        # En la UI, _onchange_withholdings ajusta payment.amount restando las
        # retenciones (amount = to_pay - withholdings).  En tests debemos invocarlo.
        payment._onchange_withholdings()
        return payment

    def _get_rate(self, from_currency, to_currency):
        return self.env["res.currency"]._get_conversion_rate(
            from_currency=from_currency,
            to_currency=to_currency,
            company=self.company,
            date=self.today,
        )

    def _set_usd_rate(self, inverse_company_rate):
        """Cambia el rate USD y registra cleanup automático."""
        rate_record = self.env["res.currency.rate"].search(
            [
                ("currency_id", "=", self.usd.id),
                ("name", "=", self.today),
                ("company_id", "=", self.company.id),
            ]
        )
        old_rate = rate_record.inverse_company_rate
        rate_record.inverse_company_rate = inverse_company_rate
        self.addCleanup(lambda: rate_record.write({"inverse_company_rate": old_rate}))

    def _wth_line(self, payment):
        """Retorna la primera línea de retención."""
        self.assertTrue(payment.l10n_ar_withholding_line_ids, "Debe haber líneas de retención")
        return payment.l10n_ar_withholding_line_ids[0]

    def _wth_move_lines(self, payment):
        """Retorna las move lines de retención (cuenta tax) del asiento posteado."""
        return payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_tax_wth)

    # ==================================================================
    # T.1 — Pago local (A=B=C=ARS)
    # ==================================================================

    def test_t1_pago_local(self):
        """A=B=C=ARS.  Factura 1210 ARS (1000 neto + 210 IVA).
        Rate = 1.0 trivial.  Retención IIBB 3% sobre base neta.

        Esperado:
            selected_debt_untaxed  = 1 000 ARS
            _get_withholding_rate  = 1.0
            base_amount            = 1 000 ARS (C)
            amount                 = 30 ARS
            withholdings_amount    = 30 ARS (UX = C)
        """
        invoice = self._create_invoice(1_000, self.ars)
        self.assertAlmostEqual(invoice.amount_total, 1_210, places=2)

        payment = self._create_payment_with_wth(self.bank_ars, invoice)

        # Monedas y rate
        self.assertEqual(payment.currency_id, self.ars)
        self.assertEqual(payment.destination_currency_id, self.ars)
        self.assertEqual(payment._get_withholding_rate(), 1.0)

        # Deuda neta y base
        self.assertAlmostEqual(payment.selected_debt_untaxed, 1_000, places=2)
        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_000, places=2)
        self.assertAlmostEqual(wth.amount, 30, places=2)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)

        # Postear y verificar asiento
        payment.action_post()
        ml = self._wth_move_lines(payment)
        self.assertEqual(len(ml), 1)
        self.assertAlmostEqual(abs(ml.balance), 30, places=2)
        self.assertEqual(ml.currency_id, self.ars)

    # ==================================================================
    # T.2 — Pago divisa pura (A=B=USD, C=ARS)
    # ==================================================================

    def test_t2_divisa_pura(self):
        """A=B=USD, C=ARS, 1 USD = 1200 ARS.
        Factura 1210 USD (1000 neto).

        Esperado:
            accounting_rate          ≈ 0.000833 (C→A format)
            _get_withholding_rate    = 1200 (B→C = USD→ARS)
            base_amount              = 1 200 000 ARS
            amount                   = 36 000 ARS
            withholdings_amount      = 30 USD
            Asiento retención: balance 36000, amt_currency 36000 ARS, currency ARS(C)
            (withholding lines siempre en C cuando A≠C)
        """
        invoice = self._create_invoice(1_000, self.usd)
        payment = self._create_payment_with_wth(self.bank_usd, invoice)

        # accounting_rate = A/C ≈ 0.000833 (NO 1200)
        expected_acc = self._get_rate(self.ars, self.usd)
        self.assertAlmostEqual(payment.accounting_rate, expected_acc, places=6)
        self.assertAlmostEqual(payment.counterpart_rate, 1.0, places=6)

        # Withholding rate: (1/0.000833) / 1.0 = 1200
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1_200, places=0)

        # Base y retención
        self.assertAlmostEqual(payment.selected_debt_untaxed, 1_000, places=2)
        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_200_000, places=0)
        self.assertAlmostEqual(wth.amount, 36_000, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)

        # Asiento: withholding lines siempre en C (ARS) cuando A≠C
        payment.action_post()
        ml = self._wth_move_lines(payment)
        self.assertAlmostEqual(abs(ml.balance), 36_000, places=0)
        self.assertAlmostEqual(
            abs(ml.amount_currency), 36_000, places=0, msg="use_company_currency: amount_currency = balance (ARS)"
        )
        self.assertEqual(ml.currency_id, self.ars, "Withholding line siempre en C (ARS)")

    # ==================================================================
    # T.3 — Compra de divisa (A=C=ARS, B=USD, rate 1500)
    # ==================================================================

    def test_t3_compra_divisa(self):
        """A=C=ARS, B=USD, 1 USD = 1500 ARS.
        Factura 1210 USD (1000 neto), pago en ARS.

        Esperado:
            accounting_rate           = 1.0 (A=C)
            counterpart_rate          = 1/1500 ≈ 0.000667
            _get_withholding_rate     = 1500
            base_amount               = 1 500 000 ARS
            amount                    = 45 000 ARS
            withholdings_amount       = 30 USD
            Asiento (counterpart_is_foreign): currency=ARS, amt_currency=balance
        """
        self._set_usd_rate(1_500)
        invoice = self._create_invoice(1_000, self.usd)
        payment = self._create_payment_with_wth(self.bank_ars, invoice)

        # Rates
        self.assertAlmostEqual(payment.accounting_rate, 1.0, places=6)
        self.assertAlmostEqual(payment.counterpart_rate, 1 / 1_500, places=6)

        # Withholding rate = (1/1.0) / (1/1500) = 1500
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1_500, places=0)

        # Base y retención
        self.assertAlmostEqual(payment.selected_debt_untaxed, 1_000, places=2)
        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_500_000, places=0)
        self.assertAlmostEqual(wth.amount, 45_000, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)

        # Asiento: counterpart_is_foreign → wth lines en ARS
        payment.action_post()
        ml = self._wth_move_lines(payment)
        self.assertAlmostEqual(abs(ml.balance), 45_000, places=0)
        self.assertAlmostEqual(
            abs(ml.amount_currency), 45_000, places=0, msg="counterpart_is_foreign: amount_currency = balance (ARS)"
        )
        self.assertEqual(ml.currency_id, self.ars, "counterpart_is_foreign: currency_id = ARS (C)")

        # AP debe estar en USD con ajuste de retención
        ap = payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_payable)
        self.assertEqual(ap.currency_id, self.usd, "AP debe estar en USD")

    # ==================================================================
    # T.4 — Dos facturas USD, pago a rate diferente
    # ==================================================================

    def test_t4_dos_facturas_rate_distinto(self):
        """A=C=ARS, B=USD, rate pago 1500.
        Factura 1: 1210 USD (1000 neto).  Factura 2: 1210 USD (1000 neto).

        Clave: base se calcula con rate del PAGO sobre total,
        NO rate histórico por factura.

        Esperado:
            selected_debt_untaxed = 2 000 USD
            base_amount           = 2 000 × 1500 = 3 000 000 ARS
            amount                = 90 000 ARS
            withholdings_amount   = 60 USD
        """
        self._set_usd_rate(1_500)
        inv1 = self._create_invoice(1_000, self.usd)
        inv2 = self._create_invoice(1_000, self.usd)

        debt = (inv1 | inv2).line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "l10n_ar_fiscal_position_id": self.fp_iibb.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
            }
        )

        self.assertAlmostEqual(payment.selected_debt_untaxed, 2_000, places=2)
        self.assertAlmostEqual(payment._get_withholding_rate(), 1_500, places=0)

        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 3_000_000, places=0, msg="Base con rate del pago, NO rates históricos")
        self.assertAlmostEqual(wth.amount, 90_000, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 60, places=2)

    # ==================================================================
    # T.5 — Pago parcial (A=C=ARS, B=USD)
    # ==================================================================

    def test_t5_pago_parcial(self):
        """A=C=ARS, B=USD, rate 1500.
        Factura 2420 USD (2000 neto), pago parcial 750 000 ARS = 500 USD.

        Flow:
            selected_debt         = 2 420 USD
            unreconciled_amount   = -1 920 USD (manual: 500 - 2420)
            to_pay_amount         = 500 USD
            withholdable_adv_amt  = -1 920 USD (= unreconciled_amount)

        Dentro de _compute_base_amount:
            advance (proporcional) = -1920 × (2000/2420) = -1 586.78 USD
            base_in_b              = 2000 + (-1586.78) = 413.22 USD
            base_amount            = 413.22 × 1500 = 619 835 ARS

        Esperado:
            amount              ≈ 18 595 ARS
            withholdings_amount ≈ 12.40 USD
        """
        self._set_usd_rate(1_500)
        invoice = self._create_invoice(2_000, self.usd)
        self.assertAlmostEqual(invoice.amount_total, 2_420, places=2)

        payment = self._create_payment_with_wth(self.bank_ars, invoice, amount=750_000)

        # Simular pago parcial: setear unreconciled_amount manualmente
        # (en UI el usuario edita to_pay_amount y el inverse setea unreconciled_amount)
        self.assertAlmostEqual(payment.selected_debt, 2_420, places=2)
        payment.unreconciled_amount = -1_920  # 500 - 2420

        self.assertAlmostEqual(
            payment.to_pay_amount, 500, places=2, msg="to_pay_amount = selected_debt + unreconciled_amount"
        )
        # withholdable_advanced_amount = unreconciled_amount (compute directo)
        self.assertAlmostEqual(payment.withholdable_advanced_amount, -1_920, places=2)

        # Forzar recompute de base_amount tras cambiar unreconciled_amount
        payment.l10n_ar_withholding_line_ids._compute_base_amount()

        wth = self._wth_line(payment)

        # Dentro de _compute_base_amount el proporcional se calcula así:
        # advance = -1920 * (2000/2420) = -1586.78
        # base_in_b = 2000 + (-1586.78) = 413.22
        # base_amount = 413.22 * 1500 = 619 835
        expected_advance = -1_920 * (2_000 / 2_420)
        expected_base_b = 2_000 + expected_advance
        expected_base_c = expected_base_b * 1_500

        self.assertAlmostEqual(wth.base_amount, expected_base_c, places=0)
        expected_wth = expected_base_c * 0.03
        self.assertAlmostEqual(wth.amount, expected_wth, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, expected_wth / 1_500, places=2)

    # ==================================================================
    # T.6 — Arbitraje (A=USD, B=EUR, C=ARS)
    # ==================================================================

    def test_t6_arbitraje(self):
        """A=USD, B=EUR, C=ARS.  Factura 1210 EUR (1000 neto), pago USD.
        Rates: 1 USD = 1200 ARS, 1 EUR = 1320 ARS.

        Esperado:
            accounting_rate          ≈ 0.000833 (USD/ARS)
            counterpart_rate         ≈ 0.909 (EUR/USD = 1200/1320)
            _get_withholding_rate    = (1/0.000833) / 0.909 = 1320 (EUR→ARS)
            base_amount              = 1 320 000 ARS
            amount                   = 39 600 ARS
            withholdings_amount      = 30 EUR
            Asiento retención: balance 39600, amt_currency 39600 ARS, currency ARS(C)
            (withholding lines siempre en C cuando A≠C)
        """
        invoice = self._create_invoice(1_000, self.eur)
        payment = self._create_payment_with_wth(self.bank_usd, invoice)

        # Monedas
        self.assertEqual(payment.currency_id, self.usd)
        self.assertEqual(payment.destination_currency_id, self.eur)

        # Rates
        expected_acc = self._get_rate(self.ars, self.usd)  # ≈ 0.000833
        expected_cp = self._get_rate(self.usd, self.eur)  # ≈ 0.909
        self.assertAlmostEqual(payment.accounting_rate, expected_acc, places=6)
        self.assertAlmostEqual(payment.counterpart_rate, expected_cp, places=4)

        # Withholding rate: EUR→ARS = 1320
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1_320, places=0)

        # Base y retención
        self.assertAlmostEqual(payment.selected_debt_untaxed, 1_000, places=2)
        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_320_000, places=0)
        self.assertAlmostEqual(wth.amount, 39_600, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)

        # Asiento: withholding lines siempre en C (ARS) cuando A≠C
        payment.action_post()
        ml = self._wth_move_lines(payment)
        self.assertAlmostEqual(abs(ml.balance), 39_600, places=0)
        self.assertAlmostEqual(
            abs(ml.amount_currency), 39_600, places=0, msg="use_company_currency: amount_currency = balance (ARS)"
        )
        self.assertEqual(ml.currency_id, self.ars, "Withholding line siempre en C (ARS)")

    # ==================================================================
    # T.7 — Ganancias con acumulado del período (A=C=ARS, B=USD)
    # ==================================================================

    def test_t7_ganancias_acumulado(self):
        """A=C=ARS, B=USD, rate 1500.
        Pago previo genera acumulados reales del período.
        Pago nuevo: factura 1210 USD (1000 neto).
        Ganancias 7%, mínimo no imponible 100 000 ARS.

        Valida que _tax_compute_all_helper suma base + same_period_base
        en C (ARS) y descuenta same_period_withholdings correctamente.
        """
        self._set_usd_rate(1_500)

        # --- Pago previo: genera acumulados reales del período ---
        inv_prev = self._create_invoice(500, self.usd)  # 500 neto + IVA = 605 USD
        pay_prev = self._create_payment_with_wth(
            self.bank_ars,
            inv_prev,
            fiscal_position=self.fp_ganancias,
        )
        pay_prev.action_post()

        # Leer acumulados reales generados por el primer pago
        wth_prev = self._wth_line(pay_prev)
        prev_base = wth_prev.base_amount  # 500 USD × 1500 = 750 000 ARS
        prev_amount = wth_prev.amount  # (750K - 100K) × 7% = 45 500 ARS

        self.assertAlmostEqual(prev_base, 750_000, places=0)
        self.assertAlmostEqual(prev_amount, 45_500, places=0)

        # --- Segundo pago: debe acumular con el anterior ---
        inv_new = self._create_invoice(1_000, self.usd)
        pay_new = self._create_payment_with_wth(
            self.bank_ars,
            inv_new,
            fiscal_position=self.fp_ganancias,
        )

        wth_new = self._wth_line(pay_new)

        # Acumulados del período deben reflejar el pago anterior
        same_base = wth_new._get_same_period_base_amount()
        same_wth = wth_new._get_same_period_withholdings_amount()
        self.assertAlmostEqual(same_base, prev_base, places=0)
        self.assertAlmostEqual(same_wth, prev_amount, places=0)

        # base_amount del nuevo pago: 1000 USD × 1500 = 1 500 000 ARS
        new_base = 1_000 * 1_500
        self.assertAlmostEqual(wth_new.base_amount, new_base, places=0)

        # net_amount = new_base + same_base - mínimo no imponible
        #            = 1 500 000 + 750 000 - 100 000 = 2 150 000
        net = new_base + prev_base - self.tax_ret_ganancias.l10n_ar_non_taxable_amount

        # withholding bruto = net × 7%, neto = bruto - same_period_wth
        expected_amount = net * 0.07 - prev_amount
        self.assertAlmostEqual(wth_new.amount, expected_amount, places=0)

        # UX en USD
        self.assertAlmostEqual(
            pay_new.withholdings_amount,
            expected_amount / 1_500,
            places=2,
        )

    # ==================================================================
    # T.8 — Reconcile modo (A=C=ARS, B1=USD, B2=ARS) + IIBB
    # ==================================================================

    def test_t8_reconcile_ars_journal_usd_invoice(self):
        """caso 8: A=C=ARS, B1=USD, B2=ARS (reconcile_on_company_currency=True).

        Factura 1000 USD neto (1210 USD total), rate 1200 ARS/USD.
        Deuda en ARS (B2=C): 1 452 000 ARS total, 1 200 000 ARS neto.

        _get_withholding_rate() = C/B2 = ARS/ARS = 1.0
        base_amount             = 1 200 000 ARS
        wth                     =    36 000 ARS
        withholdings_amount     =    36 000 ARS (en B2=ARS)

        _onchange_withholdings: B1≠B2 → diff_in_a = payment_diff * accounting_rate(1.0)
        amount esperado         = 1 452 000 − 36 000 = 1 416 000 ARS

        Valida el fix de la rama B1≠B2 en _onchange_withholdings y el cálculo
        correcto del amount_currency de la AP en el bloque counterpart_is_foreign.
        """
        self.company.reconcile_on_company_currency = True
        self.addCleanup(setattr, self.company, "reconcile_on_company_currency", False)

        invoice = self._create_invoice(1_000, self.usd)
        self.assertAlmostEqual(invoice.amount_total, 1_210, places=2)

        # Crear pago; payment_pro pondrá counterpart_currency_id=USD desde to_pay_move_line_ids
        payment = self._create_payment_with_wth(self.bank_ars, invoice)

        # Aseguramos que B1=USD (el usuario puede elegirlo en modo reconcile)
        payment.counterpart_currency_id = self.usd

        # _onchange_withholdings debe re-ejecutarse tras el cambio de moneda
        payment._onchange_withholdings()

        # --- Currencies ---
        self.assertEqual(payment.currency_id, self.ars)
        self.assertEqual(payment.destination_currency_id, self.ars, "B2=ARS en reconcile mode")
        self.assertEqual(payment.counterpart_currency_id, self.usd, "B1=USD (moneda de la deuda)")

        # --- Rates ---
        self.assertAlmostEqual(payment.accounting_rate, 1.0, places=6, msg="A=C → A/C=1.0")
        expected_cp = self._get_rate(self.ars, self.usd)  # USD/ARS ≈ 1/1200
        self.assertAlmostEqual(payment.counterpart_rate, expected_cp, places=6)

        # --- Withholding rate ---
        self.assertAlmostEqual(payment._get_withholding_rate(), 1.0, places=6, msg="B2=C=ARS → rate=1.0")

        # --- Base y retención ---
        # selected_debt_untaxed en ARS (B2=C → usa amount_residual)
        self.assertAlmostEqual(payment.selected_debt_untaxed, 1_200_000, places=0)
        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_200_000, places=0)
        self.assertAlmostEqual(wth.amount, 36_000, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 36_000, places=0, msg="withholdings en ARS (B2=C)")

        # --- amount después de _onchange_withholdings ---
        # payment_total = 0 (super) + 36 000 (wth) = 36 000 ARS
        # payment_difference = 1 452 000 − 36 000 = 1 416 000 ARS
        # B1≠B2 → diff_in_a = 1 416 000 × accounting_rate(1.0) = 1 416 000
        # amount = 0 + 1 416 000 = 1 416 000 ARS
        self.assertAlmostEqual(
            payment.amount, 1_416_000, places=0, msg="B1≠B2: diff_in_a = payment_diff × accounting_rate(1.0)"
        )

        # --- Asiento ---
        payment.action_post()
        ml = self._wth_move_lines(payment)
        self.assertEqual(len(ml), 1)
        self.assertAlmostEqual(abs(ml.balance), 36_000, places=0)
        self.assertEqual(ml.currency_id, self.ars, "retención siempre en C=ARS")

        # El asiento debe estar balanceado (valida fix counterpart_is_foreign)
        total = sum(payment.move_id.line_ids.mapped("balance"))
        self.assertAlmostEqual(total, 0, places=2, msg="El asiento debe estar balanceado")

    # ==================================================================
    # T.9 — Reconcile modo (A=USD, B1=B2=ARS) + IIBB
    # ==================================================================

    def test_t9_reconcile_usd_journal_ars_invoice(self):
        """caso 9: A=USD, B1=B2=ARS (reconcile_on_company_currency=True).

        Factura 1000 ARS neto (1210 ARS total), journal en USD.
        Rate: 1 USD = 1200 ARS.

        _get_withholding_rate() = C/B2 = ARS/ARS = 1.0
        base_amount             = 1 000 ARS
        wth                     =    30 ARS
        withholdings_amount     =    30 ARS (en B2=ARS)

        _onchange_withholdings: B1=B2=ARS → diff_in_a = payment_diff_ARS / counterpart_rate(1200)
        amount esperado         = (1210 − 30) / 1200 = 1180/1200 ≈ 0.9833 USD

        Valida la rama B1=B2 en modo reconcile (counterpart_rate=1200, wth_rate=1.0).
        """
        self.company.reconcile_on_company_currency = True
        self.addCleanup(setattr, self.company, "reconcile_on_company_currency", False)

        invoice = self._create_invoice(1_000, self.ars)
        self.assertAlmostEqual(invoice.amount_total, 1_210, places=2)

        payment = self._create_payment_with_wth(self.bank_usd, invoice)

        # --- Currencies ---
        self.assertEqual(payment.currency_id, self.usd)
        self.assertEqual(payment.destination_currency_id, self.ars, "B2=ARS en reconcile mode")
        self.assertEqual(payment.counterpart_currency_id, self.ars, "B1=ARS (moneda de la deuda)")

        # --- Rates ---
        expected_acc = self._get_rate(self.ars, self.usd)  # USD/ARS ≈ 1/1200
        self.assertAlmostEqual(payment.accounting_rate, expected_acc, places=6)
        # B1=C=ARS → counterpart_rate = 1/accounting_rate = 1200
        self.assertAlmostEqual(payment.counterpart_rate, 1.0 / expected_acc, places=2)

        # --- Withholding rate ---
        self.assertAlmostEqual(payment._get_withholding_rate(), 1.0, places=6, msg="B2=C=ARS → rate=1.0")

        # --- selected_debt_untaxed en ARS (B2=C → usa amount_residual) ---
        self.assertAlmostEqual(payment.selected_debt_untaxed, 1_000, places=2)

        # --- Base y retención ---
        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_000, places=2)
        self.assertAlmostEqual(wth.amount, 30, places=2)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2, msg="withholdings en ARS (B2=C)")

        # --- amount después de _onchange_withholdings ---
        # payment_total = cca(0) + withholdings(30) = 30 ARS
        # payment_difference = 1210 − 30 = 1180 ARS (en B2=ARS)
        # B1=B2 → diff_in_a = 1180 / counterpart_rate(1200) = 1180/1200 ≈ 0.9833 USD
        # amount se almacena en USD (2 decimales) → queda redondeado a 0.98 USD
        expected_amount = self.usd.round((1_210 - 30) * expected_acc)  # round(1180/1200, 2) = 0.98
        self.assertAlmostEqual(
            payment.amount,
            expected_amount,
            places=2,
            msg="B1=B2=ARS: diff_in_a = payment_diff_ARS / counterpart_rate(1200)",
        )

        # --- Asiento ---
        payment.action_post()
        ml = self._wth_move_lines(payment)
        self.assertEqual(len(ml), 1)
        self.assertAlmostEqual(abs(ml.balance), 30, places=2)
        self.assertEqual(ml.currency_id, self.ars, "retención siempre en C=ARS")

        # El asiento debe estar balanceado
        total = sum(payment.move_id.line_ids.mapped("balance"))
        self.assertAlmostEqual(total, 0, places=2, msg="El asiento debe estar balanceado")
