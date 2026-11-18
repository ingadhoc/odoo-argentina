import re

from odoo import _, fields, models
from odoo.exceptions import UserError


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

    def write(self, vals):
        if "vat" not in vals:
            return super().write(vals)
        old_digits = {partner.id: re.sub(r"\D", "", partner.vat or "") for partner in self}
        res = super().write(vals)
        changed = self.filtered(lambda p: old_digits[p.id] and old_digits[p.id] != re.sub(r"\D", "", p.vat or ""))
        if changed:
            changed._l10n_ar_check_vat_change_with_partner_taxes()
        return res

    def _l10n_ar_check_vat_change_with_partner_taxes(self):
        """Block a change of the identification number when the partner already has tax aliquots.

        The aliquots (padron, webservice or manual) belong to the old number: keeping them with a new one
        would apply and report the aliquots of another taxpayer. It runs after the write, so the aliquots can be
        deleted in the same save. Same digits with another format is allowed.
        """
        partner_taxes = (
            self.env["l10n_ar.partner.tax"].sudo().search([("partner_id", "in", self.commercial_partner_id.ids)])
        )
        if partner_taxes:
            raise UserError(
                _(
                    "You can't change the identification number of %(partners)s because it has tax aliquots "
                    "for the current number. Delete its aliquots first and then change the number.",
                    partners=", ".join(partner_taxes.partner_id.mapped("display_name")),
                )
            )
