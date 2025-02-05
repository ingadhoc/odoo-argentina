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
    l10n_ar_partner_tax_ids = fields.One2many(domain=[("tax_id.l10n_ar_withholding_payment_type", "=", "supplier")])
    l10n_ar_partner_perception_ids = fields.One2many(
        "l10n_ar.partner.tax",
        "partner_id",
        "Argentinean Perception Taxes",
        domain=[("tax_id.type_tax_use", "=", "sale")],
    )
