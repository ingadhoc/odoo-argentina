# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class afip_country(models.Model):
    _inherit = 'res.country'

    afip_code = fields.Char(
        'Afip Code', size=3
        )
    cuit_fisica = fields.Char(
        'CUIT persona fisica', size=11
        )
    cuit_juridica = fields.Char(
        'CUIT persona juridica', size=11
        )
    cuit_otro = fields.Char(
        'CUIT otro', size=11)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
