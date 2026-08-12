"""
Tests de re-sincronización del cheque nuevo cuando cambian las retenciones
=========================================================================

El importe del cheque nuevo se autocompleta una sola vez, con la diferencia pendiente
(``_onchange_new_check_default_amount`` de account_payment_pro, que solo pisa cheques sin
importe). Si las retenciones cambian después de ese autollenado, el cheque queda con el
importe viejo y el pago se confirma con diferencia: la factura queda con residual, o el
partner con un crédito, por exactamente lo que cambió la retención.

Ver ingadhoc/account-payment#1141.
"""

from odoo import Command
from odoo.addons.l10n_ar_tax.tests.test_payment_withholding_multimoneda import TestPaymentWithholdingMultimoneda
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestPaymentCheckWithholdingResync(TestPaymentWithholdingMultimoneda):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        own_checks_method = cls.env.ref("l10n_latam_check.account_payment_method_own_checks")
        if not cls.bank_ars.outbound_payment_method_line_ids.filtered(lambda line: line.code == "own_checks"):
            cls.bank_ars.write(
                {"outbound_payment_method_line_ids": [Command.create({"payment_method_id": own_checks_method.id})]}
            )
        cls.own_checks_pml = cls.bank_ars.outbound_payment_method_line_ids.filtered(
            lambda line: line.code == "own_checks"
        )

        new_third_party_method = cls.env.ref("l10n_latam_check.account_payment_method_new_third_party_checks")
        if not cls.bank_ars.inbound_payment_method_line_ids.filtered(
            lambda line: line.code == "new_third_party_checks"
        ):
            cls.bank_ars.write(
                {"inbound_payment_method_line_ids": [Command.create({"payment_method_id": new_third_party_method.id})]}
            )
        cls.new_third_party_pml = cls.bank_ars.inbound_payment_method_line_ids.filtered(
            lambda line: line.code == "new_third_party_checks"
        )
        cls.new_third_party_pml.payment_account_id = cls.env["account.account"].create(
            {
                "name": "Cheques de Terceros Test",
                "code": "TCHQ",
                "account_type": "asset_current",
                "company_ids": [Command.set([cls.company.id])],
            }
        )

        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": "Ventas Test",
                "type": "sale",
                "code": "STEST",
                "company_id": cls.company.id,
                "l10n_latam_use_documents": False,
            }
        )

    def _create_check_payment(self, invoice, fiscal_position=None):
        """Pago proveedor con cheques propios, en borrador y todavía sin cheques."""
        debt = invoice.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        return self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "payment_method_line_id": self.own_checks_pml.id,
                "l10n_ar_fiscal_position_id": fiscal_position and fiscal_position.id or False,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
            }
        )

    def _create_customer_invoice(self, amount):
        """Factura de cliente sin impuestos: la deuda es exactamente ``amount``."""
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "invoice_date": self.today,
                "date": self.today,
                "move_type": "out_invoice",
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.account_expense.id,
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _add_check(self, form, name="00000001"):
        with form.l10n_latam_new_check_ids.new() as check:
            check.name = name
            check.payment_date = self.today

    # ------------------------------------------------------------------
    # Casos
    # ------------------------------------------------------------------

    def test_resync_al_agregar_retencion(self):
        """Cheque primero y retención después: el cheque baja por la retención.

        Sin la re-sincronización el cheque quedaba en la deuda completa y el pago cubría
        deuda + retención, dejándole un crédito al proveedor.
        """
        invoice = self._create_invoice(1_000, self.ars)
        payment = self._create_check_payment(invoice)

        with Form(payment) as form:
            self._add_check(form)
            with form.l10n_latam_new_check_ids.edit(0) as check:
                self.assertAlmostEqual(check.amount, 1_210, places=2)
            form.l10n_ar_fiscal_position_id = self.fp_iibb

        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)
        self.assertAlmostEqual(payment.l10n_latam_new_check_ids.amount, 1_180, places=2)
        self.assertAlmostEqual(payment.payment_difference, 0, places=2)

        payment.action_post()
        self.assertAlmostEqual(invoice.amount_residual, 0, places=2)

    def test_resync_al_quitar_retencion(self):
        """Se saca la retención después del autollenado: el cheque vuelve a la deuda completa.

        Sin la re-sincronización el cheque quedaba corto y la factura quedaba parcial por el
        importe de la retención que se sacó (el síntoma reportado en el issue).
        """
        invoice = self._create_invoice(1_000, self.ars)
        payment = self._create_check_payment(invoice, self.fp_iibb)

        with Form(payment) as form:
            self._add_check(form)
            with form.l10n_latam_new_check_ids.edit(0) as check:
                self.assertAlmostEqual(check.amount, 1_180, places=2)
            form.l10n_ar_fiscal_position_id = self.env["account.fiscal.position"]

        self.assertAlmostEqual(payment.withholdings_amount, 0, places=2)
        self.assertAlmostEqual(payment.l10n_latam_new_check_ids.amount, 1_210, places=2)
        self.assertAlmostEqual(payment.payment_difference, 0, places=2)

        payment.action_post()
        self.assertAlmostEqual(invoice.amount_residual, 0, places=2)

    def test_resync_al_editar_el_importe_retenido(self):
        """Se edita a mano el importe de la retención: el cheque acompaña el nuevo importe."""
        invoice = self._create_invoice(1_000, self.ars)
        payment = self._create_check_payment(invoice, self.fp_iibb)

        with Form(payment) as form:
            self._add_check(form)
            with form.l10n_ar_withholding_line_ids.edit(0) as withholding:
                withholding.amount = 20

        self.assertAlmostEqual(payment.withholdings_amount, 20, places=2)
        self.assertAlmostEqual(payment.l10n_latam_new_check_ids.amount, 1_190, places=2)
        self.assertAlmostEqual(payment.payment_difference, 0, places=2)

    def test_resync_en_cobro_a_cliente(self):
        """Dado un cobro a cliente con un cheque de terceros nuevo ya cargado, cuando se agrega la
        retención que sufrió el cliente, entonces el cheque baja por esa retención.

        Es el escenario reportado: en cobros a cliente las retenciones se cargan a mano (los
        computes de la línea filtran ``partner_type == "supplier"``), así que el cheque siempre se
        carga antes que la retención y el autollenado ya corrió.
        """
        invoice = self._create_customer_invoice(1_000)
        debt = invoice.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable")
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": self.today,
                "payment_method_line_id": self.new_third_party_pml.id,
                "to_pay_move_line_ids": [Command.set(debt.ids)],
            }
        )

        with Form(payment) as form:
            self._add_check(form)
            with form.l10n_latam_new_check_ids.edit(0) as check:
                self.assertAlmostEqual(check.amount, 1_000, places=2)
            with form.l10n_ar_withholding_line_ids.new() as withholding:
                withholding.tax_id = self.tax_ret_iibb
                withholding.amount = 30

        self.assertAlmostEqual(payment.withholdings_amount, 30, places=2)
        self.assertAlmostEqual(payment.l10n_latam_new_check_ids.amount, 970, places=2)
        self.assertAlmostEqual(payment.payment_difference, 0, places=2)

    def test_no_resync_al_cambiar_el_partner(self):
        """Dado un pago con un cheque ya cargado, cuando se cambia el partner, entonces el importe
        del cheque no se toca.

        ``_onchange_partner_id`` re-dispara el ajuste del ``amount``, pero el importe del cheque lo
        escribe quien carga el pago: solo lo movemos cuando cambian las retenciones, que es el bug
        que este fix corrige.

        No chequeamos el ``amount`` del pago porque en este camino queda desincronizado de los
        cheques (lo pisa ``_onchange_to_pay_lines_adjust_amount`` de account_payment_pro al
        recomputarse la deuda del partner nuevo), con o sin este fix. Es otro problema.
        """
        self._create_invoice(1_000, self.ars)
        invoice_cf = self.env["account.move"].create(
            {
                "partner_id": self.partner_cf.id,
                "invoice_date": self.today,
                "date": self.today,
                "move_type": "in_invoice",
                "journal_id": self.purchase_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {"name": "Test", "quantity": 1, "price_unit": 500, "account_id": self.account_expense.id}
                    )
                ],
            }
        )
        invoice_cf.action_post()

        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_ars.id,
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "date": self.today,
                "payment_method_line_id": self.own_checks_pml.id,
            }
        )

        with Form(payment) as form:
            self._add_check(form)
            with form.l10n_latam_new_check_ids.edit(0) as check:
                self.assertAlmostEqual(check.amount, 1_210, places=2)
            form.partner_id = self.partner_cf

        self.assertAlmostEqual(payment.to_pay_amount, 500, places=2)
        self.assertAlmostEqual(payment.l10n_latam_new_check_ids.amount, 1_210, places=2)

    def test_no_resync_con_varios_cheques(self):
        """Con más de un cheque no ajustamos ninguno: no hay cuál elegir sin adivinar.

        Queda la diferencia a la vista en el pago para que la resuelva quien lo carga.
        """
        invoice = self._create_invoice(1_000, self.ars)
        payment = self._create_check_payment(invoice)

        with Form(payment) as form:
            self._add_check(form, "00000001")
            with form.l10n_latam_new_check_ids.edit(0) as check:
                check.amount = 610
            self._add_check(form, "00000002")
            form.l10n_ar_fiscal_position_id = self.fp_iibb

        self.assertAlmostEqual(sum(payment.l10n_latam_new_check_ids.mapped("amount")), 1_210, places=2)
        self.assertAlmostEqual(payment.payment_difference, -30, places=2)
