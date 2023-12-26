from odoo import models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _compute_all_tax(self):
        """ Mandamos en contexto el invoice_date para calculo de impuesto con partner aliquot"""
        for line in self:
            line = line.with_context(invoice_date=line.move_id.invoice_date if not line.move_id.reversed_entry_id else line.move_id.reversed_entry_id.invoice_date)
            super(AccountMoveLine, line)._compute_all_tax()
