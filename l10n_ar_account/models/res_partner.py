# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gross_income_number = fields.Char(
        'Gross Income Number',
        size=64,
    )
    gross_income_type = fields.Selection([
        ('multilateral', 'Multilateral'),
        ('local', 'Local'),
        ('no_liquida', 'No Liquida'),
    ],
        'Gross Income Type',
    )
    start_date = fields.Date(
        'Start-up Date'
    )
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        'AFIP Responsability Type',
    )
