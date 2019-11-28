##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    afip_code = fields.Char(
        'Afip Code',
        size=3,
    )
    cuit_fisica = fields.Char(
        'CUIT persona fisica',
        size=11,
    )
    cuit_juridica = fields.Char(
        'CUIT persona juridica',
        size=11,
    )
    cuit_otro = fields.Char(
        'CUIT otro',
        size=11,
    )
