# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'type': fields.selection(
            [('adjust', 'Adjust concept'), ('consu', 'Consumable'),
             ('service', 'Service')], 'Product Type',
            required=True,
            help="Adjust concept are items to be incremented in the client account by invoice errors, interest or other reasons, consumable are product where you don't manage stock, a service is a non-material product provided by a company or an individual."),
    }
