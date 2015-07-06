# -*- coding: utf-8 -*-
from openerp import fields, models, api, _


class account_journal(models.Model):
    _inherit = 'account.journal'

    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
        help='Partner to be used on tax settlement'
        )
    tax_code_id = fields.Many2one(
        'account.tax.code',
        'Tax Code',
        help='Set a tax code if you want to use this journal for tax settlement'
        )
    default_credit_tax_code_id = fields.Many2one(
        'account.tax.code',
        'Default Credit Tax Code',
        )
    default_debit_tax_code_id = fields.Many2one(
        'account.tax.code',
        'Default Debit Tax Code',
        )

    @api.one
    @api.constrains('company_id', 'tax_code_id')
    def check_company(self):
        if self.tax_code_id and self.company_id != self.tax_code_id.company_id:
            raise Warning(_(
                'Journal company and journal company must be the same'))
