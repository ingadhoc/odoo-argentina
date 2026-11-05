##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentFormWithholdingNet(TransactionCase):
    """El neto de la retención en el formulario de pago directo.

    FCP-R01: la retención se calcula bien pero no se resta del importe a
    transferir. Desde 20.0 el importe del pago (``amount``) es el bruto, como
    en Odoo, y lo que sale del banco es el neto (``withholding_net_amount``):
    los tests miran el neto ahí. El pago se arma con ``Form`` y el contexto de
    registrar pago, que es el formulario directo con la deuda seleccionada.

    Reutiliza una compañía AR Responsable Inscripto ya configurada en la
    base (entorno): el impuesto, la fiscal position y el proveedor son
    configuración del escenario que crea el test.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].search(
            [("withholding_tax_base_account_id", "!=", False), ("partner_id.country_id.code", "=", "AR")], limit=1
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.env.user.company_id = cls.company

        cls.tax_group = cls.env["account.tax.group"].create(
            {"name": "Test Withholding Group", "company_id": cls.company.id}
        )
        cls.withholding_account = cls.env["account.account"].create(
            {
                "name": "Test Withholding Ganancias",
                "code": "TWHG",
                "account_type": "liability_current",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.tax_wth = cls.env["account.tax"].create(
            {
                "name": "Test WTH Ganancias 6%",
                "company_id": cls.company.id,
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "l10n_ar_code": "TEST",
                "amount_type": "percent",
                "amount": -6.0,
                "tax_group_id": cls.tax_group.id,
                "l10n_ar_withholding_tax_type": "earnings",
                "withholding_sequence_id": cls.env["ir.sequence"]
                .create({"name": "Test WTH Ganancias seq", "implementation": "standard", "padding": 4})
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
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Test FP Ganancias",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [Command.create({"default_tax_id": cls.tax_wth.id, "tax_type": "withholding"})],
            }
        )
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Test Withholding Vendor",
                "company_id": False,
                "property_account_position_id": cls.fiscal_position.id,
                "country_id": cls.env.ref("base.ar").id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "vat": "30710158254",
            }
        )
        cls.invoice_a = cls.env.ref("l10n_ar.dc_a_f")
        if "use_payment_pro" in cls.env["res.company"]._fields:
            cls.company.use_payment_pro = True
        cls.bank_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "bank")], limit=1
        )

        # segundo régimen (IIBB), para la fiscal position con dos retenciones juntas
        cls.iibb_account = cls.env["account.account"].create(
            {
                "name": "Test Withholding IIBB",
                "code": "TWHI",
                "account_type": "liability_current",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.tax_iibb = cls.env["account.tax"].create(
            {
                "name": "Test WTH IIBB 2%",
                "company_id": cls.company.id,
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "amount_type": "percent",
                "amount": -2.0,
                "tax_group_id": cls.env["account.tax.group"]
                .create({"name": "Test IIBB Group", "company_id": cls.company.id})
                .id,
                "l10n_ar_withholding_tax_type": "iibb_untaxed",
                "withholding_sequence_id": cls.env["ir.sequence"]
                .create({"name": "Test WTH IIBB seq", "implementation": "standard", "padding": 4})
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
        cls.fiscal_position_two_taxes = cls.env["account.fiscal.position"].create(
            {
                "name": "Test FP Ganancias + IIBB",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": cls.tax_wth.id, "tax_type": "withholding"}),
                    Command.create({"default_tax_id": cls.tax_iibb.id, "tax_type": "withholding"}),
                ],
            }
        )

        # tercer régimen (IIBB con mínimo no imponible sobre la base), para la
        # retención que tiene que resolver en cero y no dejar línea
        cls.tax_iibb_with_minimum = cls.env["account.tax"].create(
            {
                "name": "Test WTH IIBB 2% con mínimo",
                "company_id": cls.company.id,
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "amount_type": "percent",
                "amount": -2.0,
                "tax_group_id": cls.env["account.tax.group"]
                .create({"name": "Test IIBB Minimum Group", "company_id": cls.company.id})
                .id,
                "l10n_ar_withholding_tax_type": "iibb_untaxed",
                "l10n_ar_base_minimum_threshold": 200000.0,
                "withholding_sequence_id": cls.env["ir.sequence"]
                .create({"name": "Test WTH IIBB minimum seq", "implementation": "standard", "padding": 4})
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
        cls.fiscal_position_below_minimum = cls.env["account.fiscal.position"].create(
            {
                "name": "Test FP IIBB bajo mínimo",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": cls.tax_iibb_with_minimum.id, "tax_type": "withholding"})
                ],
            }
        )

        # cuenta y tipo de ajuste, para retención + write-off en la misma operación (T03)
        cls.write_off_account = cls.env["account.account"].create(
            {
                "name": "Test Write-off",
                "code": "TWOF",
                "account_type": "expense",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.write_off_type = cls.env["account.write_off.type"].create(
            {"name": "Test Write-off Type", "account_id": cls.write_off_account.id}
        )

        # moneda extranjera, para la base de la retención en factura en USD (T04)
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True
        cls.env["res.currency.rate"].create(
            {"currency_id": cls.usd.id, "company_id": cls.company.id, "name": "2026-01-01", "rate": 0.001}
        )
        # segunda cotización, para pagar a un TC distinto del de la factura (R08-E3)
        cls.env["res.currency.rate"].create(
            {"currency_id": cls.usd.id, "company_id": cls.company.id, "name": "2026-02-01", "rate": 1.0 / 1100.0}
        )

    def _create_bill(self, amount, document_number, currency=None):
        expense = self.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "=", self.company.id)], limit=1
        )
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-01-01",
                "company_id": self.company.id,
                "currency_id": (currency or self.company.currency_id).id,
                "l10n_latam_document_type_id": self.invoice_a.id,
                "l10n_latam_document_number": document_number,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test withholding bill line",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": expense.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        bill.action_post()
        return bill

    def _pay_via_direct_form(self, bill, fiscal_position=None, date="2026-01-01", to_pay_amount=None, net=None):
        """Arma el pago como lo hace el formulario directo, con la deuda de la
        factura seleccionada. Con ``to_pay_amount`` se paga parcial, y con
        ``net`` el usuario tipea el neto a transferir."""
        # the payment is born on its date, as when the user registers it that day
        context = dict(bill.line_ids.action_register_payment()["context"], default_date=date)
        with Form(self.env["account.payment"].with_context(**context)) as form:
            form.journal_id = self.bank_journal
            form.l10n_ar_fiscal_position_id = fiscal_position or self.fiscal_position
            if to_pay_amount is not None:
                form.to_pay_amount = to_pay_amount
            if net is not None:
                form.withholding_net_amount = net
        return form.record

    def test_direct_form_nets_the_withholding_from_the_transfer_amount(self):
        """Dada una factura de $100.000 con retención de Ganancias 6%,
        cuando se arma el pago desde el formulario directo, entonces el
        neto a transferir es $94.000 y el bruto del pago, $100.000.

        Cubre FCP-R01-E1.
        """
        bill = self._create_bill(100000.0, "1-1")
        payment = self._pay_via_direct_form(bill)

        with self.subTest("la retención calculada es la esperada"):
            self.assertEqual(len(payment.withholding_line_ids), 1)
            self.assertEqual(payment.withholding_line_ids.tax_id, self.tax_wth)
            self.assertEqual(payment.withholding_amount, 6000.0)

        with self.subTest("el neto a transferir descuenta la retención del total"):
            self.assertEqual(payment.withholding_net_amount, 94000.0)
            self.assertEqual(payment.amount, 100000.0)

        payment.action_post()
        with self.subTest("el asiento: banco 94.000, retención 6.000, proveedor 100.000, sin línea de balance"):
            lines = payment.move_id.line_ids
            liquidity = lines.filtered(lambda line: line.account_id == payment.outstanding_account_id)
            withholding_line = lines.filtered(lambda line: line.account_id == self.withholding_account)
            payable = lines.filtered(lambda line: line.account_id.account_type == "liability_payable")
            self.assertEqual(liquidity.balance, -94000.0)
            self.assertEqual(withholding_line.balance, -6000.0)
            self.assertEqual(payable.balance, 100000.0)
            self.assertEqual(self.company.currency_id.round(sum(lines.mapped("balance"))), 0.0)

    def test_direct_form_net_is_the_same_regardless_of_load_order(self):
        """El neto no depende de si se carga primero la deuda o primero la
        fiscal position.

        Cubre FCP-R01-E2: es el disparador histórico del bug.
        """
        payment_debt_first = self._pay_via_direct_form(self._create_bill(100000.0, "1-2"))

        bill_2 = self._create_bill(100000.0, "1-3")
        context = bill_2.line_ids.with_context(
            default_l10n_ar_fiscal_position_id=self.fiscal_position.id
        ).action_register_payment()["context"]
        with Form(self.env["account.payment"].with_context(**context)) as form:
            form.journal_id = self.bank_journal
            form.date = "2026-01-01"
        payment_fp_first = form.record

        self.assertEqual(payment_fp_first.l10n_ar_fiscal_position_id, self.fiscal_position)
        self.assertEqual(payment_debt_first.withholding_net_amount, payment_fp_first.withholding_net_amount)
        self.assertEqual(payment_debt_first.withholding_net_amount, 94000.0)

    def test_two_withholdings_together_and_one_that_resolves_to_zero(self):
        """Dos regímenes en el mismo pago, y una retención bajo el mínimo
        no imponible.

        Dada una factura de $100.000 con Ganancias 6% e IIBB 2% juntos,
        cuando se arma el pago, entonces el neto es $92.000 y cada retención
        cae en su propia cuenta. Dada otra factura con una retención IIBB
        cuya base mínima ($200.000) supera la base de la factura, entonces
        esa retención no deja línea al postear y se transfiere el total.

        Cubre FCP-R01-E4/E9. La línea existe en cero antes de postear, y la
        borra ``action_post`` (``_l10n_ar_remove_zero_withholding_lines``,
        salvo ganancias, que se conserva).
        """
        with self.subTest("dos regímenes juntos: cada retención en su cuenta, neto $92.000"):
            bill = self._create_bill(100000.0, "1-4")
            payment = self._pay_via_direct_form(bill, fiscal_position=self.fiscal_position_two_taxes)

            self.assertEqual(len(payment.withholding_line_ids), 2)
            self.assertEqual(payment.withholding_amount, 8000.0)
            self.assertEqual(payment.withholding_net_amount, 92000.0)

            payment.action_post()
            lines = payment.move_id.line_ids
            self.assertEqual(lines.filtered(lambda line: line.account_id == self.withholding_account).balance, -6000.0)
            self.assertEqual(lines.filtered(lambda line: line.account_id == self.iibb_account).balance, -2000.0)
            self.assertEqual(
                lines.filtered(lambda line: line.account_id.account_type == "liability_payable").balance, 100000.0
            )
            self.assertEqual(self.company.currency_id.round(sum(lines.mapped("balance"))), 0.0)

        with self.subTest("retención bajo el mínimo no imponible: no deja línea, se transfiere el total"):
            bill_below_min = self._create_bill(100000.0, "1-5")
            payment_below_min = self._pay_via_direct_form(
                bill_below_min, fiscal_position=self.fiscal_position_below_minimum
            )

            self.assertEqual(
                payment_below_min.withholding_line_ids.amount,
                0.0,
                "antes de postear la línea existe, con importe en cero",
            )
            self.assertEqual(
                payment_below_min.withholding_net_amount, 100000.0, "no hay nada que restar: se transfiere el total"
            )

            payment_below_min.action_post()
            self.assertFalse(
                payment_below_min.withholding_line_ids,
                "al postear, la retención en cero no earnings se elimina y no ensucia el pago",
            )

    def test_withholding_and_write_off_do_not_absorb_each_other(self):
        """Retención y ajuste manual en el mismo pago, sin pisarse.

        Dada una factura de $100.000 con retención de Ganancias 6%
        ($6.000), cuando el usuario transfiere $93.000 y ajusta la
        diferencia con un write-off, entonces el ajuste es de $1.000, no de
        $7.000: no absorbe la retención.

        Cubre FCP-R01-E5.
        """
        bill = self._create_bill(100000.0, "1-6")
        payment = self._pay_via_direct_form(bill)
        self.assertEqual(payment.withholding_net_amount, 94000.0, "neto tras la retención, antes de tocar nada más")

        with Form(payment) as form:
            form.withholding_net_amount = 93000.0
        payment.action_adjust_writeoff_for_difference()
        payment.write_off_type_id = self.write_off_type

        with self.subTest("el ajuste es la diferencia real, no la retención completa"):
            self.assertEqual(payment.write_off_amount, 1000.0)
            self.assertEqual(payment.payment_difference, 0.0)

        payment.action_post()
        with self.subTest("el asiento: banco 93.000, retención 6.000, ajuste 1.000, proveedor 100.000"):
            lines = payment.move_id.line_ids
            liquidity = lines.filtered(lambda line: line.account_id == payment.outstanding_account_id)
            withholding_line = lines.filtered(lambda line: line.account_id == self.withholding_account)
            write_off_line = lines.filtered(lambda line: line.account_id == self.write_off_account)
            payable = lines.filtered(lambda line: line.account_id.account_type == "liability_payable")
            self.assertEqual(liquidity.balance, -93000.0)
            self.assertEqual(withholding_line.balance, -6000.0)
            self.assertEqual(write_off_line.balance, -1000.0)
            self.assertEqual(payable.balance, 100000.0)
            self.assertEqual(self.company.currency_id.round(sum(lines.mapped("balance"))), 0.0)

    def test_withholding_base_is_the_amount_actually_paid_on_a_partial_payment(self):
        """La base de la retención es lo que se paga, no la deuda completa.

        Dada una factura de $100.000, cuando se paga solo $50.000 con
        retención de Ganancias 6%, entonces la retención se calcula sobre
        los $50.000 ($3.000), se transfieren $47.000 y la factura queda en
        pago parcial con saldo $50.000.

        Cubre FCP-R01-E6. Desde 20.0 lo que se paga no mueve el importe del
        pago: el usuario tipea el neto.
        """
        bill = self._create_bill(100000.0, "1-7")
        payment = self._pay_via_direct_form(bill, to_pay_amount=50000.0, net=47000.0)

        with self.subTest("la base de la retención es lo pagado, no el total de la deuda"):
            self.assertEqual(payment.withholding_line_ids.base_amount, 50000.0)
            self.assertEqual(payment.withholding_amount, 3000.0)

        with self.subTest("el bruto del pago es lo pagado: el neto más la retención"):
            self.assertEqual(payment.amount, 50000.0)

        payment.action_post()
        with self.subTest("la factura queda en pago parcial con saldo 50.000"):
            self.assertEqual(bill.payment_state, "partial")
            self.assertEqual(bill.amount_residual, 50000.0)

    def test_withholding_survives_a_draft_and_reconfirm_cycle_without_duplicating(self):
        """Pago con retenciones vuelto a borrador y re-confirmado sin
        cambios: las líneas se conservan, y el neto no se duplica.

        Cubre FCP-R09-E2.
        """
        bill = self._create_bill(100000.0, "1-9")
        payment = self._pay_via_direct_form(bill)
        payment.action_post()
        self.assertEqual(payment.withholding_net_amount, 94000.0)

        payment.action_draft()
        payment.action_post()

        with self.subTest("una sola línea de retención, importe sin duplicar"):
            self.assertEqual(len(payment.withholding_line_ids), 1)
            self.assertEqual(payment.withholding_line_ids.amount, 6000.0)
            self.assertEqual(payment.withholding_net_amount, 94000.0)
            self.assertEqual(payment.amount, 100000.0)

    def test_withholding_base_on_a_foreign_currency_bill_is_converted_to_pesos(self):
        """La base de la retención es siempre en pesos, aunque la factura
        esté en moneda extranjera.

        Dada una factura de USD 1.000 (1 USD = ARS 1.000) pagada con un
        diario en ARS, entonces la base es ARS 1.000.000 y la retención de
        Ganancias 6%, ARS 60.000. Se transfieren ARS 940.000, que cancelan
        USD 940 netos de la deuda.

        Cubre FCP-R01-E7. La spec de payment pro pide además ver la
        retención en la moneda de la deuda (USD 60): en 20.0 el total de
        retenciones está en la moneda del pago, y eso no se prueba acá.
        """
        bill = self._create_bill(1000.0, "1-8", currency=self.usd)
        payment = self._pay_via_direct_form(bill)

        with self.subTest("la base de la retención está en pesos"):
            self.assertEqual(payment.withholding_line_ids.comodel_currency_id, self.company.currency_id)
            self.assertEqual(payment.withholding_line_ids.base_amount, 1000000.0)
            self.assertEqual(payment.withholding_line_ids.amount, 60000.0)

        with self.subTest("el neto descuenta la retención, en ARS y en la moneda de la deuda"):
            self.assertEqual(payment.withholding_net_amount, 940000.0)
            self.assertAlmostEqual(payment.counterpart_currency_net_amount, 940.0, places=2)

    def _fx_lines(self, payment):
        """Líneas de diferencia de cambio: las de las cuentas de ganancia/pérdida
        por cambio configuradas en la compañía."""
        fx_accounts = (
            self.company.income_currency_exchange_account_id | self.company.expense_currency_exchange_account_id
        )
        return payment.exchange_diff_move_ids.line_ids.filtered(lambda line: line.account_id in fx_accounts)

    def test_withholding_and_exchange_difference_do_not_cross_on_a_foreign_currency_payment(self):
        """Retención y diferencia de cambio en el mismo pago, sobre una
        factura en moneda extranjera pagada a otro TC: cada mecanismo va
        a su propia cuenta y ninguno deja saldo a favor indebido.

        Dada una factura de USD 1.000 al TC 1.000, cuando se paga con
        retención de Ganancias 6% al TC 1.100, entonces la base se convierte
        al TC del pago (D6: ARS 1.100.000), la diferencia de cambio
        ($100.000) queda en su propia cuenta y el mayor del proveedor cierra
        en cero.

        Cubre FCP-R08-E3.
        """
        bill = self._create_bill(1000.0, "1-11", currency=self.usd)
        # since 20.0 a rate applies from the day after its date. The form proposes the debt at the rate of the bill,
        # so the user types the net amount at the rate of the payment
        payment = self._pay_via_direct_form(bill, date="2026-02-02", net=1034000.0)

        with self.subTest("la base de la retención se convierte al TC del pago, no al de la factura"):
            self.assertEqual(payment.withholding_line_ids.base_amount, 1100000.0)
            self.assertEqual(payment.withholding_line_ids.amount, 66000.0)

        with self.subTest("el neto a transferir, en pesos, al TC del pago"):
            self.assertEqual(payment.withholding_net_amount, 1034000.0)

        payment.action_post()
        with self.subTest("la factura queda saldada, sin residuo en ninguna moneda"):
            self.assertEqual(bill.amount_residual, 0.0)
            self.assertEqual(bill.amount_residual_signed, 0.0)

        with self.subTest("la diferencia de cambio queda en su propia cuenta, separada de la retención"):
            fx_lines = self._fx_lines(payment)
            self.assertEqual(fx_lines.balance, 100000.0)

        with self.subTest("el mayor del proveedor cierra en cero: sin saldo a favor por retención ni por FX"):
            payable_lines = (
                bill.line_ids | payment.move_id.line_ids | payment.exchange_diff_move_ids.line_ids
            ).filtered(lambda line: line.account_id.account_type == "liability_payable")
            self.assertEqual(sum(payable_lines.mapped("balance")), 0.0)

    def test_withholding_without_any_debt_selected_uses_the_amount_the_user_loads_as_base(self):
        """Un pago a proveedor sin ninguna factura seleccionada (a cuenta)
        puede llevar retención: la base es el importe que el usuario carga
        (``to_pay_amount``, vía ``unreconciled_amount``), no cero.

        Cubre FCP-R01-E8 (D7).
        """
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-01-01",
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [Command.clear()],
                "unreconciled_amount": 100000.0,
            }
        )

        with self.subTest("la retención se permite sin deuda, sobre el importe cargado a mano"):
            self.assertEqual(payment.to_pay_amount, 100000.0)
            self.assertEqual(payment.withholding_line_ids.base_amount, 100000.0)
            self.assertEqual(payment.withholding_amount, 6000.0)

        with Form(payment) as form:
            form.withholding_net_amount = 94000.0
        with self.subTest("con el neto tipeado, el bruto es el importe cargado"):
            self.assertEqual(payment.amount, 100000.0)
