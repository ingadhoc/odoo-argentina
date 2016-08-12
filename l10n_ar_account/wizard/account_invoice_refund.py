# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        """
        We ad afip service start and afip end
        """
        invoice_ids = self._context.get('active_ids', [])
        if invoice_ids:
            invoices = self.env['account.invoice'].browse(invoice_ids)
            invoice = invoices[0]
            self = self.with_context(
                default_afip_service_start=invoice.afip_service_start,
                afip_service_start=invoice.afip_service_start,
                afip_service_end=invoice.afip_service_start,
                default_afip_service_end=invoice.afip_service_end,
                )
        return super(AccountInvoiceRefund, self).compute_refund(
            mode)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
