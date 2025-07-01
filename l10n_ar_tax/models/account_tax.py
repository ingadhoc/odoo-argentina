from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ar_tribute_afip_code = fields.Selection(related="tax_group_id.l10n_ar_tribute_afip_code")
    l10n_ar_state_code = fields.Char(related="l10n_ar_state_id.code")
    api_codigo_articulo_retencion = fields.Selection(
        [
            ("001", "001: Art.1 - inciso A - (Res. Gral. 15/97 y Modif.)"),
            ("002", "002: Art.1 - inciso B - (Res. Gral. 15/97 y Modif.)"),
            ("003", "003: Art.1 - inciso C - (Res. Gral. 15/97 y Modif.)"),
            ("004", "004: Art.1 - inciso D pto.1 - (Res. Gral. 15/97 y Modif.)"),
            ("005", "005: Art.1 - inciso D pto.2 - (Res. Gral. 15/97 y Modif.)"),
            ("006", "006: Art.1 - inciso D pto.3 - (Res. Gral. 15/97 y Modif.)"),
            ("007", "007: Art.1 - inciso E - (Res. Gral. 15/97 y Modif.)"),
            ("008", "008: Art.1 - inciso F - (Res. Gral. 15/97 y Modif.)"),
            ("009", "009: Art.1 - inciso H - (Res. Gral. 15/97 y Modif.)"),
            ("010", "010: Art.1 - inciso I - (Res. Gral. 15/97 y Modif.)"),
            ("011", "011: Art.1 - inciso J - (Res. Gral. 15/97 y Modif.)"),
            ("012", "012: Art.1 - inciso K - (Res. Gral. 15/97 y Modif.)"),
            ("013", "013: Art.1 - inciso L - (Res. Gral. 15/97 y Modif.)"),
            ("014", "014: Art.1 - inciso LL pto.1 - (Res. Gral. 15/97 y Modif.)"),
            ("015", "015: Art.1 - inciso LL pto.2 - (Res. Gral. 15/97 y Modif.)"),
            ("016", "016: Art.1 - inciso LL pto.3 - (Res. Gral. 15/97 y Modif.)"),
            ("017", "017: Art.1 - inciso LL pto.4 - (Res. Gral. 15/97 y Modif.)"),
            ("018", "018: Art.1 - inciso LL pto.5 - (Res. Gral. 15/97 y Modif.)"),
            ("019", "019: Art.1 - inciso M - (Res. Gral. 15/97 y Modif.)"),
            ("020", "020: Art.2 - (Res. Gral. 15/97 y Modif.)"),
        ],
        string="Código de Artículo/Inciso por el que retiene",
    )
    api_codigo_articulo_percepcion = fields.Selection(
        [
            ("021", "021: Art.10 - inciso A - (Res. Gral. 15/97 y Modif.)"),
            ("022", "022: Art.10 - inciso B - (Res. Gral. 15/97 y Modif.)"),
            ("023", "023: Art.10 - inciso D - (Res. Gral. 15/97 y Modif.)"),
            ("024", "024: Art.10 - inciso E - (Res. Gral. 15/97 y Modif.)"),
            ("025", "025: Art.10 - inciso F - (Res. Gral. 15/97 y Modif.)"),
            ("026", "026: Art.10 - inciso G - (Res. Gral. 15/97 y Modif.)"),
            ("027", "027: Art.10 - inciso H - (Res. Gral. 15/97 y Modif.)"),
            ("028", "028: Art.10 - inciso I - (Res. Gral. 15/97 y Modif.)"),
            ("029", "029: Art.10 - inciso J - (Res. Gral. 15/97 y Modif.)"),
            ("030", "030: Art.11 - (Res. Gral. 15/97 y Modif.)"),
            ("031", "031: Art.10 - inciso M - (Res. Gral. 15/97 y Modif.)"),
            ("032", "032: Art.11 - (Res. Gral. 15/97 y Modif.)"),
            ("033", "033: Art.125 - inciso H - (Código Fiscal - mera compra)"),
        ],
        string="Código de artículo Inciso por el que percibe",
    )
    api_articulo_inciso_calculo_selection = [
        ("001", "001: Art. 5º 1er. párrafo (Res. Gral. 15/97 y Modif.)"),
        ("002", "002: Art. 5º inciso 1)(Res. Gral. 15/97 y Modif.)"),
        ("003", "003: Art. 5° inciso 2)(Res. Gral. 15/97 y Modif.)"),
        ("004", "004: Art. 5º inciso 4)(Res. Gral. 15/97 y Modif.)"),
        ("005", "005: Art. 5° inciso 5)(Res. Gral. 15/97 y Modif.)"),
        ("006", "006: Art. 6º inciso a)(Res. Gral. 15/97 y Modif.)"),
        ("007", "007: Art. 6º inciso b)(Res. Gral. 15/97 y Modif.)"),
        ("008", "008: Art. 6º inciso c)(Res. Gral. 15/97 y Modif.)"),
        ("009", "009: Art. 12º)(Res. Gral. 15/97 y Modif.)"),
        ("010", "010: Art. 6º inciso d)(Res. Gral. 15/97 y Modif.)"),
        ("011", "011: Art. 5° inciso 6)(Res. Gral. 15/97 y Modif.)"),
        ("012", "012: Art. 5° inciso 3)(Res. Gral. 15/97 y Modif.)"),
        ("013", "013: Art. 5° inciso 7)(Res. Gral. 15/97 y Modif.)"),
        ("014", "014: Art. 5° inciso 8)(Res. Gral. 15/97 y Modif.)"),
        ("015", "015: Art. 10° inciso a - (Res. Gral. 15/97 y Modif.)"),
        ("016", "016: Art. 10° inciso b - (Res. Gral. 15/97 y Modif.)"),
        ("017", "017: Art. 10° inciso d - (Res. Gral. 15/97 y Modif.)"),
        ("018", "018: Art. 10° inciso e - (Res. Gral. 15/97 y Modif.)"),
        ("019", "019: Art. 10° inciso f - (Res. Gral. 15/97 y Modif.)"),
        ("020", "020: Art. 10° inciso g - (Res. Gral. 15/97 y Modif.)"),
        ("021", "021: Art. 10° inciso h - (Res. Gral. 15/97 y Modif.)"),
        ("022", "022: Art. 10° inciso i - (Res. Gral. 15/97 y Modif.)"),
        ("023", "023: Art. 10° inciso j - (Res. Gral. 15/97 y Modif.)"),
        ("024", "024: Art. 10° inciso l - (Res. Gral. 15/97 y Modif.)"),
        ("025", "025: Art. 10° inciso m - (Res. Gral. 15/97 y Modif.)"),
        ("027", "027: Art. 5° inciso 9 - (Res. Gral. 15/97 y Mod.)"),
        ("028", "028: Art. 5° inciso 9 - (Res. Gral. 15/97 y Mod.)"),
        ("029", "029: Art. 5° inciso 9 - (Res. Gral. 15/97 y Mod.)"),
    ]
    api_articulo_inciso_calculo_percepcion = fields.Selection(
        api_articulo_inciso_calculo_selection,
        string="Artículo/Inciso para el cálculo percepción",
    )
    api_articulo_inciso_calculo_retencion = fields.Selection(
        api_articulo_inciso_calculo_selection,
        string="Artículo/Inciso para el cálculo retención",
    )

    @api.ondelete(at_uninstall=False)
    def _check_tax_used_on_company_tax_fp(self):
        ws = self.env["account.fiscal.position.l10n_ar_tax"].search([("default_tax_id", "in", self.ids)])
        if ws:
            raise UserError(
                "Error se esta usando en ws de estas cias %s" % ws.mapped("fiscal_position_id.company_id.name")
            )
