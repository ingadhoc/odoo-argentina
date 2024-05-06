from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _process_order(self, order, draft, existing_order):
        return super(PosOrder, self.with_context(allow_no_partner=True))._process_order(order=order, draft=draft, existing_order=existing_order)

    def action_pos_order_invoice(self):
        """
            Agrego este contexto para evitar el bloqueo en los modulos saas.
        """
        return super(PosOrder, self.with_context(allow_no_partner=True)).action_pos_order_invoice()


    def _create_misc_reversal_move(self, payment_moves):
        """
            Agrego este contexto para evitar el bloqueo en los modulos saas.
        """
        return super(PosOrder, self.with_context(allow_no_partner=True))._create_misc_reversal_move(payment_moves=payment_moves)

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        invoice_ids = self.refunded_order_ids.mapped("account_move").filtered(
            lambda x: x.company_id.country_id.code == "AR"
            and x.is_invoice()
            and x.move_type in ["out_invoice"]
        )
        if len(invoice_ids) > 1:
            raise UserError(_("Only can refund one invoice at a time"))

        elif len(invoice_ids) == 1:
            vals["reversed_entry_id"] = invoice_ids[0].id
        return vals
