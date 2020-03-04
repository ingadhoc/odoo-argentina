##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    gross_income_jurisdiction_ids = fields.Many2many(
        related='partner_id.gross_income_jurisdiction_ids',
        readonly=False,
    )

    arba_cit = fields.Char(
        'CIT ARBA',
        help='Clave de Identificación Tributaria de ARBA',
    )
