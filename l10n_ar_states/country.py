# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class country_state(models.Model):
    _inherit = 'res.country.state'

    afip_code = fields.Char(
        'AFIP code',
        help='Codigo oficial del AFIP.'
    )
