##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class country_state(models.Model):
    _inherit = 'res.country.state'

    afip_code = fields.Char(
        'AFIP code',
        help='Codigo oficial del AFIP.'
    )
