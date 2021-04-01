from odoo import models, fields, api
# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # TODO ver si queremosimplementar esto o no
    # _afip_ws_selection = (
    #     lambda self, *args, **kwargs: self.env[
    #         'account.journal']._get_afip_ws_selection(*args, **kwargs))

    # afip_ws = fields.Selection(
    #     _afip_ws_selection,
    #     'AFIP WS',
    # )
    # @api.multi
    # def set_chart_of_accounts(self):
    #     """
    #     We send this value in context because to use them on journal creation
    #     """
    #     return super(AccountConfigSettings, self.with_context(
    #         afip_ws=self.afip_ws,
    #     )).set_chart_of_accounts()

    afip_auth_verify_type = fields.Selection(
        related='company_id.afip_auth_verify_type',
        readonly=False,
    )

    l10n_ar_afip_fce_transmission = fields.Selection(
        [('SCA', 'SCA - TRANSFERENCIA AL SISTEMA DE CIRCULACION ABIERTA'),
         ('ADC', 'ADC - AGENTE DE DEPOSITO COLECTIVO')],
        'FCE: Opción de Transmisión',
        help="Este campo sera necesario cuando informes comprobantes del tipo FCE MiPyME")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            l10n_ar_afip_fce_transmission=get_param('l10n_ar_edi.fce_transmission', ''),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('l10n_ar_edi.fce_transmission', self.l10n_ar_afip_fce_transmission)
