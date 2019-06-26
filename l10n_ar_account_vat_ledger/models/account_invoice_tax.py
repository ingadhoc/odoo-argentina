##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    invoice_id = fields.Many2one(
        auto_join=True,
    )
    cc_base = fields.Monetary(
        string='Company Cur. Base',
        compute="_get_currency_values",
    )
    cc_amount = fields.Monetary(
        string='Company Cur. Amount',
        compute="_get_currency_values",
    )

    @api.multi
    @api.depends('currency_id')
    def _get_currency_values(self):
        # TODO si traer el rate de esta manera no resulta (por ej. porque
        # borran una linea de rate), entonces podemos hacerlo desde el move
        # mas o menos como hace account_invoice_currency o viendo el total de
        # debito o credito de ese mismo
        for rec in self:
            currency = rec.currency_id.with_context(
                company_id=rec.company_id.id,
                date=rec.invoice_id.date_invoice or
                fields.Date.context_today(rec))
            if not currency:
                continue
            if rec.company_id.currency_id == currency:
                rec.cc_base = rec.base
                rec.cc_amount = rec.amount
            else:
                # nueva modalidad de currency_rate
                currency_rate = rec.invoice_id.currency_rate or \
                    currency.compute(
                        1., rec.company_id.currency_id, round=False)
                # TODO borrar
                # currency_rate = currency.compute
                #     1.0, rec.company_id.currency_id, round=False)
                # otra alternativa serua usar currency.compute con round true
                # para cada uno de estos valores
                rec.cc_base = currency.round(
                    rec.base * currency_rate)
                rec.cc_amount = currency.round(
                    rec.amount * currency_rate)
