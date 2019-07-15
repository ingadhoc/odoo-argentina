##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    arba_code = fields.Char(
    )
    lot_ids = fields.Many2many(
        'stock.production.lot',
        compute='_compute_lots',
    )

    @api.multi
    def _compute_lots(self):
        for rec in self:
            rec.lot_ids = rec.move_line_ids.mapped('move_line_ids.lot_id')

    @api.multi
    @api.constrains('arba_code')
    def check_arba_code(self):
        for rec in self.filtered('arba_code'):
            if len(rec.arba_code) != 6 or not rec.arba_code.isdigit():
                raise UserError(_(
                    'El código según nomenclador de arba debe ser de 6 dígitos'
                    ' numéricos'))
