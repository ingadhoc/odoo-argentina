##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class L10nArUxPartnerResponsibility(models.TransientModel):
    _name = "l10n_ar_ux.partner.responsibility"
    _description = "Set the ARCA Responsibility of a contact from an invoice"

    move_id = fields.Many2one("account.move", required=True, ondelete="cascade")
    partner_id = fields.Many2one(related="move_id.commercial_partner_id", string="Contact")
    responsibility_id = fields.Many2one(
        "l10n_ar.afip.responsibility.type",
        string="ARCA Responsibility",
        required=True,
    )

    def action_apply(self):
        self.ensure_one()
        self.partner_id.l10n_ar_afip_responsibility_type_id = self.responsibility_id
        # El dato vive en el contacto, así que Odoo no marca la factura para recalcular: se lo pedimos para
        # esta factura y nada más. Un @api.depends alcanzaría a todas las facturas del contacto, incluidas las
        # posteadas, y ahí salta _check_l10n_latam_documents.
        move = self.move_id
        move.invalidate_recordset(["l10n_latam_available_document_type_ids"])
        move._compute_l10n_latam_document_type()
        return {"type": "ir.actions.act_window_close"}
