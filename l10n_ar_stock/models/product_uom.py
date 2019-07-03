##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProductUom(models.Model):
    _inherit = 'uom.uom'

    arba_code = fields.Char(
    )
