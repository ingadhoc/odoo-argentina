from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOwnCheckNetAmount(TransactionCase):
    """D1: en un pago con cheque propio y retención, el importe del cheque es
    el neto (deuda − retenciones) — es lo que la OP precalcula hoy.

    FCP-R10: la OP dejaba pasar un cheque cargado por el total de la factura
    (bruto) habiendo retención, y el proveedor quedaba con un saldo a favor
    que nadie pedía. FCP-R10-E1/E3/E5/E6 (el neto en sus variantes de moneda,
    N cheques y write-off) están cubiertos en
    ``test_payment_withholding_checks_multimoneda`` (TC.6/TC.7/TC.9/TC.8).

    FCP-R10-E2 (cheque cargado por el bruto) queda **sin implementar**: en el
    build de runbot de la PR, postear ese escenario levanta
    ``ValidationError`` — ``_get_blocking_l10n_latam_warning_msg`` detecta que
    ``amount`` (940, recalculado por ``_onchange_withholdings``) no coincide
    con el total del cheque (1.000) — pero D1 dice exactamente lo contrario:
    "no se despeja el bruto ni se avisa la diferencia". Contradice la
    definición cerrada con gl; no es un caso de arrastrar sandbox vs. runbot,
    es una pregunta de producto (¿el bloqueo es el bug, o D1 quedó
    desactualizado?) que hay que resolver con gl antes de fijar el test.

    No hereda de ``TestArCommon``/``AccountTestInvoicingCommon``: esa base
    crea su propia compañía y choca con el ACL de productos en bases
    full-OBA (ver ``reference_v18_tests_transactioncase``). En su lugar,
    reutiliza una compañía AR ya configurada, igual que
    ``test_reset_and_recompute_rate.py`` en ``account_payment_pro``.

    Cubre FCP-R10-E4.
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
