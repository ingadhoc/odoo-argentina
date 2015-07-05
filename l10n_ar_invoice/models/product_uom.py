# -*- coding: utf-8 -*-
from openerp import fields, models


class product_uom(models.Model):
    _inherit = 'product.uom'

    afip_code = fields.Char(
        'Afip Code'
        )
