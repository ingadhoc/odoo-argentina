from odoo import models, fields
# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids'
    )
    agip_padron_type = fields.Selection(
        related='company_id.agip_padron_type'
    )
