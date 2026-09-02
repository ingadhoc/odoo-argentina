##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentFormWithholdingNet(TransactionCase):
    """El neto de la retención en el formulario de pago directo.

    FCP-R01: la retención se calcula bien pero no se resta del importe a
    transferir — el formulario propone el total de la factura en vez del
    neto. El descuento vive en ``_onchange_withholdings``
    (``l10n_ar_tax/models/account_payment.py``), un ``@api.onchange`` que
    en la UI dispara solo, y en tests hay que invocarlo a mano — patrón ya
    usado por ``test_payment_withholding_multimoneda.py`` en este mismo
    módulo. ``l10n_ar_withholding_line_ids`` en cambio es un compute normal
    (``@api.depends``): se completa solo con ``.create()``.

    Reutiliza una compañía AR Responsable Inscripto ya configurada en la
    base (entorno) — ninguna tiene hoy una fiscal position con retenciones
    armada, así que el impuesto, la fiscal position y el proveedor son
    configuración del escenario que crea el test.

    FCP-R01-E3 (wizard de pago múltiple agrupando dos facturas del mismo
    proveedor en un solo pago) **queda sin implementar: es un bug de
    producto encontrado al escribir este test, no pasa hoy en 19.0**.
    Reproducido en shell: sobre dos facturas de $100.000 con retención de
    Ganancias 6%, agrupando con ``group_payment = True`` en
    ``account.payment.register`` (sin agrupar, el wizard crea dos pagos
    separados — uno por factura — que ni siquiera comparan contra el
    formulario directo), el pago resultante sí trae
    ``withholdings_amount = 12.000`` bien calculado, pero
    ``payment.amount`` queda en **$0** y el asiento sale con todas las
    líneas en cero. Causa: la corrección del neto en ``_init_payments``
    (``l10n_ar_tax/wizard/account_payment_register.py``) lee
    ``payment.withholdings_amount`` **antes** de que
    ``l10n_ar_fiscal_position_id`` esté resuelto en el pago — el cómputo
    automático de esa fiscal position (``_compute_fiscal_position_id`` en
    ``l10n_ar_tax/models/account_payment.py``) exige ``state == "draft"``,
    y para el momento en que corre ya no lo está. Con
    ``fiscal_position_mode = "manual"`` en el wizard tampoco se arregla:
    ``_create_payments()`` solo aplica esa fiscal position manual
    **después** de que ``super()._create_payments()`` ya creó y posteó el
    pago — a esa altura ``_init_payments`` ya corrió. Corregirlo queda
    fuera de esta spec (el entregable es la cobertura de test, no el fix
    — ver "Objetivo" de la spec 71623); reportado aparte como bug de
    producto en ``account_payment_pro``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].search(
            [("l10n_ar_tax_base_account_id", "!=", False), ("partner_id.country_id.code", "=", "AR")], limit=1
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
                "type_tax_use": "none",
                "amount_type": "percent",
                "amount": 6.0,
                "tax_group_id": cls.tax_group.id,
                "l10n_ar_tax_type": "earnings",
                "l10n_ar_withholding_payment_type": "supplier",
                "l10n_ar_withholding_sequence_id": cls.env["ir.sequence"]
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
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
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
                "type_tax_use": "none",
                "amount_type": "percent",
                "amount": 2.0,
                "tax_group_id": cls.env["account.tax.group"]
                .create({"name": "Test IIBB Group", "company_id": cls.company.id})
                .id,
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_withholding_payment_type": "supplier",
                "l10n_ar_withholding_sequence_id": cls.env["ir.sequence"]
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
                "type_tax_use": "none",
                "amount_type": "percent",
                "amount": 2.0,
                "tax_group_id": cls.env["account.tax.group"]
                .create({"name": "Test IIBB Minimum Group", "company_id": cls.company.id})
                .id,
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_withholding_payment_type": "supplier",
                "l10n_ar_base_minimum_threshold": 200000.0,
                "l10n_ar_withholding_sequence_id": cls.env["ir.sequence"]
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

    def _pay_via_direct_form(self, bill, fiscal_position=None):
        """Arma el pago como lo hace el formulario simple, seleccionando la
        deuda directamente en ``to_pay_move_line_ids`` — no el wizard de
        pago múltiple, que es el otro camino y calcula distinto.

        ``_onchange_withholdings`` (el que resta la retención del importe)
        es un ``@api.onchange``: en la UI dispara solo; en test se invoca a
        mano, tal como hace ``test_payment_withholding_multimoneda.py``.
        """
        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-01-01",
                "l10n_ar_fiscal_position_id": (fiscal_position or self.fiscal_position).id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
            }
        )
        payment._onchange_withholdings()
        return payment

    def test_direct_form_nets_the_withholding_from_the_transfer_amount(self):
        """Dada una factura de $100.000 con retención de Ganancias 6%,
        cuando se arma el pago desde el formulario directo, entonces el
        importe a transferir es el neto ($94.000), no el total.

        Cubre FCP-R01-E1. Se demuestra en rojo comentando la llamada a
        ``_onchange_withholdings`` en ``_pay_via_direct_form``: sin ella el
        importe queda en $0 en vez de descontar la retención del total.
        """
        bill = self._create_bill(100000.0, "1-1")
        payment = self._pay_via_direct_form(bill)

        with self.subTest("la retención calculada es la esperada"):
            self.assertEqual(len(payment.l10n_ar_withholding_line_ids), 1)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.tax_id, self.tax_wth)
            self.assertEqual(payment.withholdings_amount, 6000.0)

        with self.subTest("el importe a transferir es el neto, no el total"):
            self.assertEqual(payment.amount, 94000.0)

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
        fiscal position — orden invertido de los mismos dos campos.

        Cubre FCP-R01-E2: nadie repite el mismo pago cambiando el orden de
        los clicks a propósito, y es justo el disparador histórico del bug.
        """
        bill_1 = self._create_bill(100000.0, "1-2")
        debt_1 = bill_1.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment_debt_first = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-01-01",
                "to_pay_move_line_ids": [Command.set(debt_1.ids)],
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
            }
        )
        payment_debt_first._onchange_withholdings()

        bill_2 = self._create_bill(100000.0, "1-3")
        debt_2 = bill_2.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment_fp_first = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-01-01",
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [Command.set(debt_2.ids)],
            }
        )
        payment_fp_first._onchange_withholdings()

        self.assertEqual(payment_debt_first.amount, payment_fp_first.amount)
        self.assertEqual(payment_debt_first.amount, 94000.0)

    def test_two_withholdings_together_and_one_that_resolves_to_zero(self):
        """Dos regímenes en el mismo pago, y una retención bajo el mínimo
        no imponible.

        Dada una factura de $100.000 con Ganancias 6% e IIBB 2% juntos,
        cuando se arma el pago, entonces el neto es $92.000 y cada retención
        cae en su propia cuenta — ninguna en la base imponible ni en el
        banco. Dada otra factura con una retención IIBB cuya base mínima no
        imponible ($200.000) supera la base de la factura ($100.000),
        cuando se posea el pago, entonces esa retención no deja línea y el
        importe transferido es el total, no el neto.

        Cubre FCP-R01-E4/E9. La retención en cero se demuestra en rojo
        comprobando que la línea existe (importe $0) antes de postear, y
        que ``action_post`` es quien la elimina
        (``_l10n_ar_remove_zero_withholding_lines``, distinto de earnings,
        que se conserva siempre) — si esa limpieza no corriera, la línea en
        cero quedaría ensuciando el pago.
        """
        with self.subTest("dos regímenes juntos: cada retención en su cuenta, neto $92.000"):
            bill = self._create_bill(100000.0, "1-4")
            payment = self._pay_via_direct_form(bill, fiscal_position=self.fiscal_position_two_taxes)

            self.assertEqual(len(payment.l10n_ar_withholding_line_ids), 2)
            self.assertEqual(payment.withholdings_amount, 8000.0)
            self.assertEqual(payment.amount, 92000.0)

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
                payment_below_min.l10n_ar_withholding_line_ids.amount,
                0.0,
                "antes de postear la línea existe, con importe en cero",
            )
            self.assertEqual(payment_below_min.amount, 100000.0, "no hay nada que restar: se transfiere el total")

            payment_below_min.action_post()
            self.assertFalse(
                payment_below_min.l10n_ar_withholding_line_ids,
                "al postear, la retención en cero no earnings se elimina y no ensucia el pago",
            )

    def test_withholding_and_write_off_do_not_absorb_each_other(self):
        """Retención y ajuste manual en el mismo pago, sin pisarse.

        Dada una factura de $100.000 con retención de Ganancias 6%
        ($6.000), cuando el usuario además reduce el importe a transferir
        a $93.000 y ajusta la diferencia con un write-off, entonces el
        ajuste es de $1.000 — no de $7.000: no absorbe la retención.

        Cubre FCP-R01-E5. Dos mecanismos que se pisan: a mano el error se
        ve como "un número raro" y se recalcula a ojo en vez de
        reportarse. Se demuestra en rojo asertando que el ajuste NO es
        igual a la retención más la diferencia real ($7.000) — si el
        ajuste absorbiera la retención, este test lo agarra.
        """
        bill = self._create_bill(100000.0, "1-6")
        payment = self._pay_via_direct_form(bill)
        self.assertEqual(payment.amount, 94000.0, "neto tras la retención, antes de tocar nada más")

        payment.write_off_type_id = self.write_off_type
        payment.amount = 93000.0
        payment.amount_exact = 93000.0
        payment.action_adjust_writeoff_for_difference()

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
        los $50.000 pagados ($3.000) — no sobre el total — y se transfieren
        $47.000, dejando la factura en pago parcial con saldo $50.000.

        Cubre FCP-R01-E6. Verifica que la base no se recalcule en cascada
        contra el total de la deuda al ajustar el neto.
        """
        bill = self._create_bill(100000.0, "1-7")
        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-01-01",
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
                # unreconciled_amount es el "adelanto/ajuste" respecto a la deuda
                # seleccionada; negativo = se paga menos que la deuda ($100.000 - $50.000).
                # to_pay_amount se recomputa solo a partir de esto (selected_debt + unreconciled_amount).
                "unreconciled_amount": -50000.0,
            }
        )
        payment._onchange_withholdings()

        with self.subTest("la base de la retención es lo pagado, no el total de la deuda"):
            self.assertEqual(payment.l10n_ar_withholding_line_ids.base_amount, 50000.0)
            self.assertEqual(payment.withholdings_amount, 3000.0)

        with self.subTest("se transfieren 47.000, no 94.000"):
            self.assertEqual(payment.amount, 47000.0)

        payment.action_post()
        with self.subTest("la factura queda en pago parcial con saldo 50.000"):
            self.assertEqual(bill.payment_state, "partial")
            self.assertEqual(bill.amount_residual, 50000.0)

    def test_withholding_survives_a_draft_and_reconfirm_cycle_without_duplicating(self):
        """Pago con retenciones vuelto a borrador y re-confirmado sin
        cambios: las líneas se conservan, y el neto no se duplica ni se
        recalcula de más.

        Cubre FCP-R09-E2. El bug es la duplicación del neto: solo se ve
        comparando el importe antes y después del ciclo completo.
        """
        bill = self._create_bill(100000.0, "1-9")
        payment = self._pay_via_direct_form(bill)
        payment.action_post()
        self.assertEqual(payment.amount, 94000.0)

        payment.action_draft()
        payment.action_post()

        with self.subTest("una sola línea de retención, importe sin duplicar"):
            self.assertEqual(len(payment.l10n_ar_withholding_line_ids), 1)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.amount, 6000.0)
            self.assertEqual(payment.amount, 94000.0)

    def test_withholding_base_on_a_foreign_currency_bill_is_converted_to_pesos(self):
        """La base de la retención es siempre en pesos, aunque la factura
        esté en moneda extranjera.

        Dada una factura de USD 1.000 (cotización 1 USD = ARS 1.000, pagada
        con un diario en ARS), cuando se arma el pago, entonces la base de
        la retención es ARS 1.000.000 (no USD 1.000) y la retención de
        Ganancias 6% es ARS 60.000 — mostrada también en USD (60), la
        moneda de la deuda, en el campo que resume la retención en el
        pago. El importe a transferir descuenta esa retención en ambas
        monedas: ARS 940.000 (moneda del diario) y USD 60 (moneda de la
        deuda).

        Cubre FCP-R01-E7. Se demuestra en rojo forzando
        ``base_amount = payment.selected_debt_untaxed`` (sin la conversión
        de ``_get_withholding_rate``): la retención saldría en USD 60 en
        vez de ARS 60.000, mil veces menor.
        """
        bill = self._create_bill(1000.0, "1-8", currency=self.usd)
        payment = self._pay_via_direct_form(bill)

        with self.subTest("la base de la retención está en pesos, convertida a la cotización de la factura"):
            self.assertEqual(payment.l10n_ar_withholding_line_ids.currency_id, self.company.currency_id)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.base_amount, 1000000.0)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.amount, 60000.0)

        with self.subTest(
            "el importe a transferir ya descuenta la retención, tanto en ARS como en la moneda de la factura"
        ):
            self.assertEqual(payment.withholdings_amount, 60.0, "retención expresada en USD, la moneda de la deuda")
            self.assertEqual(payment.amount, 940000.0, "importe en ARS, la moneda del diario: neto de la retención")

    def _fx_lines(self, payment):
        """Líneas de diferencia de cambio: no se identifican por un
        ``account_type`` fijo, sino por ser las cuentas de ganancia/pérdida
        por cambio configuradas en la compañía (patrón de
        ``account_payment_pro/tests/test_exchange_difference.py``)."""
        fx_accounts = (
            self.company.income_currency_exchange_account_id | self.company.expense_currency_exchange_account_id
        )
        return payment.exchange_diff_move_ids.line_ids.filtered(lambda line: line.account_id in fx_accounts)

    def test_withholding_and_exchange_difference_do_not_cross_on_a_foreign_currency_payment(self):
        """Retención y diferencia de cambio en el mismo pago, sobre una
        factura en moneda extranjera pagada a otro TC: cada mecanismo va
        a su propia cuenta y ninguno deja saldo a favor indebido.

        Dada una factura de compra USD 1.000 al TC 1.000 ($1.000.000),
        cuando se paga con retención de Ganancias 6% al TC 1.100 (un mes
        después), entonces la base de la retención se convierte al TC del
        pago (**D6**: ARS 1.100.000, no al TC de la factura), la
        diferencia de cambio ($100.000) queda en su propia cuenta,
        separada de la retención, y el mayor del proveedor cierra en
        cero — ni la retención ni la diferencia dejan saldo a favor.

        Cubre FCP-R08-E3.
        """
        bill = self._create_bill(1000.0, "1-11", currency=self.usd)
        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-02-01",
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
            }
        )
        payment._onchange_withholdings()

        with self.subTest("la base de la retención se convierte al TC del pago, no al de la factura"):
            self.assertEqual(payment.l10n_ar_withholding_line_ids.base_amount, 1100000.0)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.amount, 66000.0)

        with self.subTest("el importe a transferir es el neto, en pesos, al TC del pago"):
            self.assertEqual(payment.amount, 1034000.0)

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
        """Un pago a proveedor sin ninguna factura seleccionada (a cuenta) puede
        llevar retención igual: la base es el importe que el usuario carga a mano
        (``to_pay_amount``, vía ``unreconciled_amount`` al no haber deuda), no cero.

        Cubre FCP-R01-E8 (D7). Se demuestra en rojo: si la base dependiera solo de
        ``selected_debt`` (0 sin factura), la retención saldría en $0 en vez de
        $6.000 — revertir la resta de ``advance_amount`` en
        ``l10n_ar_payment_withholding.py`` reproduce justo eso.
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
        payment._onchange_withholdings()

        with self.subTest("la retención se permite sin deuda, sobre el importe cargado a mano"):
            self.assertEqual(payment.to_pay_amount, 100000.0)
            self.assertEqual(payment.l10n_ar_withholding_line_ids.base_amount, 100000.0)
            self.assertEqual(payment.withholdings_amount, 6000.0)

        with self.subTest("el importe a transferir descuenta esa retención"):
            self.assertEqual(payment.amount, 94000.0)
