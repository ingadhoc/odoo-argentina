from odoo import models, fields
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
        related='company_id.afip_auth_verify_type'
    )
