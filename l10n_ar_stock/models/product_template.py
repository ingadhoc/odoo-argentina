##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    arba_code = fields.Char(
    )

    @api.constrains('arba_code')
    def check_arba_code(self):
        for rec in self.filtered('arba_code'):
            if len(rec.arba_code) != 6 or not rec.arba_code.isdigit():
                raise ValidationError(_(
                    'El código según nomenclador de arba debe ser de 6 dígitos'
                    ' numéricos'))
