from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id.l10n_ar_currency_rate')
    def _compute_currency_rate(self):
        forced = self.filtered(lambda x: x.move_id.l10n_ar_currency_rate)
        for rec in forced:
            rec.currency_rate = rec.move_id.l10n_ar_currency_rate
        return super(AccountMoveLine, self - forced)._compute_currency_rate()
