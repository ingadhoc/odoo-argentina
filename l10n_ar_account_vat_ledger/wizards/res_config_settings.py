##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    iva_control_presentation = fields.Boolean(
        "Control de presentación de Libro IVA",
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].set_param
        set_param('l10n_ar_vat_ledger.require_file_and_page',
                  repr(self.iva_control_presentation))

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            iva_control_presentation=literal_eval(get_param(
                'l10n_ar_vat_ledger.require_file_and_page', default='False')))
        return res
