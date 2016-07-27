# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class account_invoice_refund(models.TransientModel):

    # we inherit refund creation to choose a company journal and also try to
    # choose a journal of same point of sale

    _inherit = 'account.invoice.refund'

    @api.model
    def _get_invoice_id(self):
        return self._context.get('active_id', False)

    # @api.one
    @api.multi
    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        journal_type = False
        if self.invoice_id.type == 'out_refund' or 'out_invoice':
            journal_type = 'sale_refund'
        elif self.invoice_id.type == 'in_refund' or 'in_invoice':
            journal_type = 'purchase_refund'
        # return {'domain': {'journal_id': price}}
        journals = self.env['account.journal'].search(
            [('type', '=', journal_type),
             ('company_id', '=', self.invoice_id.company_id.id)])
        periods = self.env['account.period'].search(
            [('company_id', '=', self.invoice_id.company_id.id)])
        # self.journal_type = journal_type

        point_of_sale = self.invoice_id.journal_id.point_of_sale_id
        journal = self.env['account.journal']
        if point_of_sale:
            journal = journal.search(
                [('type', '=', journal_type),
                 ('company_id', '=', self.invoice_id.company_id.id),
                 ('point_of_sale_id', '=', point_of_sale.id),
                 ], limit=1)
            if not journal and journals:
                journal = journals[0]
        if journal:
            self.journal_id = journal.id
        return {'domain': {
            'journal_id': [('id', 'in', journals.ids)],
            'period': [('id', 'in', periods.ids)]
        }}

    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice',
        default=_get_invoice_id,
        store=True)

    @api.multi
    def compute_refund(self, data_refund):
        invoice_ids = self._context.get('active_ids', [])
        if not invoice_ids:
            return super(account_invoice_refund, self).compute_refund(
                data_refund)
        elif len(invoice_ids) > 1:
            raise Warning(_(
                'Solo una factura puede ser reembolsada en cada operación'))
        invoice = self.env['account.invoice'].browse(invoice_ids)
        if not self.period:
            date = self.date or invoice.date_invoice
            period = date
            self.env['account.period'].find()
            period = self.env['account.period'].with_context(
                company_id=invoice.company_id.id).find(date)[:1]
            self.period = period.id
        res = super(account_invoice_refund, self).compute_refund(data_refund)
        domain = res.get('domain', [])
        refund_invoices = invoice.search(domain)
        origin = invoice.number
        refund_invoices.write({
            'origin': origin,
            'afip_service_start': invoice.afip_service_start,
            'afip_service_end': invoice.afip_service_end,
        })
        if self.pool.get('sale.order'):
            sale_orders = self.env['sale.order'].search(
                [('invoice_ids', 'in', invoice_ids)])
            for refund_invoice in refund_invoices:
                sale_orders.write(
                    {'invoice_ids': [(4, refund_invoice.id)]})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
