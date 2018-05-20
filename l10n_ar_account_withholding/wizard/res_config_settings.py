from odoo import models, fields
# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    arba_cit = fields.Char(
        related='company_id.arba_cit'
    )
    regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids'
    )
