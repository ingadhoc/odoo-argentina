# -*- coding: utf-8 -*-
from openerp import fields, models
# from openerp.exceptions import Warning


class account_move_line(models.Model):
    _inherit = 'account.move.line'
    _inherit = ['mail.thread']

    # tax_settlement_id = fields.Many2one(
    tax_settlement_detail_id = fields.Many2one(
        'account.tax.settlement.detail',
        # 'account.tax.settlement',
        'Tax Settlement Detail',
        )
