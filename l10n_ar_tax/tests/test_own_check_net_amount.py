from odoo import Command
from odoo.addons.account_ux.tests.invariants import AccountInvariantsMixin
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOwnCheckNetAmount(AccountInvariantsMixin, TransactionCase):
    """D1: en un pago con cheque propio y retención, el importe del cheque es
    el neto (deuda − retenciones) — es lo que la OP precalcula hoy.

    FCP-R10: la OP dejaba pasar un cheque cargado por el total de la factura
    (bruto) habiendo retención, y el proveedor quedaba con un saldo a favor
    que nadie pedía. FCP-R10-E1/E3/E5/E6 (el neto en sus variantes de moneda,
    N cheques y write-off) están cubiertos en
    ``test_payment_withholding_checks_multimoneda`` (TC.6/TC.7/TC.9/TC.8).

    FCP-R10-E2 (cheque cargado por el bruto) sigue **sin implementar**, y la
    razón cambió de piso el 2026-09-01. La spec reabrió D1 "verificado leyendo
    el código" y concluyó que el wizard no bloquea y recalcula en silencio al
    neto. Repetí la lectura y además lo corrí en ``all_v19`` (ver detalle de
    la corrida en el reporte de la tarea 71623) y encontré un tercer resultado
    que no es ninguno de los dos que se venían discutiendo:

    - Por el wizard (``account.payment.register`` con ``fiscal_position_mode
      = 'manual'``): no bloquea, pero la retención persistida
      (``l10n_ar_withholding_line_ids``) queda en **0** y ``payment.amount``
      termina igual al cheque cargado (bruto) — la retención calculada en el
      wizard nunca se traslada al pago creado.
    - Por el camino directo (``account.payment.create()`` +
      ``_onchange_withholdings()``, el que usan **todos** los tests ya verdes
      de este módulo, TC.6 incluido): tampoco bloquea, pero el asiento que
      postea es ``AP 1.060 = cheque 1.000 + retención 60`` para una deuda de
      **1.000** — el cheque se contabiliza por el bruto en la línea de
      liquidez, la retención se practica *además*, y el proveedor queda con
      **60 de saldo a favor**. Es exactamente lo que D1 dice que nunca tiene
      que pasar, reproducido con el código de hoy, no el del 27/08.

    Ninguno de los dos caminos hace lo que D1 (re-verificada) describe
    ("se recalcula al neto"): en el primero la retención desaparece: en el
    segundo el saldo a favor aparece. No fijo ninguno de los dos con un test
    en verde porque blindaría un bug con un test que lo defiende — es la
    misma pregunta de producto que ya estaba abierta con gl, con un hallazgo
    nuevo y más preciso para llevarle. Repro con datos y line-by-line del
    asiento en el reporte de esta corrida.

    No hereda de ``TestArCommon``/``AccountTestInvoicingCommon``: esa base
    crea su propia compañía y choca con el ACL de productos en bases
    full-OBA (ver ``reference_v18_tests_transactioncase``). En su lugar,
    reutiliza una compañía AR ya configurada, igual que
    ``test_reset_and_recompute_rate.py`` en ``account_payment_pro``.

    Mixea ``AccountInvariantsMixin`` (``account_ux``, transitivo vía
    ``account_payment_pro``) para la batería de invariantes de cobros/pagos.

    Cubre FCP-R10-E4, FCP-R08-E4.
    Tickets 114272, 122219, 118579, 119844.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].search(
            [("l10n_ar_tax_base_account_id", "!=", False), ("partner_id.country_id.code", "=", "AR")], limit=1
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.env.user.company_id = cls.company
        cls.company.use_payment_pro = True

        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Test Own Check Net Amount Vendor",
                "company_id": False,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "vat": "30710158292",
            }
        )
        cls.invoice_doc_type = cls.env.ref("l10n_ar.dc_a_f")
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "=", cls.company.id)], limit=1
        )

        # Retención de Ganancias 6% a proveedores, configuración del escenario.
        tax_group = cls.env["account.tax.group"].create(
            {"name": "Test Own Check Net Amount WTH Group", "company_id": cls.company.id}
        )
        wth_account = cls.env["account.account"].create(
            {
                "name": "Test Own Check Net Amount WTH",
                "code": "TOCNAWTH",
                "account_type": "liability_current",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )
        cls.tax_wth = cls.env["account.tax"].create(
            {
                "name": "Test Own Check Net Amount WTH 6%",
                "company_id": cls.company.id,
                "type_tax_use": "none",
                "amount_type": "percent",
                "amount": 6.0,
                "tax_group_id": tax_group.id,
                "l10n_ar_tax_type": "earnings",
                "l10n_ar_withholding_payment_type": "supplier",
                "l10n_ar_withholding_sequence_id": cls.env["ir.sequence"]
                .create({"name": "Test Own Check Net Amount WTH seq", "implementation": "standard", "padding": 4})
                .id,
                "invoice_repartition_line_ids": [
                    Command.create({"factor_percent": 100, "repartition_type": "base"}),
                    Command.create({"factor_percent": 100, "repartition_type": "tax", "account_id": wth_account.id}),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"factor_percent": 100, "repartition_type": "base"}),
                    Command.create({"factor_percent": 100, "repartition_type": "tax", "account_id": wth_account.id}),
                ],
            }
        )
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Test Own Check Net Amount FP",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [Command.create({"default_tax_id": cls.tax_wth.id, "tax_type": "withholding"})],
            }
        )

        cls.bank_journal = cls.env["account.journal"].create(
            {"name": "Test Own Check Net Amount Bank", "type": "bank", "code": "TOCNAB", "company_id": cls.company.id}
        )
        own_checks_method = cls.env.ref("l10n_latam_check.account_payment_method_own_checks")
        cls.bank_journal.write(
            {"outbound_payment_method_line_ids": [Command.create({"payment_method_id": own_checks_method.id})]}
        )
        cls.own_checks_line = cls.bank_journal.outbound_payment_method_line_ids.filtered(
            lambda line: line.code == "own_checks"
        )[:1]

    def _make_bill(self, amount, number):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-01-01",
                "company_id": self.company.id,
                "l10n_latam_document_type_id": self.invoice_doc_type.id,
                "l10n_latam_document_number": number,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test own check net amount line",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.expense_account.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        bill.action_post()
        return bill

    def _make_check_payment(self, debt, check_amount, check_number):
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal.id,
                "partner_id": self.vendor.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": "2026-01-01",
                "payment_method_line_id": self.own_checks_line.id,
                "l10n_ar_fiscal_position_id": self.fiscal_position.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
                "l10n_latam_new_check_ids": [
                    Command.create({"name": check_number, "payment_date": "2026-01-01", "amount": check_amount})
                ],
            }
        )
        payment._onchange_withholdings()
        return payment

    def test_editing_the_check_after_the_withholding_was_computed_keeps_totals_consistent(self):
        """Dado un pago con cheque propio de $940 (neto) y su retención de $60
        ya calculada, cuando se edita el cheque a $900, entonces el asiento
        sigue balanceado y la retención **no cambia** de golpe por editar el
        cheque — el cheque y la retención son dos campos independientes, no un
        cálculo que se retroalimenta.

        Cubre FCP-R10-E4.
        """
        bill = self._make_bill(1000.0, "1-2401")
        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment = self._make_check_payment(debt, 940.0, "00000310")
        wth_before = payment.l10n_ar_withholding_line_ids[0].amount

        payment.l10n_latam_new_check_ids.amount = 900.0

        with self.subTest("la retención no se recalcula por editar el cheque"):
            self.assertAlmostEqual(payment.l10n_ar_withholding_line_ids[0].amount, wth_before, places=2)
        with self.subTest("el importe del pago sigue el del cheque editado"):
            self.assertAlmostEqual(payment.amount, 900.0, places=2)

        payment.action_post()

        with self.subTest("el asiento posteado queda balanceado con el importe editado"):
            self.assertAlmostEqual(self.company.currency_id.round(sum(payment.move_id.line_ids.mapped("balance"))), 0.0)
        liq_line = payment.move_id.line_ids.filtered(lambda line: line.account_id == payment.outstanding_account_id)
        with self.subTest("la línea de liquidez lleva el importe editado, no el original"):
            self.assertAlmostEqual(abs(liq_line.balance), 900.0, places=2)
        with self.subTest("batería de invariantes"):
            self.assert_payment_invariants(payment, "cheque propio editado tras calcular la retención")

    def test_own_check_with_withholding_settles_the_invoice_in_a_single_declared_state(self):
        """Dado un pago de factura con cheque propio cargado por el **neto**
        (con su retención ya calculada), cuando se postea, entonces la
        factura queda en **un único estado declarado** — ``in_payment``, no
        ``paid`` ni "pagada o en proceso" indistintamente — porque un cheque
        propio es una promesa de pago, no efectivo acreditado: pasa a
        ``paid`` recién cuando el banco lo debita (fuera del alcance de T19,
        eso es T20).

        Corrida en ``all_v19`` hoy: con el mismo fixture que ya usa
        ``test_editing_the_check_after_the_withholding_was_computed_keeps_totals_consistent``
        (cheque a $940 neto, retención $60 sobre una deuda de $1.000), el
        pago posteado da ``payment.state == 'in_process'`` y
        ``invoice.payment_state == 'in_payment'`` de forma consistente — sin
        el asiento sobrante que sí aparece al cargar el cheque por el bruto
        (ver docstring de la clase, FCP-R10-E2).

        Se demuestra en rojo: forzando ``payment_state`` a ``'paid'`` en el
        assert (falla, porque el estado real es ``in_payment``), o rompiendo
        la reconciliación del pago con la deuda (deja la factura en
        ``not_paid`` y también hace fallar la batería de invariantes).

        Cubre FCP-R08-E4.
        """
        bill = self._make_bill(1000.0, "1-2402")
        debt = bill.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment = self._make_check_payment(debt, 940.0, "00000311")

        payment.action_post()

        with self.subTest("la factura queda en un único estado declarado: in_payment"):
            self.assert_payment_state(bill, "in_payment")
        with self.subTest("batería de invariantes"):
            self.assert_payment_invariants(payment, "cheque propio por el neto con retención")
        with self.subTest("el cheque sigue abierto en cheques a pagar hasta que se debite (T20)"):
            # ``assert_no_open_outstanding`` no aplica acá: un cheque propio queda
            # abierto en la cuenta de cheques a pagar (``outstanding_account_id``)
            # a propósito hasta el débito — es el ``issue_state`` "handed" de D4,
            # no un residual sin conciliar. Se concilia recién en
            # ``l10n_latam_check_ux:test_own_check_debit`` (T20).
            outstanding_line = payment.move_id.line_ids.filtered(
                lambda line: line.account_id == payment.outstanding_account_id
            )
            self.assertAlmostEqual(abs(outstanding_line.amount_residual), 940.0, places=2)
