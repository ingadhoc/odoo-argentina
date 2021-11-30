# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    invoice_currency_id = fields.Many2one('res.currency', string='Invoice Currency', readonly=True)
    line_id = fields.Many2one('account.move.line', string='Journal Item', readonly=True)
    price_unit = fields.Monetary('Unit Price', readonly=True, currency_field='invoice_currency_id',)
    discount = fields.Float('Discount (%)', readonly=True)
    discount_amount = fields.Monetary(
        'Discount Amount', readonly=True, group_operator="sum", currency_field='invoice_currency_id',)
    price_subtotal = fields.Monetary(currency_field='company_currency_id')
    price_average = fields.Monetary(currency_field='company_currency_id')

    _depends = {'account.move.line': ['price_unit', 'discount']}

    def _select(self):
        return super()._select() + """,
            line.price_unit,
            line.id as line_id,
            move.currency_id as invoice_currency_id,
            line.discount,
            line.price_unit * line.quantity * line.discount/100 *
                (CASE WHEN move
                .move_type IN ('in_refund','out_refund','in_receipt') THEN -1 ELSE 1 END) as discount_amount
            """

    def _group_by(self):
        return super()._group_by() + ", move.invoice_currency_id"
