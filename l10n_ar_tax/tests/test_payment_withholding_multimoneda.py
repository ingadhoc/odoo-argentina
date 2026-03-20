"""
Tests para retenciones en pagos multimoneda (l10n_ar_tax)
=========================================================

Estos tests validan los casos de uso definidos en spec_l10n_ar_tax.md para
el cálculo de retenciones en pagos con distintas combinaciones de monedas.

Principio fiscal clave:
- Las retenciones en Argentina se calculan y almacenan SIEMPRE en ARS (C)
- La base imponible se convierte B→C usando el rate del pago
- El usuario ve los montos en la moneda de la deuda (B) solo para UX

Monedas:
- A: currency_id (moneda del diario)
- B: destination_currency_id (moneda de la deuda/UX)
- C: company_currency_id (ARS, moneda contable)

Factor IVA: Para deuda con IVA 21%, la base neta = total / 1.21 ≈ 0.8264
Retención ejemplo: 3% sobre base neta sin IVA
"""

from odoo import Command, fields
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestPaymentWithholdingMultimoneda(common.TransactionCase):
    """Tests de retenciones en pagos multimoneda"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.ar = cls.env.ref("base.ar")
        cls.company = cls.env.company
        cls.company.use_payment_pro = True
        cls.company.country_id = cls.ar

        # === Configuración de monedas ===
        cls.ars = cls.company.currency_id

        cls.usd = cls.env["res.currency"].with_context(active_test=False).search([("name", "=", "USD")])
        cls.usd.active = True
        cls.eur = cls.env["res.currency"].with_context(active_test=False).search([("name", "=", "EUR")])
        cls.eur.active = True

        # === Rates ===
        # 1 USD = 1200 ARS, 1 EUR = 1320 ARS
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

        # === Diarios ===
        cls.bank_journal_ars = cls.env["account.journal"].create(
            {
                "name": "Banco ARS",
                "type": "bank",
                "code": "BARS",
                "company_id": cls.company.id,
                "currency_id": cls.ars.id,
            }
        )
        cls.bank_journal_usd = cls.env["account.journal"].create(
            {
                "name": "Banco USD",
                "type": "bank",
                "code": "BUSD",
                "company_id": cls.company.id,
                "currency_id": cls.usd.id,
            }
        )
        cls.bank_journal_eur = cls.env["account.journal"].create(
            {
                "name": "Banco EUR",
                "type": "bank",
                "code": "BEUR",
                "company_id": cls.company.id,
                "currency_id": cls.eur.id,
            }
        )

        # === Partner ===
        cls.partner_ri = cls.env["res.partner"].create(
            {
                "name": "RI Partner",
                "vat": "34278580484",
                "country_id": cls.ar.id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
            }
        )

        # === Cuentas ===
        cls.account_payable = cls.env["account.account"].create(
            {
                "name": "Test Payable",
                "code": "TPAY",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        cls.account_expense = cls.env["account.account"].create(
            {
                "name": "Test Expense",
                "code": "TEXP",
                "account_type": "expense",
            }
        )
        cls.account_tax = cls.env["account.account"].create(
            {
                "name": "Test Tax Account",
                "code": "TTAX",
                "account_type": "liability_current",
            }
        )
        cls.account_tax_base = cls.env["account.account"].create(
            {
                "name": "Tax Base Account",
                "code": "TBASE",
                "account_type": "asset_current",
            }
        )
        cls.company.l10n_ar_tax_base_account_id = cls.account_tax_base
        cls.partner_ri.property_account_payable_id = cls.account_payable

        # === Impuestos ===
        # Tax group para IVA
        cls.tax_group_iva = cls.env["account.tax.group"].create(
            {
                "name": "IVA Tax Group",
                "company_id": cls.company.id,
            }
        )

        # Tax group para Ganancias
        cls.tax_group_ganancias = cls.env["account.tax.group"].create(
            {
                "name": "Ganancias Tax Group",
                "company_id": cls.company.id,
            }
        )

        # IVA 21%
        cls.tax_iva_21 = cls.env["account.tax"].create(
            {
                "name": "IVA 21%",
                "amount": 21.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": cls.company.id,
                "tax_group_id": cls.tax_group_iva.id,
            }
        )

        # Retención IVA 3% (sobre base neta)
        cls.tax_ret_iva_3 = cls.env["account.tax"].create(
            {
                "name": "Retención IVA 3%",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "company_id": cls.company.id,
                "tax_group_id": cls.tax_group_iva.id,
                "invoice_repartition_line_ids": [
                    Command.create({"factor_percent": 100, "repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.account_tax.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"factor_percent": 100, "repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.account_tax.id,
                        }
                    ),
                ],
            }
        )

        # Retención Ganancias 7% (con mínimo no imponible)
        cls.tax_ret_ganancias_7 = cls.env["account.tax"].create(
            {
                "name": "Retención Ganancias 7%",
                "amount": 7.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "company_id": cls.company.id,
                "tax_group_id": cls.tax_group_ganancias.id,
                "invoice_repartition_line_ids": [
                    Command.create({"factor_percent": 100, "repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.account_tax.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"factor_percent": 100, "repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.account_tax.id,
                        }
                    ),
                ],
            }
        )

        # Secuencias para numeración de retenciones
        cls.sequence_ret_iva = cls.env["ir.sequence"].create(
            {
                "name": "Secuencia Retención IVA",
                "code": "l10n_ar.payment.withholding.iva",
                "prefix": "RET-IVA-",
                "padding": 8,
                "company_id": cls.company.id,
            }
        )
        cls.tax_ret_iva_3.l10n_ar_withholding_sequence_id = cls.sequence_ret_iva

        cls.sequence_ret_ganancias = cls.env["ir.sequence"].create(
            {
                "name": "Secuencia Retención Ganancias",
                "code": "l10n_ar.payment.withholding.ganancias",
                "prefix": "RET-GAN-",
                "padding": 8,
                "company_id": cls.company.id,
            }
        )
        cls.tax_ret_ganancias_7.l10n_ar_withholding_sequence_id = cls.sequence_ret_ganancias

        # Fiscal Position: crear con solo el impuesto de IVA para los tests básicos
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Posición Fiscal con Retenciones IVA",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": cls.tax_ret_iva_3.id, "tax_type": "withholding"}),
                ],
            }
        )

    def _create_invoice(self, amount, currency, with_iva=True):
        """
        Helper: Crea una factura de proveedor.

        Args:
            amount: Importe neto (sin IVA)
            currency: Moneda de la factura
            with_iva: Si True, aplica IVA 21% al total

        Returns:
            account.move: Factura posteada
        """
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_ri.id,
                "invoice_date": self.today,
                "date": self.today,
                "move_type": "in_invoice",
                "currency_id": currency.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test Product",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.account_expense.id,
                            "tax_ids": [Command.set([self.tax_iva_21.id] if with_iva else [])],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _create_payment_with_withholding(self, journal, invoice, fiscal_position=None):
        """
        Helper: Crea un pago con retenciones.

        Args:
            journal: Diario del pago
            invoice: Factura a pagar
            fiscal_position: Posición fiscal (si None, usa self.fiscal_position)

        Returns:
            account.payment: Pago en borrador con líneas de retención
        """
        if fiscal_position is None:
            fiscal_position = self.fiscal_position

        payment = self.env["account.payment"].create(
            {
                "journal_id": journal.id,
                "partner_id": self.partner_ri.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "l10n_ar_fiscal_position_id": fiscal_position.id,
                "to_pay_move_line_ids": [
                    Command.set(
                        invoice.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable").ids
                    )
                ],
            }
        )

        # Forzar compute de líneas de retención (simula onchange/fiscal position)
        payment._compute_l10n_ar_withholding_line_ids()
        return payment

    # =====================================================================
    # TESTS DE CASOS DE USO
    # =====================================================================

    def test_t1_pago_local_ars_ars_ars(self):
        """
        T.1: Pago local (A=B=C=ARS)

        Setup: Factura 1.210 ARS (1.000 neto + 210 IVA 21%), pago 1.210 ARS.
        Retención IVA 3% sobre base neta.

        Valida:
        - selected_debt_untaxed = 1.000 ARS (deuda neta)
        - _get_withholding_rate() = 1.0 (ARS→ARS)
        - base_amount = 1.000 ARS (C, stored)
        - withholding amount = 30 ARS (3% de 1.000)
        - withholdings_amount = 30 ARS (UX en B=C)
        """
        # Crear factura: 1.000 neto + 21% IVA = 1.210 ARS
        invoice = self._create_invoice(1000, self.ars, with_iva=True)
        self.assertAlmostEqual(invoice.amount_total, 1210, places=2, msg="Total factura debe ser 1.210 ARS")

        # Crear pago con retención
        payment = self._create_payment_with_withholding(self.bank_journal_ars, invoice)

        # === VALIDACIONES ===
        # A = B = C = ARS
        self.assertEqual(payment.currency_id, self.ars, "A debe ser ARS")
        self.assertEqual(payment.destination_currency_id, self.ars, "B debe ser ARS")
        self.assertEqual(payment.company_currency_id, self.ars, "C debe ser ARS")

        # selected_debt_untaxed: 1.210 / 1.21 = 1.000 ARS
        self.assertAlmostEqual(
            payment.selected_debt_untaxed, 1000, places=2, msg="selected_debt_untaxed debe ser 1.000 ARS"
        )

        # _get_withholding_rate: ARS→ARS = 1.0
        rate = payment._get_withholding_rate()
        self.assertEqual(rate, 1.0, msg="_get_withholding_rate debe ser 1.0 (ARS→ARS)")

        # Línea de retención
        self.assertEqual(len(payment.l10n_ar_withholding_line_ids), 1, "Debe haber 1 línea de retención")
        wth_line = payment.l10n_ar_withholding_line_ids[0]

        # base_amount en C (ARS): 1.000 * 1.0 = 1.000 ARS
        self.assertAlmostEqual(wth_line.base_amount, 1000, places=2, msg="base_amount debe ser 1.000 ARS (C)")

        # amount en C (ARS): 1.000 * 3% = 30 ARS
        self.assertAlmostEqual(wth_line.amount, 30, places=2, msg="amount debe ser 30 ARS")

        # withholdings_amount en B (ARS): 30 / 1.0 = 30 ARS
        self.assertAlmostEqual(
            payment.withholdings_amount, 30, places=2, msg="withholdings_amount debe ser 30 ARS (UX)"
        )

        # Postear y validar asiento
        payment.action_post()
        self.assertEqual(payment.state, "posted", "Pago debe estar posteado")

        # Validar líneas de retención en el asiento
        wth_move_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_tax)
        self.assertEqual(len(wth_move_lines), 1, "Debe haber 1 línea de retención en el asiento")
        self.assertAlmostEqual(abs(wth_move_lines.balance), 30, places=2, msg="Balance de retención debe ser 30 ARS")

    def test_t2_pago_divisa_pura_usd_usd_ars(self):
        """
        T.2: Pago divisa pura (A=B=USD, C=ARS, 1 USD = 1.200 ARS)

        Setup: Factura 1.210 USD (1.000 neto + 210 IVA), pago 1.210 USD.

        Valida:
        - selected_debt_untaxed = 1.000 USD (usa amount_residual_currency)
        - _get_withholding_rate() = 1200 (USD→ARS)
        - base_amount = 1.200.000 ARS (C, stored)
        - withholding amount = 36.000 ARS (3% de 1.200.000)
        - withholdings_amount = 30 USD (UX: 36.000 / 1200)
        - Asiento: balance=36.000 ARS, amount_currency=30 USD, currency_id=USD(A)
        """
        # Crear factura: 1.000 neto + 21% = 1.210 USD
        invoice = self._create_invoice(1000, self.usd, with_iva=True)
        self.assertAlmostEqual(invoice.amount_total, 1210, places=2, msg="Total factura debe ser 1.210 USD")

        # Crear pago con retención
        payment = self._create_payment_with_withholding(self.bank_journal_usd, invoice)

        # === VALIDACIONES ===
        # A = B = USD, C = ARS
        self.assertEqual(payment.currency_id, self.usd, "A debe ser USD")
        self.assertEqual(payment.destination_currency_id, self.usd, "B debe ser USD")
        self.assertEqual(payment.company_currency_id, self.ars, "C debe ser ARS")

        # accounting_rate: formato Odoo _get_conversion_rate(USD, ARS) = 1200
        expected_accounting_rate = 1200.0
        self.assertAlmostEqual(
            payment.accounting_rate, expected_accounting_rate, places=2, msg="accounting_rate debe ser 1200 (USD→ARS)"
        )

        # selected_debt_untaxed: 1.000 USD (usa amount_residual_currency porque B≠C)
        self.assertAlmostEqual(
            payment.selected_debt_untaxed, 1000, places=2, msg="selected_debt_untaxed debe ser 1.000 USD"
        )

        # _get_withholding_rate: USD→ARS = 1200
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1200, places=2, msg="_get_withholding_rate debe ser 1200 (USD→ARS)")

        # Línea de retención
        wth_line = payment.l10n_ar_withholding_line_ids[0]

        # base_amount en C (ARS): 1.000 * 1200 = 1.200.000 ARS
        self.assertAlmostEqual(wth_line.base_amount, 1200000, places=2, msg="base_amount debe ser 1.200.000 ARS (C)")

        # amount en C (ARS): 1.200.000 * 3% = 36.000 ARS
        self.assertAlmostEqual(wth_line.amount, 36000, places=2, msg="amount debe ser 36.000 ARS")

        # withholdings_amount en B (USD): 36.000 / 1200 = 30 USD
        self.assertAlmostEqual(
            payment.withholdings_amount, 30, places=2, msg="withholdings_amount debe ser 30 USD (UX)"
        )

        # Postear y validar asiento
        payment.action_post()

        # Validar líneas de retención: balance en ARS, amount_currency en USD
        wth_move_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_tax)
        self.assertEqual(len(wth_move_lines), 1, "Debe haber 1 línea de retención")
        wth_ml = wth_move_lines[0]

        self.assertAlmostEqual(abs(wth_ml.balance), 36000, places=2, msg="Balance debe ser 36.000 ARS")
        self.assertAlmostEqual(abs(wth_ml.amount_currency), 30, places=2, msg="amount_currency debe ser 30 USD")
        self.assertEqual(wth_ml.currency_id, self.usd, "currency_id debe ser USD (A)")

    def test_t3_compra_de_divisa_ars_usd_ars(self):
        """
        T.3: Compra de divisa (A=C=ARS, B=USD, 1 USD = 1.500 ARS)

        Setup: Factura 1.210 USD (1.000 neto), pago en ARS a rate 1.500.

        Valida:
        - selected_debt_untaxed = 1.000 USD (amount_residual_currency)
        - _get_withholding_rate() = 1500 (USD→ARS, via transitividad)
        - base_amount = 1.500.000 ARS (C)
        - withholding amount = 45.000 ARS (3%)
        - withholdings_amount = 30 USD (UX: 45.000 / 1500)
        - Asiento retención (counterpart_is_foreign): currency_id=ARS, balance=amount_currency=-45.000 ARS
        - Ajuste USD en contrapartida AP (hecho en _prepare_move_lines_per_type)
        """
        # Actualizar rate a 1.500 ARS para este test
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1500.0}
        )

        # Crear factura: 1.000 neto + 21% = 1.210 USD
        invoice = self._create_invoice(1000, self.usd, with_iva=True)

        # Crear pago desde diario ARS
        payment = self._create_payment_with_withholding(self.bank_journal_ars, invoice)

        # Usuario ajusta rate a 1.500 (formato user-friendly)
        payment.user_counterpart_rate = 1500.0

        # Recomputar retenciones con el nuevo rate
        payment._compute_l10n_ar_withholding_line_ids()

        # === VALIDACIONES ===
        # A = C = ARS, B = USD
        self.assertEqual(payment.currency_id, self.ars, "A debe ser ARS")
        self.assertEqual(payment.destination_currency_id, self.usd, "B debe ser USD")
        self.assertEqual(payment.company_currency_id, self.ars, "C debe ser ARS")

        # counterpart_rate: formato Odoo = 1/1500 = 0.000667
        self.assertAlmostEqual(
            payment.counterpart_rate, 1 / 1500.0, places=6, msg="counterpart_rate debe ser ~0.000667"
        )

        # selected_debt_untaxed: 1.000 USD
        self.assertAlmostEqual(
            payment.selected_debt_untaxed, 1000, places=2, msg="selected_debt_untaxed debe ser 1.000 USD"
        )

        # _get_withholding_rate: calcula vía transitividad
        # = _get_conversion_rate(USD, ARS) = 1500
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1500, places=2, msg="_get_withholding_rate debe ser 1500 (USD→ARS)")

        # Línea de retención
        wth_line = payment.l10n_ar_withholding_line_ids[0]

        # base_amount en C: 1.000 * 1500 = 1.500.000 ARS
        self.assertAlmostEqual(wth_line.base_amount, 1500000, places=2, msg="base_amount debe ser 1.500.000 ARS (C)")

        # amount en C: 1.500.000 * 3% = 45.000 ARS
        self.assertAlmostEqual(wth_line.amount, 45000, places=2, msg="amount debe ser 45.000 ARS")

        # withholdings_amount en B (USD): 45.000 / 1500 = 30 USD
        self.assertAlmostEqual(
            payment.withholdings_amount, 30, places=2, msg="withholdings_amount debe ser 30 USD (UX)"
        )

        # Postear y validar asiento (caso counterpart_is_foreign)
        payment.action_post()

        # Validar líneas de retención: SIEMPRE en ARS cuando A=C
        wth_move_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_tax)
        self.assertEqual(len(wth_move_lines), 1, "Debe haber 1 línea de retención")
        wth_ml = wth_move_lines[0]

        self.assertAlmostEqual(abs(wth_ml.balance), 45000, places=2, msg="Balance debe ser 45.000 ARS")
        self.assertAlmostEqual(
            abs(wth_ml.amount_currency), 45000, places=2, msg="amount_currency debe ser 45.000 ARS (no USD)"
        )
        self.assertEqual(wth_ml.currency_id, self.ars, "currency_id debe ser ARS (C), NO USD")

        # Validar que el ajuste USD se hizo en la contrapartida AP
        ap_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_payable)
        self.assertEqual(len(ap_lines), 1, "Debe haber 1 línea de contrapartida AP")
        ap_line = ap_lines[0]

        # La línea AP debe estar en USD con amount_currency ajustado
        self.assertEqual(ap_line.currency_id, self.usd, "Línea AP debe estar en USD")
        # amount_currency de AP debe reflejar el total en USD (incluye ajuste de withholdings)
        # Total deuda: 1.210 USD, withholding en USD: 30 → AP debe ser 1.210 - ajuste
        # El ajuste exacto depende de _prepare_move_lines_per_type

        # Restaurar rate original
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1200.0}
        )

    def test_t4_dos_facturas_usd_distintos_rates(self):
        """
        T.4: Dos facturas USD a distintos rates, pago a rate diferente

        Setup: A=C=ARS, B=USD, pago a rate 1.500
        - Factura 1: 1.210 USD (1.000 neto), rate original 1.000
        - Factura 2: 1.210 USD (1.000 neto), rate original 1.100

        Valida:
        - selected_debt_untaxed = 2.000 USD (suma en USD)
        - base_amount = 3.000.000 ARS (2.000 * 1500, NO 1.000*1000 + 1.000*1100)
        - withholding = 90.000 ARS (3%)
        - withholdings_amount = 60 USD

        Clave: NO se usa rate histórico de cada factura, se usa rate del pago sobre el total.
        """
        # Actualizar rate a 1.500 para el pago
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1500.0}
        )

        # Crear dos facturas con rates históricos diferentes (simulado vía fecha)
        invoice1 = self._create_invoice(1000, self.usd, with_iva=True)
        invoice2 = self._create_invoice(1000, self.usd, with_iva=True)

        # Crear pago que paga ambas facturas
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal_ars.id,
                "partner_id": self.partner_ri.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [
                    Command.set(
                        (invoice1 | invoice2)
                        .line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
                        .ids
                    )
                ],
            }
        )

        # Usuario ajusta rate a 1.500
        payment.user_counterpart_rate = 1500.0

        # === VALIDACIONES ===
        # selected_debt_untaxed: (1.210 + 1.210) / 1.21 = 2.000 USD
        self.assertAlmostEqual(
            payment.selected_debt_untaxed, 2000, places=2, msg="selected_debt_untaxed debe ser 2.000 USD"
        )

        # _get_withholding_rate = 1500
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1500, places=2, msg="Rate debe ser 1500")

        # base_amount: 2.000 * 1500 = 3.000.000 ARS (NO 2.100.000)
        wth_line = payment.l10n_ar_withholding_line_ids[0]
        self.assertAlmostEqual(
            wth_line.base_amount,
            3000000,
            places=2,
            msg="base_amount debe ser 3.000.000 ARS (rate del pago, NO rates históricos)",
        )

        # amount: 3.000.000 * 3% = 90.000 ARS
        self.assertAlmostEqual(wth_line.amount, 90000, places=2, msg="amount debe ser 90.000 ARS")

        # withholdings_amount: 90.000 / 1500 = 60 USD
        self.assertAlmostEqual(payment.withholdings_amount, 60, places=2, msg="withholdings_amount debe ser 60 USD")

        # Restaurar rate
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1200.0}
        )

    def test_t5_pago_parcial_ars_usd_ars(self):
        """
        T.5: Pago parcial (A=C=ARS, B=USD, 1 USD = 1.500 ARS)

        Setup: Factura 2.420 USD (2.000 neto), pago 750.000 ARS → 500 USD.

        Valida:
        - selected_debt = 2.420 USD
        - to_pay_amount = 500 USD
        - unreconciled_amount = -1.920 USD
        - withholdable_advanced_amount = -1.920 * (2.000/2.420) = -1.586,78 USD
        - base_in_b = 2.000 + (-1.586,78) = 413,22 USD
        - base_amount = 619.835 ARS (413,22 * 1500)
        - withholding = 18.595 ARS (3%)
        - UX = 12,40 USD
        """
        # Actualizar rate a 1.500
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1500.0}
        )

        # Crear factura: 2.000 neto + 21% = 2.420 USD
        invoice = self._create_invoice(2000, self.usd, with_iva=True)
        self.assertAlmostEqual(invoice.amount_total, 2420, places=2, msg="Total debe ser 2.420 USD")

        # Crear pago desde ARS por monto fijo 750.000 ARS (= 500 USD a rate 1.500)
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal_ars.id,
                "partner_id": self.partner_ri.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "amount": 750000,  # ARS
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [
                    Command.set(
                        invoice.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable").ids
                    )
                ],
            }
        )

        # Usuario ajusta rate a 1.500
        payment.user_counterpart_rate = 1500.0

        # === VALIDACIONES ===
        # selected_debt: 2.420 USD
        self.assertAlmostEqual(payment.selected_debt, 2420, places=2, msg="selected_debt debe ser 2.420 USD")

        # to_pay_amount: 750.000 / 1500 = 500 USD
        self.assertAlmostEqual(payment.to_pay_amount, 500, places=2, msg="to_pay_amount debe ser 500 USD")

        # unreconciled_amount: 500 - 2.420 = -1.920 USD
        self.assertAlmostEqual(
            payment.unreconciled_amount, -1920, places=2, msg="unreconciled_amount debe ser -1.920 USD"
        )

        # withholdable_advanced_amount (calculado en _compute_base_amount)
        # = -1.920 * (2.000 / 2.420) = -1.586,78 USD
        expected_advance = -1920 * (2000 / 2420)
        self.assertAlmostEqual(
            payment.withholdable_advanced_amount,
            expected_advance,
            places=2,
            msg="withholdable_advanced_amount incorrecto",
        )

        # base_in_b = 2.000 + (-1.586,78) = 413,22 USD
        expected_base_in_b = 2000 + expected_advance

        # base_amount = 413,22 * 1500 = 619.835 ARS
        wth_line = payment.l10n_ar_withholding_line_ids[0]
        expected_base_ars = expected_base_in_b * 1500
        self.assertAlmostEqual(wth_line.base_amount, expected_base_ars, places=0, msg="base_amount incorrecto")

        # withholding = 619.835 * 3% = 18.595 ARS
        expected_wth = expected_base_ars * 0.03
        self.assertAlmostEqual(wth_line.amount, expected_wth, places=0, msg="amount incorrecto")

        # UX = 18.595 / 1500 ~ 12,40 USD
        expected_wth_usd = expected_wth / 1500
        self.assertAlmostEqual(
            payment.withholdings_amount, expected_wth_usd, places=2, msg="withholdings_amount incorrecto"
        )

        # Restaurar rate
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1200.0}
        )

    def test_t6_arbitraje_usd_eur_ars(self):
        """
        T.6: Arbitraje (A=USD, B=EUR, C=ARS)

        Setup: Factura 1.210 EUR (1.000 neto), pago en USD.
        Rates: 1 USD = 1.200 ARS, 1 EUR = 1.320 ARS

        Valida:
        - selected_debt_untaxed = 1.000 EUR
        - _get_withholding_rate: calcula EUR→ARS vía transitividad = 1320
        - base_amount = 1.320.000 ARS (C)
        - withholding = 39.600 ARS (3%)
        - withholdings_amount = 30 EUR (39.600 / 1320)
        - Asiento: balance=39.600 ARS, amount_currency=33 USD (39.600/1200), currency_id=USD(A)
        """
        # Crear factura: 1.000 neto + 21% = 1.210 EUR
        invoice = self._create_invoice(1000, self.eur, with_iva=True)

        # Crear pago desde diario USD
        payment = self._create_payment_with_withholding(self.bank_journal_usd, invoice)

        # === VALIDACIONES ===
        # A = USD, B = EUR, C = ARS
        self.assertEqual(payment.currency_id, self.usd, "A debe ser USD")
        self.assertEqual(payment.destination_currency_id, self.eur, "B debe ser EUR")
        self.assertEqual(payment.company_currency_id, self.ars, "C debe ser ARS")

        # selected_debt_untaxed: 1.000 EUR
        self.assertAlmostEqual(
            payment.selected_debt_untaxed, 1000, places=2, msg="selected_debt_untaxed debe ser 1.000 EUR"
        )

        # _get_withholding_rate: EUR→ARS vía transitividad
        # Odoo calcula: _get_conversion_rate(EUR, ARS) = 1320
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1320, places=2, msg="_get_withholding_rate debe ser 1320 (EUR→ARS)")

        # Línea de retención
        wth_line = payment.l10n_ar_withholding_line_ids[0]

        # base_amount: 1.000 * 1320 = 1.320.000 ARS
        self.assertAlmostEqual(wth_line.base_amount, 1320000, places=2, msg="base_amount debe ser 1.320.000 ARS")

        # amount: 1.320.000 * 3% = 39.600 ARS
        self.assertAlmostEqual(wth_line.amount, 39600, places=2, msg="amount debe ser 39.600 ARS")

        # withholdings_amount: 39.600 / 1320 = 30 EUR
        self.assertAlmostEqual(
            payment.withholdings_amount, 30, places=2, msg="withholdings_amount debe ser 30 EUR (UX)"
        )

        # Postear y validar asiento
        payment.action_post()

        # Validar líneas de retención: balance en ARS, amount_currency en USD (A)
        wth_move_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_tax)
        wth_ml = wth_move_lines[0]

        self.assertAlmostEqual(abs(wth_ml.balance), 39600, places=2, msg="Balance debe ser 39.600 ARS")
        # amount_currency: 39.600 / 1200 = 33 USD (convierte a moneda del pago A)
        expected_amount_currency = 39600 / 1200
        self.assertAlmostEqual(
            abs(wth_ml.amount_currency), expected_amount_currency, places=2, msg="amount_currency debe ser 33 USD"
        )
        self.assertEqual(wth_ml.currency_id, self.usd, "currency_id debe ser USD (A)")

    def test_t7_ganancias_con_acumulado(self):
        """
        T.7: Ganancias con acumulado del período (A=C=ARS, B=USD)

        Setup: Ya hay retenciones del período por 500.000 ARS (base) y 15.000 ARS (retenido).
               Factura nueva: 1.210 USD (1.000 neto), rate 1.500.
               Retención ganancias 7%, mínimo no imponible 100.000 ARS.

        Valida:
        - base_amount = 1.500.000 ARS (1.000 * 1500)
        - same_period_base = 500.000 ARS (de move lines, ya en C)
        - net_amount = 1.500.000 + 500.000 - 100.000 = 1.900.000 ARS (C + C)
        - withholding = 1.900.000 * 7% = 133.000 ARS
        - withholding neto = 133.000 - 15.000 = 118.000 ARS
        - withholdings_amount = 118.000 / 1500 ~ 78,67 USD
        """
        # Actualizar rate a 1.500
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1500.0}
        )

        # === Crear retenciones previas del período ===
        # Simular un pago anterior con retenciones de ganancias
        # Base: 500.000 ARS, Retenido: 15.000 ARS (3% - simplificado)

        # Crear asiento manual de retención previa
        prev_payment_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": self.today,
                "journal_id": self.bank_journal_ars.id,
                "line_ids": [
                    # Línea de retención (tax_line)
                    Command.create(
                        {
                            "name": "Retención Ganancias Previa",
                            "account_id": self.account_tax.id,
                            "partner_id": self.partner_ri.id,
                            "debit": 15000,
                            "credit": 0,
                            "tax_line_id": self.tax_ret_ganancias_7.id,
                        }
                    ),
                    # Línea base retención (tax_ids)
                    Command.create(
                        {
                            "name": "Base Retención Previa",
                            "account_id": self.account_tax_base.id,
                            "partner_id": self.partner_ri.id,
                            "debit": 500000,
                            "credit": 0,
                            "tax_ids": [Command.set([self.tax_ret_ganancias_7.id])],
                        }
                    ),
                    # Contrapartida base
                    Command.create(
                        {
                            "name": "Base Contrapartida",
                            "account_id": self.account_tax_base.id,
                            "partner_id": self.partner_ri.id,
                            "debit": 0,
                            "credit": 500000,
                        }
                    ),
                    # Contrapartida (payable)
                    Command.create(
                        {
                            "name": "Contrapartida Payable",
                            "account_id": self.account_payable.id,
                            "partner_id": self.partner_ri.id,
                            "debit": 0,
                            "credit": 15000,
                        }
                    ),
                ],
            }
        )
        prev_payment_move.action_post()

        # === Crear nuevo pago con factura USD ===
        # Crear factura: 1.000 neto + 21% = 1.210 USD
        invoice = self._create_invoice(1000, self.usd, with_iva=True)

        # Crear fiscal position con retención de ganancias
        fiscal_pos_ganancias = self.env["account.fiscal.position"].create(
            {
                "name": "FP Ganancias",
                "company_id": self.company.id,
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": self.tax_ret_ganancias_7.id, "tax_type": "withholding"})
                ],
            }
        )

        # Crear pago
        payment = self._create_payment_with_withholding(self.bank_journal_ars, invoice, fiscal_pos_ganancias)
        payment.user_counterpart_rate = 1500.0

        # === VALIDACIONES ===
        # _get_withholding_rate = 1500
        rate = payment._get_withholding_rate()
        self.assertAlmostEqual(rate, 1500, places=2, msg="Rate debe ser 1500")

        # base_amount: 1.000 * 1500 = 1.500.000 ARS
        wth_line = payment.l10n_ar_withholding_line_ids[0]
        self.assertAlmostEqual(wth_line.base_amount, 1500000, places=2, msg="base_amount debe ser 1.500.000 ARS")

        # same_period_base: 500.000 ARS (de move lines previas)
        same_period_base = wth_line._get_same_period_base_amount()
        self.assertAlmostEqual(same_period_base, 500000, places=2, msg="same_period_base debe ser 500.000 ARS")

        # net_amount: 1.500.000 + 500.000 - 100.000 = 1.900.000 ARS (C + C, correcto)
        expected_net = 1500000 + 500000 - 100000

        # withholding: 1.900.000 * 7% = 133.000 ARS
        expected_gross_wth = expected_net * 0.07

        # same_period_withholdings: 15.000 ARS
        same_period_wth = wth_line._get_same_period_withholdings_amount()
        self.assertAlmostEqual(same_period_wth, 15000, places=2, msg="same_period_withholdings debe ser 15.000 ARS")

        # withholding neto: 133.000 - 15.000 = 118.000 ARS
        expected_net_wth = expected_gross_wth - same_period_wth
        self.assertAlmostEqual(wth_line.amount, expected_net_wth, places=0, msg="amount debe ser ~118.000 ARS")

        # withholdings_amount: 118.000 / 1500 ~ 78,67 USD
        expected_wth_usd = expected_net_wth / 1500
        self.assertAlmostEqual(
            payment.withholdings_amount, expected_wth_usd, places=2, msg="withholdings_amount debe ser ~78,67 USD"
        )

        # Restaurar rate
        self.env["res.currency.rate"].search([("currency_id", "=", self.usd.id)]).write(
            {"inverse_company_rate": 1200.0}
        )
