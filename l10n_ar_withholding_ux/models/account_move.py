from odoo import models


class AccountMove(models.Model):

    _inherit = "account.move"

    def _get_tax_factor(self):
        self.ensure_one()
        return (self.amount_total and (self.amount_untaxed / self.amount_total) or 1.0)
