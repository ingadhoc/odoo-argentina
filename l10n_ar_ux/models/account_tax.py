##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.onchange("price_include")
    def onchange_price_include(self):
        """En argentina, no queremos que se marque por defecto el campo"""
        if self.country_id.code != "AR":
            super().onchange_price_include()
