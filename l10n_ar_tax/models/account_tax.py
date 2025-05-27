from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ar_tribute_afip_code = fields.Selection(related="tax_group_id.l10n_ar_tribute_afip_code")
    l10n_ar_state_code = fields.Char(related="l10n_ar_state_id.code")
    api_codigo_articulo_retencion = fields.Char(
        string="Código de Artículo/Inciso por el que retiene",
        size=3,
    )
    api_codigo_articulo_percepcion = fields.Char(
        string="Código de artículo Inciso por el que percibe",
        size=3,
    )
    api_articulo_inciso_calculo_percepcion = fields.Char(string="Artículo/Inciso para el cálculo percepción", size=3)
    api_articulo_inciso_calculo_retencion = fields.Char(string="Artículo/Inciso para el cálculo retención", size=3)

    @api.ondelete(at_uninstall=False)
    def _check_tax_used_on_company_tax_fp(self):
        ws = self.env["account.fiscal.position.l10n_ar_tax"].search([("default_tax_id", "in", self.ids)])
        if ws:
            raise UserError(
                "Error se esta usando en ws de estas cias %s" % ws.mapped("fiscal_position_id.company_id.name")
            )
