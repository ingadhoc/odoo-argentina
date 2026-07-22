from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentWithholdingKeptOnPost(TestArWithholdingArRi):
    """Regression para el ticket 113171 / tarea 65423.

    Bug reportado (video de jjs): al *validar* (postear) un pago de proveedor con
    retenciones automáticas -calculadas desde la posición fiscal- se borraban tanto
    las retenciones del pago como la posición fiscal.

    Root cause (en ``account_payment_pro``, revertido en PR #950): el constraint
    ``_check_to_pay_lines_account`` llamaba a ``_clean_invalid_to_pay_lines()``, que
    al postear reescribía ``to_pay_move_line_ids`` (la línea de la factura conciliada
    ya no cumple el dominio ``reconciled = False``). Ese write disparaba en
    ``l10n_ar_tax`` el recompute de ``_compute_fiscal_position_id`` -que con
    ``state != 'draft'`` fija ``l10n_ar_fiscal_position_id = False``- y en cascada
    ``_compute_l10n_ar_withholding_line_ids``, que hacía ``Command.clear()`` sobre las
    líneas de retención.

    El test reproduce el caso del video y valida el comportamiento correcto: después
    de validar el pago, las retenciones y la posición fiscal deben seguir presentes.
    """

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.company_bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )
        # Partner de CABA creado en el test (no demo): contacto de entrega bajo el fixture base
        # res_partner_adhoc (RI), replicando la estructura del demo res_partner_adhoc_caba. La
        # dirección de entrega en CABA es la que dispara la posición fiscal.
        self.wth_partner = self.env["res.partner"].create(
            {
                "name": "Oficina CABA 113171",
                "parent_id": self.res_partner_adhoc.id,
                "type": "delivery",
                "state_id": self.env.ref("base.state_ar_c").id,
                "country_id": self.env.ref("base.ar").id,
                "street": "Libertador 1234",
                "zip": "1000",
            }
        )
        # Alícuota de retención cargada explícitamente en el commercial partner (2.5%), para que
        # _l10n_ar_add_taxes la resuelva desde l10n_ar_partner_tax_ids sin depender del webservice
        # de AGIP (que solo devuelve la alícuota demo si está cargada la data demo). Copiamos
        # tax_wth_test_1 para conservar grupo y jurisdicción (IIBB CABA) y fijamos el 2.5%.
        self.wth_tax_caba = self.tax_wth_test_1.copy({"name": "IIBB WTH CABA 2.5%", "amount": 2.5})
        self.env["l10n_ar.partner.tax"].create(
            {
                "partner_id": self.res_partner_adhoc.id,
                "tax_id": self.wth_tax_caba.id,
            }
        )

    def test_withholding_and_fiscal_position_kept_after_post(self):
        # 1. Factura de proveedor para un partner de CABA y postear.
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.wth_partner.id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            # Reusamos el fixture product_a de la clase base (no demo de Odoo core) con
                            # IVA 21% explícito, igual patrón que TestArWithholdingArRi.in_invoice_wht.
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 500000,
                            "tax_ids": [Command.set(self.tax_21.ids)],
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": "1-113171",
            }
        )
        invoice.action_post()

        # 2. Posición fiscal con retención IIBB CABA auto-aplicable para el partner.
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA",
                "l10n_ar_afip_responsibility_type_ids": [(6, 0, [self.env.ref("l10n_ar.res_IVARI").id])],
                "sequence": 10,
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "company_id": self.company_ri.id,
                "state_ids": [(6, 0, [self.env.ref("base.state_ar_c").id])],
            }
        )
        # La retención se resuelve contra la alícuota cargada en el partner (self.wth_tax_caba, 2.5%),
        # que comparte grupo y jurisdicción con default_tax_id; no usamos webservice para no depender
        # de la data demo.
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_pos.id,
                "default_tax_id": self.tax_wth_test_1.id,
                "tax_type": "withholding",
            }
        )

        # 3. Registrar el pago: la retención se calcula automáticamente desde la posición fiscal.
        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create(
                {
                    "journal_id": self.company_bank_journal.id,
                    "amount": invoice.amount_total,
                    "date": self.today,
                }
            )
        )

        # Precondición: en borrador el pago toma la posición fiscal y la línea de retención.
        self.assertEqual(
            payment.l10n_ar_fiscal_position_id,
            fiscal_pos,
            "El pago en borrador debe tomar la posición fiscal con retención.",
        )
        wth_line = payment.l10n_ar_withholding_line_ids.filtered(
            lambda line: line.tax_id.tax_group_id == self.tax_wth_test_1.tax_group_id
        )
        self.assertTrue(wth_line, "El pago en borrador debe tener la línea de retención automática.")
        draft_wth_line_ids = payment.l10n_ar_withholding_line_ids.ids

        # La base de la retención es el neto del comprobante (500.000) y el importe la alícuota
        # cargada en el partner (2.5%) aplicada sobre esa base: 500.000 * 2.5% = 12.500.
        self.assertEqual(wth_line.base_amount, 500000, "La base de la retención debe ser el neto (500.000).")
        self.assertEqual(wth_line.amount, 12500, "La retención debe ser 500.000 * 2.5% = 12.500.")

        # 4. Validar (postear) el pago: es el paso donde el bug borraba las retenciones.
        payment.action_post()
        # Forzamos el flush como al final de un request real: es cuando corre el constraint
        # diferido de ``account_payment_pro`` sobre ``to_pay_move_line_ids`` -ya con la línea
        # de la factura conciliada- que en el bug reescribía las líneas y disparaba la cascada
        # que borraba retenciones y posición fiscal.
        self.env.flush_all()
        self.assertEqual(payment.move_id.state, "posted")

        # 5. Assert central del ticket 113171: al validar, las retenciones NO se borran.
        self.assertTrue(
            payment.l10n_ar_withholding_line_ids,
            "Al validar el pago las retenciones NO deben borrarse (ticket 113171).",
        )
        self.assertEqual(
            sorted(payment.l10n_ar_withholding_line_ids.ids),
            sorted(draft_wth_line_ids),
            "Las líneas de retención del pago validado deben ser las mismas del borrador.",
        )

        # 5b. La posición fiscal tampoco debe borrarse (título del ticket: "se elimina la pos fiscal en pagos").
        self.assertEqual(
            payment.l10n_ar_fiscal_position_id,
            fiscal_pos,
            "Al validar el pago la posición fiscal NO debe borrarse.",
        )

        # 5c. El asiento contable del pago validado debe conservar la línea de impuesto de retención.
        posted_wth_lines = payment.move_id.line_ids.filtered(lambda line: line.tax_repartition_line_id)
        self.assertTrue(
            posted_wth_lines,
            "El asiento del pago validado debe conservar la línea de retención.",
        )
