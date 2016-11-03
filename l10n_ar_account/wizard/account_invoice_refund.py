# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class AccountInvoiceRefund(models.TransientModel):

    _inherit = 'account.invoice.refund'

    @api.multi
    def compute_refund(self, mode='refund'):
        res = super(AccountInvoiceRefund, self).compute_refund(mode=mode)
        domain = res.get('domain', [])
        refund_invoices = self.env['account.invoice'].search(domain)
        # invoice = self.env['account.invoice'].browse(invoice_ids)
        refund_invoices.write({
            'afip_service_start': self.invoice_id.afip_service_start,
            'afip_service_end': self.invoice_id.afip_service_end,
        })
        return res
