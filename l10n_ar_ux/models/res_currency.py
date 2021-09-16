from odoo import models, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        return self._context.get('force_rate', False) or super()._get_conversion_rate(
            from_currency, to_currency, company, date)
