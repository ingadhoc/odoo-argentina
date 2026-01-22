# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class L10nLatamIdentificationType(models.Model):
    _inherit = "l10n_latam.identification.type"

    @api.depends("country_id")
    def _compute_display_name(self):
        super()._compute_display_name()
        # Personalizar la visualización específicamente para SIGD para que sea más claro
        sigd_records = self.filtered(lambda r: r.name and r.name.upper() == "SIGD")
        for rec in sigd_records:
            # Cambiar el nombre a algo más descriptivo en el dropdown
            rec.display_name = "Sin Identificar"
