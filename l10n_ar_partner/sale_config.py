# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api
from openerp.tools.safe_eval import safe_eval


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_multiple_id_numbers = fields.Boolean(
        "Allow Multiple Id Numbers on Partners",
        help="If you allow multiple Id Numbers, then a new tab for 'Id "
        "NUmbers' will be added on partner form view",
        implied_group='l10n_ar_partner.group_multiple_id_numbers',
    )
    unique_id_numbers = fields.Boolean(
        "Restrict Id Numbers to be Unique",
        help="If you set it True, then we will check that partner Id Numbers "
        "(for eg. cuit, dni, etc) are unique",
    )

    @api.multi
    def get_default_unique_id_numbers(self):
        unique_id_numbers = self.env['ir.config_parameter'].get_param(
            "l10n_ar_partner.unique_id_numbers", 'False')
        return {
            'unique_id_numbers': safe_eval(unique_id_numbers),
        }

    @api.multi
    def set_default_unique_id_numbers(self):
        for record in self:
            self.env['ir.config_parameter'].set_param(
                "l10n_ar_partner.unique_id_numbers", record.unique_id_numbers)
