# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class product_uom(models.Model):
    _inherit = 'product.uom'

    afip_code = fields.Char(
        'Afip Code'
        )
