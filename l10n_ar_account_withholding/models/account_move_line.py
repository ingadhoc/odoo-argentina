from odoo import models, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def compute_l10n_latam_prices_and_taxes(self):
        """ When computing the prices and taxes compute we pass the invoice date
        in order to properly compute the perception/retention rates """
        for line in self:
            invoice_date = line.move_id.invoice_date or fields.Date.context_today(self)
            super(AccountMoveLine, line.with_context(invoice_date=invoice_date)).compute_l10n_latam_prices_and_taxes()
