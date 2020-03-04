##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    computed_currency_rate = fields.Float(
        compute='_compute_currency_rate',
        string='Currency Rate (preview)',
        digits=(16, 4),
    )

    @api.depends('currency_id', 'company_id', 'invoice_date')
    def _compute_currency_rate(self):
        for rec in self:
            if rec.currency_id and rec.company_id and (rec.currency_id != rec.company_id.currency_id):
                rec.computed_currency_rate = rec.currency_id._convert(
                    1.0, self.company_id.currency_id, self.company_id,
                    date=rec.invoice_date or fields.Date.context_today(rec),
                    round=False)
            else:
                rec.computed_currency_rate = 1.0
