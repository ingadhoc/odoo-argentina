# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class afip_ws_currency_rate_wizard(models.TransientModel):
    _name = 'afip.ws.currency_rate.wizard'
    _description = 'AFIP WS Currency Rate Wizard'

    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        required=True,
        )

    @api.multi
    def confirm(self):
        self.ensure_one()
        point_of_sale_id = self._context.get('active_id', False)
        if not point_of_sale_id:
            raise Warning(_(
                'No Point Of sale as active_id on context'))
        point_of_sale = self.env[
            'afip.point_of_sale'].browse(point_of_sale_id)
        return point_of_sale.get_pyafipws_currency_rate(self.currency_id)
