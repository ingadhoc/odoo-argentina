from odoo import models, api
import functools


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id.l10n_ar_currency_rate')
    def _compute_currency_rate(self):

        print("---- US FORCE _compute_currency_rate")

        forced = self.filtered(lambda x: x.move_id.l10n_ar_currency_rate)
        for rec in forced:
            rec.currency_rate = 1 / rec.move_id.l10n_ar_currency_rate if (rec.currency_id != rec.move_id.company_currency_id) else 1

        # method = super(AccountMoveLine, self - forced)._compute_currency_rate
        # endpoint = functools.partial(method)
        # functools.update_wrapper(endpoint, method)
        # self.clear_caches()

        super(AccountMoveLine, self - forced)._compute_currency_rate()
