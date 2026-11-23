##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, fields, models

# Esto es la primera modificacion para el ejercicio

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
        """Add new ARCA Pos type"""
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.append(("CF", _("External Fiscal Controller")))
        return res

    def _get_codes_per_journal_type(self, afip_pos_system):
        """Add support for External Fiscal Controller (CF) and fix document availability
        for manual journals without AFIP POS system."""
        tique_codes = ["81", "82", "83", "110", "112", "113", "115", "116", "118", "119", "120"]
        if afip_pos_system == "CF":
            return [("code", "in", tique_codes)]
        # Diarios de venta que usan documentos pero no tienen sistema AFIP POS configurado
        # (ej: cuenta y orden). El _compute_l10n_ar_is_pos los marca como is_pos=True,
        # lo cual vacía la lista de códigos. Los tratamos como no-POS para que accedan
        # a los mismos comprobantes que un diario de venta manual.
        if self.type == "sale" and self.l10n_ar_is_pos and not afip_pos_system:
            no_pos_docs = [
                "23",
                "24",
                "25",
                "26",
                "27",
                "28",
                "33",
                "43",
                "45",
                "46",
                "48",
                "58",
                "60",
                "61",
                "150",
                "151",
                "157",
                "158",
                "161",
                "162",
                "164",
                "166",
                "167",
                "171",
                "172",
                "180",
                "182",
                "186",
                "188",
                "332",
            ]
            lsg_codes = ["331"]
            return [("code", "in", no_pos_docs + lsg_codes)]
        # Diarios de compra sin sistema AFIP POS. Odoo aplica [('code', 'not in', no_pos_docs)]
        # que excluye el código 60 y similares.
        # Antes de que se agregara _get_journal_codes_domain no había restricción por código,
        # por lo que todos los tipos de comprobante eran accesibles. Restauramos ese comportamiento.
        if self.type == "purchase" and not afip_pos_system:
            return []
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
