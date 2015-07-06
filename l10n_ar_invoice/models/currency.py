# -*- coding: utf-8 -*-
from openerp import fields, models


class res_currency(models.Model):
    _inherit = "res.currency"
    afip_code = fields.Char(
        'AFIP Code', size=4
        )
