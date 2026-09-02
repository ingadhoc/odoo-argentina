##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWithholdingSufferedLedger(TransactionCase):
    """El mayor de las retenciones sufridas (cliente nos retiene a nosotros).

    FCP-R05: el asiento del cobro quedaba con una línea de balance
    automático en vez de la línea de retención, y el mayor de la cuenta de
    retención quedaba vacío.

    A diferencia de la retención que nosotros le practicamos a un
    proveedor (``FCP-R01``, en ``test_payment_form_withholding_net.py``),
    la retención sufrida NO se autocompleta:
    ``_compute_l10n_ar_withholding_line_ids`` y ``_compute_base_amount``
    solo corren para ``partner_type == "supplier"``. Para un cobro de
    cliente, la línea de retención (impuesto, base y monto) la carga a
    mano quien cobra — el campo admite escritura directa aunque sea un
    compute (``readonly=False``). Tampoco corre ``_onchange_withholdings``
    (excluido por diseño para pagos de cliente): el neto lo ajusta
    ``_onchange_to_pay_lines_adjust_amount``, que sí aplica a los dos
    tipos de partner y hay que invocar a mano en los tests, igual que su
    par de ``FCP-R01``.

    No cubre ``FCP-R05-E3`` (retención sufrida + cheque de terceros como
    medio de cobro): ese mecanismo es del ciclo de vida del cheque
    (``T17``/``T18``), no de este archivo.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].search(
            [("l10n_ar_tax_base_account_id", "!=", False), ("partner_id.country_id.code", "=", "AR")], limit=1
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.env.user.company_id = cls.company
        if "use_payment_pro" in cls.env["res.company"]._fields:
            cls.company.use_payment_pro = True

        cls.withholding_account = cls.env["account.account"].create(
            {
                "name": "Test Withholding Sufrida Ganancias",
                "code": "TWSG",
                "account_type": "asset_current",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.tax_sufrida = cls.env["account.tax"].create(
            {
                "name": "Test WTH Sufrida Ganancias 6%",
                "company_id": cls.company.id,
                "type_tax_use": "none",
                "amount_type": "percent",
                "amount": 6.0,
                "tax_group_id": cls.env["account.tax.group"]
                .create({"name": "Test Sufrida Ganancias Group", "company_id": cls.company.id})
                .id,
                "l10n_ar_tax_type": "earnings",
                "l10n_ar_withholding_payment_type": "customer",
                "l10n_ar_withholding_sequence_id": cls.env["ir.sequence"]
                .create({"name": "Test WTH Sufrida seq", "implementation": "standard", "padding": 4})
                .id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.withholding_account.id}),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.withholding_account.id}),
                ],
            }
        )

        # segundo régimen (IIBB sufrido), para el caso de dos retenciones juntas (E2)
        cls.iibb_account = cls.env["account.account"].create(
            {
                "name": "Test Withholding Sufrida IIBB",
                "code": "TWSI",
                "account_type": "asset_current",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.tax_iibb_sufrida = cls.env["account.tax"].create(
            {
                "name": "Test WTH Sufrida IIBB 2%",
                "company_id": cls.company.id,
                "type_tax_use": "none",
                "amount_type": "percent",
                "amount": 2.0,
                "tax_group_id": cls.env["account.tax.group"]
                .create({"name": "Test Sufrida IIBB Group", "company_id": cls.company.id})
                .id,
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_withholding_payment_type": "customer",
                "l10n_ar_withholding_sequence_id": cls.env["ir.sequence"]
                .create({"name": "Test WTH Sufrida IIBB seq", "implementation": "standard", "padding": 4})
                .id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.iibb_account.id}),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.iibb_account.id}),
                ],
            }
        )

        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Test Withholding Suffered Customer",
                "company_id": False,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "vat": "30710158261",
            }
        )
        cls.invoice_a = cls.env.ref("l10n_ar.dc_a_f")
        cls.bank_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "bank")], limit=1
        )

        # moneda extranjera, para la base de la retención sufrida al TC del cobro (T04)
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True
        cls.env["res.currency.rate"].create(
            {"currency_id": cls.usd.id, "company_id": cls.company.id, "name": "2026-01-01", "rate": 0.001}
        )
        cls.env["res.currency.rate"].create(
            {"currency_id": cls.usd.id, "company_id": cls.company.id, "name": "2026-02-01", "rate": 1.0 / 1100.0}
        )

        # cuenta y tipo de ajuste, para retención sufrida + write-off en el mismo cobro (T03)
        cls.write_off_account = cls.env["account.account"].create(
            {
                "name": "Test Write-off Sufrida",
                "code": "TWOFS",
                "account_type": "income",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.write_off_type = cls.env["account.write_off.type"].create(
            {"name": "Test Write-off Type Sufrida", "account_id": cls.write_off_account.id}
        )

    def _create_sale_bill(self, amount, document_number):
        income = self.env["account.account"].search(
            [("account_type", "=", "income"), ("company_ids", "=", self.company.id)], limit=1
        )
        bill = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": "2026-01-01",
                "company_id": self.company.id,
                "l10n_latam_document_type_id": self.invoice_a.id,
                "l10n_latam_document_number": document_number,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test suffered withholding bill line",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": income.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        bill.action_post()
        return bill

    def _receive_via_direct_form(self, bill, withholdings=(), unreconciled_amount=0.0):
        """Arma el recibo como lo hace el formulario simple, y carga a mano
        las retenciones sufridas (``tax``, ``base_amount``, ``amount``) —
        acá no hay compute que las adivine, a diferencia de ``FCP-R01``.

        ``_onchange_to_pay_lines_adjust_amount`` (el que ajusta ``amount``
        contra ``to_pay_amount``) es un ``@api.onchange``: en la UI dispara
        solo, y en test hay que invocarlo a mano.
        """
        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.customer.id,
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": "2026-01-01",
                "to_pay_move_line_ids": [Command.set(debt.ids)],
                "unreconciled_amount": unreconciled_amount,
            }
        )
        if withholdings:
            payment.write(
                {
                    "l10n_ar_withholding_line_ids": [
                        Command.create({"tax_id": tax.id, "base_amount": base, "amount": amount})
                        for tax, base, amount in withholdings
                    ]
                }
            )
        payment._onchange_to_pay_lines_adjust_amount()
        return payment

    def test_withholding_suffered_lands_in_its_own_ledger_account(self):
        """Una retención sufrida, y dos juntas, van cada una a su propia
        cuenta — nunca a la de base imponible ni mezcladas entre sí.

        Dada una factura de venta de $100.000 y una retención sufrida de
        Ganancias 6%, cuando se confirma el cobro, entonces el banco entra
        por el neto ($94.000), la cuenta a cobrar se cancela por el total
        ($100.000) y la retención queda en su propia cuenta ($6.000) — no
        hay línea de "balance automático".

        Cubre FCP-R05-E1/E2. Se demuestra en rojo comentando la línea de
        retención en ``_prepare_move_withholding_lines`` (que arma esas
        líneas de asiento): sin ella, el asiento no balancea y Odoo lo
        rechaza en vez de generar una línea correcta a su cuenta.
        """
        with self.subTest("una retención sufrida, en su propia cuenta"):
            bill = self._create_sale_bill(100000.0, "1-1")
            payment = self._receive_via_direct_form(bill, withholdings=[(self.tax_sufrida, 100000.0, 6000.0)])
            self.assertEqual(payment.amount, 94000.0)

            payment.action_post()
            lines = payment.move_id.line_ids
            liquidity = lines.filtered(lambda line: line.account_id == payment.outstanding_account_id)
            withholding_line = lines.filtered(lambda line: line.account_id == self.withholding_account)
            receivable = lines.filtered(lambda line: line.account_id.account_type == "asset_receivable")
            self.assertEqual(liquidity.balance, 94000.0)
            self.assertEqual(withholding_line.balance, 6000.0)
            self.assertEqual(receivable.balance, -100000.0)
            self.assertEqual(self.company.currency_id.round(sum(lines.mapped("balance"))), 0.0)

        with self.subTest("dos retenciones juntas, cada una en su cuenta"):
            bill_two = self._create_sale_bill(100000.0, "1-2")
            payment_two = self._receive_via_direct_form(
                bill_two,
                withholdings=[(self.tax_sufrida, 100000.0, 6000.0), (self.tax_iibb_sufrida, 100000.0, 2000.0)],
            )
            self.assertEqual(payment_two.amount, 92000.0)

            payment_two.action_post()
            lines_two = payment_two.move_id.line_ids
            self.assertEqual(
                lines_two.filtered(lambda line: line.account_id == self.withholding_account).balance, 6000.0
            )
            self.assertEqual(lines_two.filtered(lambda line: line.account_id == self.iibb_account).balance, 2000.0)
            self.assertEqual(self.company.currency_id.round(sum(lines_two.mapped("balance"))), 0.0)

    def test_withholding_suffered_and_write_off_do_not_absorb_each_other(self):
        """Retención sufrida y ajuste manual en el mismo recibo, sin
        pisarse entre sí — tres líneas separadas, ninguna absorbe a otra.

        Dada una factura de $100.000 con retención sufrida de $6.000,
        cuando además se deja un ajuste de $500 sobre el resto, entonces
        el asiento tiene tres líneas independientes: retención $6.000,
        ajuste $500, banco $93.500 — el ajuste no absorbe la retención.

        Cubre FCP-R05-E4.
        """
        bill = self._create_sale_bill(100000.0, "1-6")
        payment = self._receive_via_direct_form(bill, withholdings=[(self.tax_sufrida, 100000.0, 6000.0)])
        self.assertEqual(payment.amount, 94000.0, "neto tras la retención, antes de tocar nada más")

        payment.write_off_type_id = self.write_off_type
        payment.amount = 93500.0
        payment.amount_exact = 93500.0
        payment.action_adjust_writeoff_for_difference()

        with self.subTest("el ajuste es la diferencia real, no la retención completa"):
            self.assertEqual(payment.write_off_amount, 500.0)
            self.assertEqual(payment.payment_difference, 0.0)

        payment.action_post()
        with self.subTest("el asiento: retención 6.000, ajuste 500, banco 93.500, tres líneas separadas"):
            lines = payment.move_id.line_ids
            liquidity = lines.filtered(lambda line: line.account_id == payment.outstanding_account_id)
            withholding_line = lines.filtered(lambda line: line.account_id == self.withholding_account)
            write_off_line = lines.filtered(lambda line: line.account_id == self.write_off_account)
            self.assertEqual(liquidity.balance, 93500.0)
            self.assertEqual(withholding_line.balance, 6000.0)
            self.assertEqual(write_off_line.balance, 500.0)
            self.assertEqual(self.company.currency_id.round(sum(lines.mapped("balance"))), 0.0)

    def test_withholding_suffered_added_and_removed_before_confirming(self):
        """Cargar una retención sufrida y quitarla antes de confirmar no
        deja ni línea huérfana ni error al guardar.

        Cubre FCP-R05-E6. Reproduce el crash histórico de ids virtuales
        (agregar y quitar en la misma edición, sin pasar por la base de
        datos entre medio).
        """
        bill = self._create_sale_bill(100000.0, "1-3")
        payment = self._receive_via_direct_form(bill, withholdings=[(self.tax_sufrida, 100000.0, 6000.0)])
        self.assertEqual(payment.amount, 94000.0, "con la retención cargada, el importe ya está neteado")

        line = payment.l10n_ar_withholding_line_ids
        payment.write({"l10n_ar_withholding_line_ids": [Command.unlink(line.id)]})
        payment._onchange_to_pay_lines_adjust_amount()
        with self.subTest("sin retención, el importe a cobrar vuelve al total"):
            self.assertFalse(payment.l10n_ar_withholding_line_ids)
            self.assertEqual(payment.amount, 100000.0)

        payment.action_post()
        with self.subTest("el asiento no tiene ninguna línea de retención"):
            self.assertFalse(
                payment.move_id.line_ids.filtered(lambda line: line.account_id == self.withholding_account)
            )

    def test_withholding_suffered_base_is_the_amount_actually_collected_on_a_partial_receipt(self):
        """La base de la retención sufrida es lo que efectivamente se
        cobra, no la deuda completa — igual que su par de FCP-R01.

        Dada una factura de $100.000, cuando se cobran $50.000 con una
        retención sufrida cargada sobre esa base ($3.000), entonces el
        banco entra por $47.000 y la factura queda en cobro parcial con
        saldo $50.000.

        Cubre FCP-R05-E8.
        """
        bill = self._create_sale_bill(100000.0, "1-4")
        payment = self._receive_via_direct_form(
            bill, withholdings=[(self.tax_sufrida, 50000.0, 3000.0)], unreconciled_amount=-50000.0
        )
        with self.subTest("el importe a cobrar descuenta la retención sobre lo efectivamente cobrado"):
            self.assertEqual(payment.amount, 47000.0)

        payment.action_post()
        with self.subTest("la factura queda en cobro parcial con saldo 50.000"):
            self.assertEqual(bill.payment_state, "partial")
            self.assertEqual(bill.amount_residual, 50000.0)

    def _fx_lines(self, payment):
        """Líneas de diferencia de cambio: las cuentas de ganancia/pérdida
        por cambio configuradas en la compañía, no un ``account_type``
        fijo (patrón de ``account_payment_pro/tests/test_exchange_difference.py``,
        reutilizado también en ``test_payment_form_withholding_net.py`` para R08-E3)."""
        fx_accounts = (
            self.company.income_currency_exchange_account_id | self.company.expense_currency_exchange_account_id
        )
        return payment.exchange_diff_move_ids.line_ids.filtered(lambda line: line.account_id in fx_accounts)

    def test_withholding_suffered_and_exchange_difference_do_not_cross_on_a_foreign_currency_receipt(self):
        """Retención sufrida y diferencia de cambio en el mismo cobro,
        sobre una factura en moneda extranjera cobrada a otro TC: cada
        mecanismo va a su propia cuenta, sin cruzarse.

        Dada una factura de venta USD 1.000 al TC 1.000 ($1.000.000),
        cuando se cobra con retención sufrida al TC 1.100 (un mes
        después), entonces la base de la retención está en pesos, al TC
        del cobro (**D6**: ARS 1.100.000), la diferencia de cambio
        ($100.000) queda en su propia cuenta separada de la retención, y
        la factura cierra en cero en ambas monedas.

        Cubre FCP-R05-E5/FCP-R07-E8.
        """
        bill = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": "2026-01-01",
                "company_id": self.company.id,
                "currency_id": self.usd.id,
                "l10n_latam_document_type_id": self.invoice_a.id,
                "l10n_latam_document_number": "1-6",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test suffered withholding USD bill line",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.env["account.account"]
                            .search([("account_type", "=", "income"), ("company_ids", "=", self.company.id)], limit=1)
                            .id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        bill.action_post()

        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.customer.id,
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": "2026-02-01",
                "currency_id": self.usd.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
            }
        )
        payment.write(
            {
                "l10n_ar_withholding_line_ids": [
                    Command.create({"tax_id": self.tax_sufrida.id, "base_amount": 1100000.0, "amount": 66000.0})
                ]
            }
        )
        payment._onchange_to_pay_lines_adjust_amount()

        with self.subTest("el importe a cobrar es el neto, en la moneda de la deuda"):
            self.assertEqual(payment.amount, 940.0)

        payment.action_post()
        with self.subTest("la factura cierra en cero en ambas monedas"):
            self.assertEqual(bill.amount_residual, 0.0)
            self.assertEqual(bill.amount_residual_signed, 0.0)

        with self.subTest("la diferencia de cambio queda en su propia cuenta, separada de la retención"):
            fx_lines = self._fx_lines(payment)
            self.assertEqual(fx_lines.balance, -100000.0)

        with self.subTest("la retención en pesos, al TC del cobro, no al de la factura"):
            withholding_line = payment.move_id.line_ids.filtered(
                lambda line: line.account_id == self.withholding_account
            )
            self.assertEqual(withholding_line.balance, 66000.0)

    def test_withholding_suffered_corrected_after_a_draft_and_reconfirm_does_not_duplicate(self):
        """Recibo confirmado, vuelto a borrador, retención corregida, y
        re-confirmado: la retención vieja no queda duplicada.

        Dado un cobro confirmado con una retención sufrida de $6.000,
        cuando se lo vuelve a borrador y se corrige la retención a
        $8.000, entonces al re-confirmar el mayor refleja $8.000 — no
        $14.000 ni dos líneas.

        Cubre FCP-R05-E7.
        """
        bill = self._create_sale_bill(100000.0, "1-5")
        payment = self._receive_via_direct_form(bill, withholdings=[(self.tax_sufrida, 100000.0, 6000.0)])
        payment.action_post()
        self.assertEqual(payment.amount, 94000.0)

        payment.action_draft()
        payment.l10n_ar_withholding_line_ids.amount = 8000.0
        payment._onchange_to_pay_lines_adjust_amount()
        payment.action_post()

        with self.subTest("una sola línea de retención, por el monto corregido"):
            self.assertEqual(len(payment.l10n_ar_withholding_line_ids), 1)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.amount, 8000.0)
            self.assertEqual(payment.amount, 92000.0)

        with self.subTest("el mayor refleja 8.000, no 14.000"):
            withholding_line = payment.move_id.line_ids.filtered(
                lambda line: line.account_id == self.withholding_account
            )
            self.assertEqual(len(withholding_line), 1)
            self.assertEqual(withholding_line.balance, 8000.0)
