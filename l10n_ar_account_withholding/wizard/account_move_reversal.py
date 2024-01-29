from odoo import models


class AccountMoveReversal(models.TransientModel):

    _inherit = "account.move.reversal"

    def reverse_moves(self, is_modify=False):
        """ Forzamos fecha de la factura original para que el amount total de la linea se calcule bien"""
        if self.move_ids:
            self = self.with_context(invoice_date=self.move_ids[0].date)
        return super(AccountMoveReversal, self).reverse_moves(is_modify=is_modify)
