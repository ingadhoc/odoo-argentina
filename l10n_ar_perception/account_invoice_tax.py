# -*- coding: utf-8 -*-
from openerp import models, api


class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'

    @api.one
    @api.onchange('tax_code_id')
    def _onchange_tax_code(self):
        if self.tax_code_id:
            self.name = 'asdasd'
            self.account_id = False

                # if invoice.type in ('out_invoice','in_invoice'):
                #     val['base_code_id'] = tax['base_code_id']
                #     val['tax_code_id'] = tax['tax_code_id']
                #     val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                #     val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                #     val['account_id'] = tax['account_collected_id'] or line.account_id.id
                #     val['account_analytic_id'] = tax['account_analytic_collected_id']
                # else:
                #     val['base_code_id'] = tax['ref_base_code_id']
                #     val['tax_code_id'] = tax['ref_tax_code_id']
                #     val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                #     val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                #     val['account_id'] = tax['account_paid_id'] or line.account_id.id
                #     val['account_analytic_id'] = tax['account_analytic_paid_id']