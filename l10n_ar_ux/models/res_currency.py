from odoo import models, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _search_by_name(self, currency_name):
        """ This method was original defined in ingadhoc/enterprise-extensions/account_balance_import.
        We overwrited completely in order to add the logic of AFIP Code """
        return self.search(["|", ("name", "=", currency_name), ("l10n_ar_afip_code", "=", currency_name)])
