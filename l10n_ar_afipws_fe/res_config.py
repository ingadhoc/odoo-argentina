# -*- coding: utf-8 -*-
from openerp import models, fields, api
# from openerp.exceptions import UserError


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    _afip_ws_selection = (
        lambda self, *args, **kwargs: self.env[
            'account.journal']._get_afip_ws_selection(*args, **kwargs))

    afip_ws = fields.Selection(
        _afip_ws_selection,
        'AFIP WS',
    )

    @api.multi
    def set_chart_of_accounts(self):
        """
        We send this value in context because to use them on journals creation
        """
        return super(AccountConfigSettings, self.with_context(
            afip_ws=self.afip_ws,
        )).set_chart_of_accounts()
