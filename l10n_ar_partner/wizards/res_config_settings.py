##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api
from odoo.tools.safe_eval import safe_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_multiple_id_numbers = fields.Boolean(
        "Allow Multiple Id Numbers on Partners",
        help="If you allow multiple Id Numbers, then a new tab for 'Id "
        "NUmbers' will be added on partner form view",
        implied_group='l10n_ar_partner.group_multiple_id_numbers',
    )
    unique_id_numbers = fields.Boolean(
        "Restrict Id Numbers to be Unique",
        help="If you set it True, then we will check that partner Id Numbers "
        "(for eg. cuit, dni, etc) are unique. Same number for partners in a "
        "child/parent relation are still allowed",
    )

    @api.multi
    def set_default_unique_id_numbers(self):
        for record in self:
            self.env['ir.config_parameter'].set_param(
                "l10n_ar_partner.unique_id_numbers", record.unique_id_numbers)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        unique_id_numbers = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_ar_partner.unique_id_numbers')
        res.update(
            default_unique_id_numbers=unique_id_numbers,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_ar_partner.unique_id_numbers', self.unique_id_numbers)
