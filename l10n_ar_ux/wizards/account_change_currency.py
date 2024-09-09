from odoo import fields, models


class AccountChangeCurrency(models.TransientModel):
    _inherit = 'account.change.currency'

    def change_currency(self):
        super().change_currency()
        if self.change_type == 'currency':
            self.move_id.l10n_ar_currency_rate = False
