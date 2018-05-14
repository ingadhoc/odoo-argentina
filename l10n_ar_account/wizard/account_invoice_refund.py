##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountInvoiceRefund(models.TransientModel):

    _inherit = 'account.invoice.refund'

    @api.multi
    def compute_refund(self, mode='refund'):
        res = super(AccountInvoiceRefund, self).compute_refund(mode=mode)
        if isinstance(res, dict):
            domain = res.get('domain', [])
            refund_invoices = self.env['account.invoice'].search(domain)
            # invoice = self.env['account.invoice'].browse(invoice_ids)
            invoice = self.invoice_id
            refund_invoices.write({
                # TODO this origin should be set on account_document module
                'origin': invoice.document_number or invoice.number,
                'afip_service_start': invoice.afip_service_start,
                'afip_service_end': invoice.afip_service_end,
            })
        return res
