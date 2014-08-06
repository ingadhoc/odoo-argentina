# -*- coding: utf-8 -*-
from openerp import osv, models, fields, api

class account_voucher_receipt (models.Model):
       
    _inherit = "account.voucher.receipt" 

    @api.multi
    def get_pay_lines(self):
        res = self.search([('id','=',5)])
        return res