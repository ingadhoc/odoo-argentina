from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ar_ncm_code = fields.Char('NCM Code', copy=False, help='Code according to the Common Nomenclator of MERCOSUR')
