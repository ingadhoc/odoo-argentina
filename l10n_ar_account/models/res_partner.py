# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iibb = fields.Char(
        'Gross Income',
        size=64
        )
    start_date = fields.Date(
        'Start-up Date'
        )
    afip_responsible_type_id = fields.Many2one(
        'afip.responsible.type',
        'AFIP Responsible Type',
        )
