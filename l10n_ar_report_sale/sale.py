# -*- coding: utf-8 -*-
from openerp import osv, models, fields, api, _
from openerp.osv import fields as old_fields
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

class sale_order_line(models.Model):
    """
    """

    _inherit = "sale.order.line"
    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}

        for line in self.browse(cr, uid, ids, context=context):
            discount = line.discount
            res[line.id] = {
                'price_net': line.price_unit * (1-(discount or 0.0)/100.0),
            }
        return res

    _columns = {
        'price_net': old_fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Net Price', multi='printed'),
    }    