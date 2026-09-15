from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentFiscalPositionRestoredOnDraft(TestArWithholdingArRi):
    """Volver a borrador recupera la posición fiscal del pago sin tocar sus retenciones.

    Un pago que la perdió mientras estaba validado no la recuperaba, y se volvía a validar sin que
    se le propusiera ninguna retención. Es también el estado en que quedan los pagos históricos de
    una base donde el módulo se instaló con las columnas pre-creadas desde ``_auto_init``.

    El porqué del diseño -y por qué ``state`` no está en los depends del compute- está en
    ``AccountPayment.action_draft``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.company_bank_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company_ri.id), ("type", "=", "bank")], limit=1
        )
        # Mismo fixture que test_payment_withholding_kept_on_post: contacto de entrega en CABA bajo
        # el partner RI de la clase base, que es lo que dispara la posición fiscal, y la alícuota
        # cargada en el commercial partner para no depender del webservice de AGIP.
        cls.wth_partner = cls.env["res.partner"].create(
            {
                "name": "Oficina CABA 127703",
                "parent_id": cls.res_partner_adhoc.id,
                "type": "delivery",
                "state_id": cls.env.ref("base.state_ar_c").id,
                "country_id": cls.env.ref("base.ar").id,
                "street": "Libertador 1234",
                "zip": "1000",
            }
        )
        cls.env["l10n_ar.partner.tax"].create(
            {
                "partner_id": cls.res_partner_adhoc.id,
                "tax_id": cls.tax_wth_test_1.id,
            }
        )
        cls.fiscal_pos = cls.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA",
                "l10n_ar_afip_responsibility_type_ids": [Command.set([cls.env.ref("l10n_ar.res_IVARI").id])],
                "sequence": 10,
                "auto_apply": True,
                "country_id": cls.env.ref("base.ar").id,
                "company_id": cls.company_ri.id,
                "state_ids": [Command.set([cls.env.ref("base.state_ar_c").id])],
            }
        )
        cls.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": cls.fiscal_pos.id,
                "default_tax_id": cls.tax_wth_test_1.id,
                "tax_type": "withholding",
            }
        )

    def _create_draft_payment(self, document_number):
        """Factura de proveedor en CABA, con el pago en borrador y la retención que propone la FP."""
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.wth_partner.id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 500000,
                            "tax_ids": [Command.set(self.tax_21.ids)],
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": document_number,
            }
        )
        invoice.action_post()

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
        self.assertEqual(
            payment.l10n_ar_fiscal_position_id,
            self.fiscal_pos,
            "Precondición: en borrador el pago toma la posición fiscal con retención.",
        )
        self.assertTrue(
            payment.l10n_ar_withholding_line_ids,
            "Precondición: en borrador el pago tiene la línea de retención automática.",
        )
        return payment

    def _clear_fiscal_position_keeping_lines(self, payment):
        """Deja el pago validado sin posición fiscal, como queda tras un recompute sobre un posteado.

        Se protegen las líneas de retención porque lo que se quiere reproducir es el estado final
        -sin posición fiscal, con las retenciones ya emitidas-, no el camino que lleva ahí.
        """
        with self.env.protecting([payment._fields["l10n_ar_withholding_line_ids"]], payment):
            payment.l10n_ar_fiscal_position_id = False

    def test_going_back_to_draft_recovers_the_fiscal_position_and_keeps_the_lines(self):
        payment = self._create_draft_payment("1-127703")
        payment.action_post()
        wth_line_ids = payment.l10n_ar_withholding_line_ids.ids
        wth_amounts = payment.l10n_ar_withholding_line_ids.mapped("amount")
        self._clear_fiscal_position_keeping_lines(payment)
        self.assertFalse(
            payment.l10n_ar_fiscal_position_id, "Precondición: el pago validado quedó sin posición fiscal."
        )

        payment.action_draft()

        self.assertEqual(payment.state, "draft")
        self.assertEqual(
            payment.l10n_ar_fiscal_position_id,
            self.fiscal_pos,
            "Al volver a borrador el pago debe recuperar su posición fiscal.",
        )
        self.assertEqual(
            payment.l10n_ar_withholding_line_ids.ids,
            wth_line_ids,
            "Volver a borrador recupera la posición fiscal, no regenera las retenciones existentes.",
        )
        self.assertEqual(
            payment.l10n_ar_withholding_line_ids.mapped("amount"),
            wth_amounts,
            "Los importes de las retenciones existentes no deben cambiar al volver a borrador.",
        )

    def test_manually_edited_withholding_amount_survives_going_back_to_draft(self):
        """El caso que decide el diseño: lo que el usuario editó a mano no se pisa."""
        payment = self._create_draft_payment("2-127703")
        wth_line = payment.l10n_ar_withholding_line_ids[0]
        edited_amount = wth_line.amount + 1000
        wth_line.amount = edited_amount
        payment.action_post()
        self._clear_fiscal_position_keeping_lines(payment)

        payment.action_draft()

        self.assertEqual(wth_line.exists(), wth_line, "La línea editada a mano no debe borrarse.")
        self.assertEqual(
            wth_line.amount,
            edited_amount,
            "El importe editado a mano debe sobrevivir al pase a borrador.",
        )
