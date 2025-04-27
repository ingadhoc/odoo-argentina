from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # TODO Borrar? lo estamos usando?
    drei = fields.Selection(
        [
            ("activo", "Activo"),
            ("no_activo", "No Activo"),
        ],
        string="DREI",
    )
