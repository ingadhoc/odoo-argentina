# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    afip_code = fields.Char(
        'AFIP Code', size=4
    )
