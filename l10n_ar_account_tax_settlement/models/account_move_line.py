# -*- coding: utf-8 -*-
from openerp import fields, models, api
# from openerp.exceptions import Warning


class account_move_line(models.Model):
    _inherit = 'account.move.line'

    # tax_settlement_id = fields.Many2one(
    tax_settlement_detail_id = fields.Many2one(
        'account.tax.settlement.detail',
        # 'account.tax.settlement',
        'Tax Settlement Detail',
        )
    tax_amount_with_sign = fields.Boolean(
        'Tax Amount With Sign',
        compute='get_tax_amount_with_sign'
        )

    @api.one
    @api.depends('tax_amount', 'tax_code_id.sign')
    def get_tax_amount_with_sign(self):
        self.tax_amount_with_sign = self.tax_amount * self.tax_code_id.sign
