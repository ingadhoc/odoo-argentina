from odoo import models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    withholding_id = fields.Many2one('l10n_ar.payment.withholding', compute='_compute_withholding')

    def _compute_withholding(self):
        for rec in self:
            if rec.tax_line_id and rec.payment_id:
                rec.withholding_id = rec.payment_id.l10n_ar_withholding_line_ids.filtered(lambda x: x.tax_id == rec.tax_line_id)
            else:
                rec.withholding_id = False

    def _compute_all_tax(self):
        """ Mandamos en contexto el invoice_date para calculo de impuesto con partner aliquot"""
        for line in self:
            line = line.with_context(invoice_date=line.move_id.invoice_date if not line.move_id.reversed_entry_id else line.move_id.reversed_entry_id.invoice_date)
            super(AccountMoveLine, line)._compute_all_tax()
