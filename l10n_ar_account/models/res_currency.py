##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    afip_code = fields.Char(
        'AFIP Code',
        size=4,
    )
