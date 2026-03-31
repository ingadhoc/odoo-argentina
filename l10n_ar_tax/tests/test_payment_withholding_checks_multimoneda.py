from odoo import Command
from odoo.addons.l10n_ar_tax.tests.test_payment_withholding_multimoneda import TestPaymentWithholdingMultimoneda
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentChecksWithholding(TestPaymentWithholdingMultimoneda):
    """Pruebas de pagos con cheques propios + retenciones (l10n_latam_check + l10n_ar_tax).

    Valida que la combinación de N líneas de liquidez (un cheque por línea, F.2)
    y el cálculo de retenciones argentinas funciona correctamente en los
    distintos escenarios de moneda.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Agregar método de pago "Cheques propios" a los diarios de banco ARS y USD (si no existe ya)
        own_checks_method = cls.env.ref("l10n_latam_check.account_payment_method_own_checks")
        for journal in (cls.bank_ars, cls.bank_usd):
            already = journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == "own_checks")
            if not already:
                journal.write(
                    {"outbound_payment_method_line_ids": [Command.create({"payment_method_id": own_checks_method.id})]}
                )

        # Write-off type para TC.8
        cls.account_write_off = cls.env["account.account"].create(
            {
                "name": "Write Off Test",
                "code": "TWOFF",
                "account_type": "expense",
                "company_ids": [Command.set([cls.company.id])],
            }
        )
        cls.write_off_type = cls.env["account.write_off.type"].create(
            {
                "name": "Write off",
                "account_id": cls.account_write_off.id,
            }
        )

    def _own_checks_pml(self, journal):
        """Devuelve la payment method line 'own_checks' del diario dado."""
        return journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == "own_checks")

    def _create_check_payment_with_wth(self, journal, invoice, checks, fiscal_position=None, **kw):
        """Crea pago proveedor con cheques propios y retenciones, en borrador.

        ``checks``: lista de dicts con claves ``name``, ``amount``, y
        opcionalmente ``payment_date`` (default: today).
        """
        fp = fiscal_position or self.fp_iibb
        debt = invoice.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        vals = {
            "journal_id": journal.id,
            "partner_id": self.partner.id,
            "partner_type": "supplier",
            "payment_type": "outbound",
            "date": self.today,
            "payment_method_line_id": self._own_checks_pml(journal).id,
            "l10n_ar_fiscal_position_id": fp.id,
            "to_pay_move_line_ids": [Command.set(debt.ids)],
            "l10n_latam_new_check_ids": [
                Command.create(
                    {
                        "name": c["name"],
                        "payment_date": c.get("payment_date", self.today),
                        "amount": c["amount"],
                    }
                )
                for c in checks
            ],
        }
        vals.update(kw)
        payment = self.env["account.payment"].create(vals)
        payment._onchange_withholdings()
        return payment

    # ------------------------------------------------------------------
    # TC.6 — 1 cheque ARS + IIBB 3% (A=B=C=ARS)
    # ------------------------------------------------------------------

    def test_tc6_cheque_ars_con_iibb(self):
        """TC.6 · 1 cheque propio en ARS + retención IIBB 3% (A=B=C=ARS).

        Factura 1 210 ARS (1 000 neto + 210 IVA). 1 cheque de 1 180 ARS.

        Verifica:
        - Retención 30 ARS (= 1 000 * 3%)
        - payment.amount = 1 180 ARS (neto pagado)
        - 3 líneas en el asiento: 1 liquidez + 1 retención + 1 contrapartida
        - sum(balances) == 0
        """
        invoice = self._create_invoice(1_000, self.ars)
        payment = self._create_check_payment_with_wth(
            self.bank_ars,
            invoice,
            [{"name": "00000100", "amount": 1180}],
        )

        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_000, places=2)
        self.assertAlmostEqual(wth.amount, 30, places=2)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)
        self.assertAlmostEqual(payment.amount, 1_180, places=2)

        payment.action_post()

        lines = payment.move_id.line_ids
        liq_lines = lines.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        wth_ml = self._wth_move_lines(payment)
        cp = lines.filtered(lambda l: l.account_id == payment.destination_account_id)

        self.assertEqual(len(liq_lines), 1, "1 cheque → 1 línea de liquidez")
        self.assertEqual(len(wth_ml), 1, "1 línea de retención")
        self.assertEqual(len(cp), 1, "1 contrapartida")
        # 1 liq + 1 wth_tax + 2 base_ret (Base Ret + Base Ret Cont) + 1 cp
        self.assertEqual(len(lines), 5)

        self.assertAlmostEqual(liq_lines.balance, -1_180, places=2)
        self.assertAlmostEqual(abs(wth_ml.balance), 30, places=2)
        self.assertAlmostEqual(cp.balance, 1_210, places=2, msg="AP = cheque + retención")
        self.assertAlmostEqual(sum(lines.mapped("balance")), 0, places=2)

    # ------------------------------------------------------------------
    # TC.7 — 2 cheques ARS + IIBB 3% para deuda USD (A=C=ARS, B=USD)
    # ------------------------------------------------------------------

    def test_tc7_dos_cheques_compra_divisa_con_iibb(self):
        """TC.7 · 2 cheques ARS + IIBB 3% para deuda USD (A=C=ARS, B=USD,
        1 USD = 1200 ARS).

        Factura 1 210 USD (1 000 neto). 2 cheques de 716 000 y 700 000 ARS
        (total 1 416 000 = (1 210 - 30) × 1 200).

        Verifica (base en C=ARS, UX en B=USD):
        - base_amount = 1 000 * 1200 = 1 200 000 ARS
        - withholding  = 1 200 000 * 3% = 36 000 ARS
        - withholdings_amount = 36 000 / 1200 = 30 USD
        - 4 líneas: 2 liquidez + 1 retención + 1 contrapartida
        - sum(balances) == 0
        """
        invoice = self._create_invoice(1_000, self.usd)
        payment = self._create_check_payment_with_wth(
            self.bank_ars,
            invoice,
            [
                {"name": "00000110", "amount": 716_000},
                {"name": "00000111", "amount": 700_000},
            ],
        )

        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_200_000, places=0)
        self.assertAlmostEqual(wth.amount, 36_000, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)

        payment.action_post()

        lines = payment.move_id.line_ids
        liq_lines = lines.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        wth_ml = self._wth_move_lines(payment)
        cp = lines.filtered(lambda l: l.account_id == payment.destination_account_id)

        self.assertEqual(len(liq_lines), 2, "2 cheques → 2 líneas de liquidez")
        self.assertEqual(len(wth_ml), 1)
        self.assertEqual(len(cp), 1)
        # 2 liq + 1 wth_tax + 2 base_ret + 1 cp
        self.assertEqual(len(lines), 6)

        # Liquidez en ARS: balance = amount_currency (accounting_rate = 1.0)
        for liq in liq_lines:
            self.assertEqual(liq.currency_id, self.ars)
            self.assertAlmostEqual(liq.balance, liq.amount_currency, places=2)

        # Retención siempre en ARS (compra divisa)
        self.assertEqual(wth_ml.currency_id, self.ars)
        self.assertAlmostEqual(abs(wth_ml.balance), 36_000, places=0)

        # Contrapartida en USD (B)
        self.assertEqual(cp.currency_id, self.usd)
        self.assertAlmostEqual(sum(lines.mapped("balance")), 0, places=2)

    # ------------------------------------------------------------------
    # TC.8 — 2 cheques ARS + IIBB + write-off (A=C=ARS, B=USD)
    # ------------------------------------------------------------------

    def test_tc8_dos_cheques_con_iibb_y_write_off(self):
        """TC.8 · 2 cheques ARS + IIBB + write-off para deuda USD
        (A=C=ARS, B=USD, 1 USD = 1200 ARS).

        Factura 1 210 USD (1 000 neto). 2 cheques de 678 000 y 678 000 ARS
        (total 1 356 000 = (1 210 - 30 - 50) × 1 200) + write-off 50 USD.

        Verifica:
        - 5 líneas: 2 liquidez + 1 retención + 1 write-off + 1 contrapartida
        - sum(balances) == 0
        """
        invoice = self._create_invoice(1_000, self.usd)
        debt = invoice.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "payment_method_line_id": self._own_checks_pml(self.bank_ars).id,
                "l10n_ar_fiscal_position_id": self.fp_iibb.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
                "write_off_type_id": self.write_off_type.id,
                "write_off_amount": 50,
                "l10n_latam_new_check_ids": [
                    Command.create({"name": "00000120", "payment_date": self.today, "amount": 678_000}),
                    Command.create({"name": "00000121", "payment_date": self.today, "amount": 678_000}),
                ],
            }
        )
        payment._onchange_withholdings()

        payment.action_post()

        lines = payment.move_id.line_ids
        liq_lines = lines.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        wth_ml = self._wth_move_lines(payment)
        wo_line = lines.filtered(lambda l: l.account_id == self.write_off_type.account_id)
        cp = lines.filtered(lambda l: l.account_id == payment.destination_account_id)

        self.assertEqual(len(liq_lines), 2, "2 cheques → 2 líneas de liquidez")
        self.assertEqual(len(wth_ml), 1, "1 línea de retención")
        self.assertEqual(len(wo_line), 1, "1 línea de write-off")
        self.assertEqual(len(cp), 1, "1 contrapartida")
        # 2 liq + 1 wth_tax + 2 base_ret + 1 wo + 1 cp
        self.assertEqual(len(lines), 7)

        self.assertAlmostEqual(sum(lines.mapped("balance")), 0, places=2)

    # ------------------------------------------------------------------
    # TC.9 — 2 cheques USD + IIBB divisa pura (A=B=USD, C=ARS)
    # ------------------------------------------------------------------

    def test_tc9_dos_cheques_usd_con_iibb(self):
        """TC.9 · 2 cheques propios en USD + IIBB 3% (A=B=USD, C=ARS,
        1 USD = 1200 ARS).

        Factura 1 210 USD (1 000 neto). 2 cheques de 580 y 600 USD.

        Verifica (base y amount en C=ARS, UX en B=USD):
        - base_amount = 1 000 * 1200 = 1 200 000 ARS
        - withholding  = 36 000 ARS
        - withholdings_amount = 30 USD
        - 4 líneas: 2 liquidez + 1 retención + 1 contrapartida
        - balance de cada liquidez = amount_currency / accounting_rate
        - sum(balances) == 0
        """
        invoice = self._create_invoice(1_000, self.usd)
        payment = self._create_check_payment_with_wth(
            self.bank_usd,
            invoice,
            [
                {"name": "00000130", "amount": 580},
                {"name": "00000131", "amount": 600},
            ],
        )

        self.assertAlmostEqual(payment.accounting_rate, self._get_rate(self.ars, self.usd), places=6)

        wth = self._wth_line(payment)
        self.assertAlmostEqual(wth.base_amount, 1_200_000, places=0)
        self.assertAlmostEqual(wth.amount, 36_000, places=0)
        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)

        payment.action_post()

        lines = payment.move_id.line_ids
        liq_lines = lines.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        wth_ml = self._wth_move_lines(payment)
        cp = lines.filtered(lambda l: l.account_id == payment.destination_account_id)

        self.assertEqual(len(liq_lines), 2, "2 cheques → 2 líneas de liquidez")
        self.assertEqual(len(wth_ml), 1)
        self.assertEqual(len(cp), 1)
        # 2 liq + 1 wth_tax + 2 base_ret + 1 cp
        self.assertEqual(len(lines), 6)

        # Cada línea de liquidez debe usar accounting_rate del pago (F.2)
        for liq in liq_lines:
            expected_balance = liq.amount_currency / payment.accounting_rate
            self.assertAlmostEqual(
                liq.balance,
                expected_balance,
                places=2,
                msg=f"balance debe usar accounting_rate del pago (F.2). "
                f"amount_currency={liq.amount_currency}, rate={payment.accounting_rate}",
            )

        # A≠C (USD≠ARS) → use_company_currency=True → wth lines siempre en ARS (C)
        self.assertEqual(wth_ml.currency_id, self.ars)
        self.assertAlmostEqual(abs(wth_ml.amount_currency), 36_000, places=0)
        self.assertAlmostEqual(abs(wth_ml.balance), 36_000, places=0)

        self.assertAlmostEqual(sum(lines.mapped("balance")), 0, places=2)
