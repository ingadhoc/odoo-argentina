##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    qr_code_label = fields.Char(
        string="QR Code Label", help="String to display before the QR Code on the invoice report."
    )
    qr_code = fields.Char(
        string="QR Code", help="String to generate the QR Code that will be displayed on the invoice report."
    )
    discriminate_taxes = fields.Selection(
        [("yes", "Yes"), ("no", "No"), ("according_to_partner", "According to partner VAT responsibility")],
        string="Discriminate taxes?",
        default="no",
        required=True,
    )
    l10n_ar_afip_pos_partner_id = fields.Many2one(string="Dirección Punto de venta")

    def _get_l10n_ar_afip_pos_types_selection(self):
        """Add new AFIP Pos type"""
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.append(("CF", _("External Fiscal Controller")))
        return res

    def _get_codes_per_journal_type(self, afip_pos_system):
        """Add filter for External Fiscal Controller
        NOTE: This can be removed in version 18.0 since has been already included in Odoo"""
        tique_codes = ["81", "82", "83", "110", "112", "113", "115", "116", "118", "119", "120"]
        if afip_pos_system == "CF":
            return [("code", "in", tique_codes)]
        res = super()._get_codes_per_journal_type(afip_pos_system)
        if res and isinstance(res, list):
            filtered_res = []
            for term in res:
                if (
                    isinstance(term, tuple)
                    and len(term) == 3
                    and term[0] == "code"
                    and term[1] == "in"
                    and isinstance(term[2], (list, tuple, set))
                ):
                    codes = [code for code in term[2] if code not in {"80", "83"}]
                    filtered_res.append(("code", "in", codes))
                else:
                    filtered_res.append(term)
            res = filtered_res
        return res
