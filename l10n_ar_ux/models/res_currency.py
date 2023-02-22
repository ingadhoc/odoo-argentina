from odoo import models, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        return self._context.get('force_rate', False) or super()._get_conversion_rate(
            from_currency, to_currency, company, date)

    @api.model
    def _search_by_name(self, currency_name):
        """ This method was original defined in ingadhoc/enterprise-extensions/account_balance_import.
        We overwrited completely in order to add the logic of AFIP Code """
        return self.search(["|", ("name", "=", currency_name), ("l10n_ar_afip_code", "=", currency_name)])
