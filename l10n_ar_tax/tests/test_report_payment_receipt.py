"""
Tests para los valores de campos usados en report_payment_receipt_templates.xml
================================================================================

Validan los 3 escenarios de columnas del recibo multimoneda:

  Caso 1 — Arbitraje, pago único:  A=EUR, B=USD, C=ARS
  Caso 2 — Bundle EUR + USD:       A1=EUR / A2=USD, B=USD, C=ARS
  Caso 3 — Reconcile on company:   A=EUR / A=USD, B=ARS, C=ARS
  Caso 3b— Reconcile + deuda USD:  A=ARS, B1=USD, B2=ARS, C=ARS (B1!=B2)

Template usa:
  show_amount_col = any(doc.currency_id != o.destination_currency_id for doc in bundle)
                    or bool(withholdings and destination != company)

  Columna "Importe" (natural):
    · Pagos:      doc.amount_signed         (en A, currency_id del diario)
    · Cheques:    check.amount              (en A)
    · Retención:  line.amount               (en ARS, currency_id = company_currency_id)
    · Write-off:  doc.write_off_amount      (en B)

  Columna "Importe B":
    · Pagos:      counterpart_currency_amount      si B1==B2
                  amount / accounting_rate          si B1!=B2
    · Cheques:    check.amount * counterpart_rate   si B1==B2
                  check.amount / accounting_rate    si B1!=B2
    · Retención:  line.amount / line.payment_id._get_withholding_rate()
    · Write-off:  doc.write_off_amount

  Total Paid: sum(payment_bundle.mapped('payment_total'))  → ya en B
"""

from odoo import Command
from odoo.addons.l10n_ar_tax.tests.test_payment_withholding_multimoneda import TestPaymentWithholdingMultimoneda
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestReportPaymentReceipt(TestPaymentWithholdingMultimoneda):
    """Valida campos utilizados por report_payment_receipt_templates.xml."""

    # ------------------------------------------------------------------
    # Helper: replica la condición show_amount_col del template
    # ------------------------------------------------------------------

    def _show_amount_col(self, payment_bundle):
        """Replica:
        any(doc.currency_id != o.destination_currency_id for doc in bundle)
        or bool(withholdings and destination != company)
        """
        # payment_bundle es un recordset; o = payment_bundle[0]
        o = payment_bundle[:1]
        has_wth = bool(payment_bundle.l10n_ar_withholding_line_ids.filtered("amount"))
        return any(doc.currency_id != o.destination_currency_id for doc in payment_bundle) or (
            has_wth and o.destination_currency_id != o.company_currency_id
        )

    # ------------------------------------------------------------------
    # Caso 1: A=EUR, B=USD, C=ARS — pago único con retención
    # ------------------------------------------------------------------

    def test_case1_arbitrage_single_payment(self):
        """
        Escenario: Factura en USD, pago en EUR. A=EUR, B=USD, C=ARS.
          1 USD = 1200 ARS, 1 EUR = 1320 ARS → 1 EUR ≈ 1.1 USD.

        Columna "Importe":    pago en EUR, retención en ARS.
        Columna "Importe USD": pago en USD (counterpart_currency_amount), retención en USD.
        show_amount_col = True (EUR != USD).
        """
        invoice = self._create_invoice(1_000, self.usd)
        payment = self._create_payment_with_wth(self.bank_eur, invoice)

        # destination_currency_id = B = USD
        self.assertEqual(payment.destination_currency_id, self.usd)

        # show_amount_col: EUR != USD → True
        self.assertTrue(self._show_amount_col(payment))

        # --- Columna "Importe" (moneda natural del pago = EUR) ---
        self.assertEqual(payment.currency_id, self.eur)
        self.assertGreater(payment.amount, 0)

        # --- Columna "Importe USD" (counterpart_currency_amount) ---
        self.assertEqual(payment.counterpart_currency_id, self.usd)
        self.assertGreater(payment.counterpart_currency_amount, 0)
        # Relación: B = A * counterpart_rate
        self.assertAlmostEqual(
            payment.counterpart_currency_amount,
            payment.amount * payment.counterpart_rate,
            places=2,
        )

        # --- Retención ---
        wth = self._wth_line(payment)

        # Columna "Importe" de retención = ARS (company_currency)
        self.assertEqual(wth.currency_id, self.ars)
        self.assertGreater(wth.amount, 0)

        # Columna "Importe USD" de retención = amount / _get_withholding_rate()
        rate = payment._get_withholding_rate()
        self.assertGreater(rate, 0)
        expected_usd = payment.destination_currency_id.round(wth.amount / rate)
        self.assertAlmostEqual(expected_usd, wth.amount / rate, places=2)
        self.assertGreater(expected_usd, 0)

        # --- payment_total (suma para el footer) ---
        # Incluye counterpart_currency_amount + withholdings_amount, ambos en B (USD)
        self.assertAlmostEqual(
            payment.payment_total,
            payment.counterpart_currency_amount + payment.withholdings_amount,
            places=2,
        )

    # ------------------------------------------------------------------
    # Caso 2: Bundle EUR + USD -> B=USD
    # ------------------------------------------------------------------

    def test_case2_bundle_eur_and_usd(self):
        """
        Bundle de 2 pagos contra deuda en USD:
          - Pago 1: journal EUR (A=EUR, B=USD).
          - Pago 2: journal USD (A=USD, B=USD).

        show_amount_col = True porque EUR != USD.
        Cada pago usa sus propias tasas para la retención.
        """
        inv1 = self._create_invoice(1_000, self.usd)
        inv2 = self._create_invoice(1_000, self.usd)

        p1 = self._create_payment_with_wth(self.bank_eur, inv1)
        p2 = self._create_payment_with_wth(self.bank_usd, inv2)

        # Simular el bundle como lo armaría _get_payment_bundles
        bundle = p1 | p2

        # show_amount_col: p1 tiene EUR != USD → True
        self.assertTrue(self._show_amount_col(bundle))

        # --- destination_currency_id = USD para ambos ---
        self.assertEqual(p1.destination_currency_id, self.usd)
        self.assertEqual(p2.destination_currency_id, self.usd)

        # --- Monedas naturales (columna "Importe") ---
        self.assertEqual(p1.currency_id, self.eur)
        self.assertEqual(p2.currency_id, self.usd)

        # --- Columna "Importe USD" para cada pago ---
        # p1: EUR * counterpart_rate → USD
        self.assertAlmostEqual(
            p1.counterpart_currency_amount,
            p1.amount * p1.counterpart_rate,
            places=2,
        )
        # p2: USD → USD (counterpart_rate ≈ 1.0)
        self.assertAlmostEqual(p2.counterpart_rate, 1.0, places=4)
        self.assertAlmostEqual(p2.counterpart_currency_amount, p2.amount, places=2)

        # --- Retenciones: cada línea usa el rate de SU pago ---
        wth1 = p1.l10n_ar_withholding_line_ids.filtered("amount")[:1]
        wth2 = p2.l10n_ar_withholding_line_ids.filtered("amount")[:1]
        self.assertTrue(wth1 and wth2)

        # p2: A=B=USD, rate = 1200 ARS/USD
        self.assertAlmostEqual(p2._get_withholding_rate(), 1_200, delta=1)

        # Conversión retención p1 (EUR diario): wth1.amount / _get_withholding_rate()
        rate1 = p1._get_withholding_rate()
        self.assertGreater(rate1, 0)
        wth1_usd = p1.destination_currency_id.round(wth1.amount / rate1)
        self.assertGreater(wth1_usd, 0)

        # Conversión retención p2 (USD diario): wth2.amount / 1200
        wth2_usd = p2.destination_currency_id.round(wth2.amount / p2._get_withholding_rate())
        self.assertGreater(wth2_usd, 0)

        # --- Total Paid (footer) = suma de payment_total de cada pago, ya en USD ---
        total_paid = sum(bundle.mapped("payment_total"))
        self.assertGreater(total_paid, 0)
        # Debe ser >= suma de counterpart_currency_amounts (withholdings también suman)
        self.assertGreaterEqual(
            total_paid,
            p1.counterpart_currency_amount + p2.counterpart_currency_amount,
        )

    # ------------------------------------------------------------------
    # Caso 3: reconcile_on_company_currency → B=ARS
    # ------------------------------------------------------------------

    def test_case3_reconcile_on_company_currency(self):
        """
        reconcile_on_company_currency=True → destination_currency_id = ARS (= C).
        Bundle EUR + USD pagando deuda en ARS.

        Columna "Importe":   pago1 en EUR, pago2 en USD, retención en ARS.
        Columna "Importe ARS": todo en ARS (counterpart_currency_amount).
        show_amount_col = True (EUR != ARS, USD != ARS).
        """
        if not hasattr(self.company, "reconcile_on_company_currency"):
            self.skipTest("account_ux no instalado; reconcile_on_company_currency no disponible")

        self.company.reconcile_on_company_currency = True
        self.addCleanup(lambda: self.company.write({"reconcile_on_company_currency": False}))

        # Dos facturas en ARS (la cuenta AP no tiene currency_id)
        inv1 = self._create_invoice(1_500, self.ars)
        inv2 = self._create_invoice(1_000, self.ars)

        p_eur = self._create_payment_with_wth(self.bank_eur, inv1)
        p_usd = self._create_payment_with_wth(self.bank_usd, inv2)

        # Con reconcile_on_company_currency, destination = ARS
        self.assertEqual(p_eur.destination_currency_id, self.ars)
        self.assertEqual(p_usd.destination_currency_id, self.ars)

        bundle = p_eur | p_usd

        # show_amount_col: EUR!=ARS → True (indep. de retenciones)
        self.assertTrue(self._show_amount_col(bundle))

        # Encabezado "Importe ARS": o.destination_currency_id.name = 'ARS'
        self.assertEqual(bundle[:1].destination_currency_id.name, "ARS")

        # --- Columna "Importe" (moneda natural) ---
        self.assertEqual(p_eur.currency_id, self.eur)
        self.assertEqual(p_usd.currency_id, self.usd)

        # --- Columna "Importe ARS" (counterpart_currency_amount en ARS) ---
        # EUR → ARS: amount * counterpart_rate (ARS/EUR ≈ 1320)
        self.assertAlmostEqual(
            p_eur.counterpart_currency_amount,
            p_eur.amount * p_eur.counterpart_rate,
            places=2,
        )
        # USD → ARS: amount * counterpart_rate (ARS/USD = 1200)
        self.assertAlmostEqual(
            p_usd.counterpart_currency_amount,
            p_usd.amount * p_usd.counterpart_rate,
            places=2,
        )
        # Ambos en ARS (> 0)
        self.assertGreater(p_eur.counterpart_currency_amount, 0)
        self.assertGreater(p_usd.counterpart_currency_amount, 0)

        # --- Retenciones: destination=ARS=company → _get_withholding_rate = 1.0 ---
        # (no hace falta convertir: retención ya está en ARS = B)
        self.assertAlmostEqual(p_eur._get_withholding_rate(), 1.0, places=4)
        self.assertAlmostEqual(p_usd._get_withholding_rate(), 1.0, places=4)

        for p in (p_eur, p_usd):
            wth = p.l10n_ar_withholding_line_ids.filtered("amount")[:1]
            if not wth:
                continue
            wth_ars = p.destination_currency_id.round(wth.amount / p._get_withholding_rate())
            # Con rate=1.0, importe en B = importe en ARS sin conversión
            self.assertAlmostEqual(wth_ars, wth.amount, places=2)

    # ------------------------------------------------------------------
    # Caso base — A=B=C=ARS sin retenciones: NO muestra columna extra
    # ------------------------------------------------------------------

    def test_no_amount_col_local_ars(self):
        """Pago local ARS sin retenciones: show_amount_col = False."""
        inv = self._create_invoice(1_000, self.ars)
        p = self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "to_pay_move_line_ids": [
                    Command.set(inv.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable").ids)
                ],
            }
        )
        # Sin retenciones
        self.assertFalse(p.l10n_ar_withholding_line_ids)
        self.assertEqual(p.destination_currency_id, self.ars)
        self.assertFalse(self._show_amount_col(p))

    # ------------------------------------------------------------------
    # Caso A=B=USD con retenciones: SÍ muestra columna extra (ARS ≠ USD)
    # ------------------------------------------------------------------

    def test_show_amount_col_usd_with_withholdings(self):
        """Pago USD puro con retención: show_amount_col = True
        porque la retencia está en ARS != USD."""
        inv = self._create_invoice(1_000, self.usd)
        p = self._create_payment_with_wth(self.bank_usd, inv)

        # A=B=USD → any(USD != USD) = False, pero tienen wth y USD != ARS → True
        self.assertEqual(p.destination_currency_id, self.usd)
        any_different = any(doc.currency_id != p.destination_currency_id for doc in p)
        self.assertFalse(any_different)
        self.assertTrue(
            self._show_amount_col(p),
            "show_amount_col debe ser True: retenciones en ARS != USD",
        )

    # ------------------------------------------------------------------
    # Caso 3b: reconcile_on_company_currency + deuda USD → B1!=B2
    # ------------------------------------------------------------------

    def test_case3b_reconcile_with_usd_debt(self):
        """reconcile_on_company_currency=True, factura en USD, pago en ARS.
        El usuario fuerza counterpart_currency_id=USD.
        B1=USD, B2=ARS → B1!=B2.

        La columna "Amount" del recibo debe mostrar tanto cheques como pagos
        regulares en ARS (destination_currency_id), NO en USD.
        Fórmula correcta: amount / accounting_rate (cuando B1!=B2).
        Fórmula incorrecta (bug): amount * counterpart_rate → da USD.
        """
        if not hasattr(self.company, "reconcile_on_company_currency"):
            self.skipTest("account_ux no instalado; reconcile_on_company_currency no disponible")

        self.company.reconcile_on_company_currency = True
        self.addCleanup(lambda: self.company.write({"reconcile_on_company_currency": False}))

        # Factura 1000 USD (neto, sin IVA para simplificar)
        inv = self._create_invoice(1_000, self.usd)

        # Pago desde banco ARS
        debt = inv.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
                # Forzar counterpart a USD (usuario elige ver cotización en USD)
                "counterpart_currency_id": self.usd.id,
            }
        )

        # --- Precondiciones ---
        self.assertEqual(payment.currency_id, self.ars, "A = ARS")
        self.assertEqual(payment.counterpart_currency_id, self.usd, "B1 = USD")
        self.assertEqual(payment.destination_currency_id, self.ars, "B2 = ARS")
        self.assertNotEqual(
            payment.counterpart_currency_id,
            payment.destination_currency_id,
            "B1 != B2: este es el caso del bug",
        )

        # --- Monto del cheque en destination_currency_id (ARS) ---
        # check.amount está en ARS (= currency_id del pago)
        check_amount = payment.amount  # 1,200,000 ARS (o similar)
        self.assertGreater(check_amount, 0)

        # Fórmula INCORRECTA (bug): da el monto en USD, no en ARS
        wrong_amount = payment.destination_currency_id.round(check_amount * (payment.counterpart_rate or 1.0))
        # wrong_amount ≈ 1000 USD mostrado como ARS → claramente wrong
        self.assertNotEqual(
            wrong_amount,
            check_amount,
            "check.amount * counterpart_rate != check.amount: confirma el bug (convierte a B1, no a B2)",
        )

        # Fórmula CORRECTA: cuando B1!=B2, usar amount / accounting_rate
        correct_amount = payment.destination_currency_id.round(
            check_amount / payment.accounting_rate if payment.accounting_rate else check_amount
        )
        # Con A=C=ARS, accounting_rate=1 → correct_amount = check_amount
        self.assertEqual(
            correct_amount,
            check_amount,
            "Fórmula correcta: check.amount / accounting_rate debe dar el monto en ARS",
        )

        # --- payment_total: ya usa la lógica correcta en _compute_payment_total ---
        self.assertAlmostEqual(
            payment.payment_total,
            check_amount,
            places=2,
            msg="payment_total ya maneja B1!=B2 correctamente",
        )

        # --- Pagos regulares (no cheques): display_amount_b ---
        # counterpart_currency_amount está en B1 (USD), pero debe mostrarse en B2 (ARS)
        wrong_regular = payment.counterpart_currency_amount  # en USD
        correct_regular = payment.amount / payment.accounting_rate if payment.accounting_rate else payment.amount
        self.assertNotEqual(
            payment.destination_currency_id.round(wrong_regular),
            payment.destination_currency_id.round(correct_regular),
            "counterpart_currency_amount (B1) != amount/accounting_rate (B2): confirma el bug en pagos regulares",
        )
        self.assertAlmostEqual(
            correct_regular,
            payment.amount,
            places=2,
            msg="Con A=C=ARS, amount/accounting_rate = amount (en ARS)",
        )
