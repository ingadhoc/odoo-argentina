from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL


class AccountTax(models.Model):
    _inherit = "account.tax"

    # mejora de usabilidad, duplicar un impuesto mantiene la secuencia
    l10n_ar_withholding_sequence_id = fields.Many2one(
        copy=True,
    )

    @api.model
    @api.readonly
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        """En localización AR, cuando la Posición Fiscal activa **es de
        complemento** (tiene `l10n_ar_tax_ids` — percepciones, retenciones), el
        IVA doméstico debe seguir siendo elegible en el dropdown. Sumamos al
        dominio los taxes `is_domestic=True`.

        Acotado a PFs con `l10n_ar_tax_ids` porque otras PFs AR pueden ser de
        **reemplazo** puro (e.g. mapeo IVA 21% → IVA 10.5% vía `tax_ids` +
        `original_tax_ids`); en esos casos el comportamiento de core Odoo es el
        correcto (excluir el tax doméstico reemplazado) y no debemos
        contaminarlo. `country_id == AR` queda implícito porque
        `l10n_ar_tax_ids` solo existe en contexto AR.

        El widget `many2many_tax_tags` invoca este método (vía `web_name_search`)
        con `dynamic_fiscal_position_id` Y `hide_original_tax_ids` en el context.
        El override aplica también con `hide_original_tax_ids` set — en ese caso
        replicamos la rama `replacing_tax_ids` del core (`addons/account/models/
        account_tax.py:264-275`) sobre el dominio extendido, y sacamos
        `dynamic_fiscal_position_id` para que el super no AND-ee con la condición
        restrictiva `fiscal_position_ids in (False, fp_id)` que excluye el IVA
        doméstico.
        """
        fp_id = self.env.context.get("dynamic_fiscal_position_id")
        if fp_id:
            fp = self.env["account.fiscal.position"].browse(int(fp_id))
            if fp.l10n_ar_tax_ids and fp != fp.company_id.domestic_fiscal_position_id:
                # is_domestic=True ya cubre los taxes sin fiscal_position_ids
                # (is_domestic computa `not tax.fiscal_position_ids → True`).
                # El segundo OR captura taxes que pertenecen explícitamente a
                # la PF activa.
                domain = Domain(domain or Domain.TRUE) & (
                    Domain("is_domestic", "=", True) | Domain("fiscal_position_ids", "=", int(fp_id))
                )
                # Replicamos la rama `hide_original_tax_ids` del core sobre el
                # dominio extendido. Sin esto, los taxes que fueron reemplazados
                # por otro (`replacing_tax_ids`) aparecerían en el dropdown.
                if self.env.context.get("hide_original_tax_ids"):
                    domain &= Domain("replacing_tax_ids", "not any", domain) | Domain.custom(
                        to_sql=lambda model, alias, query: SQL(
                            "EXISTS (SELECT 1 FROM %s WHERE %s = %s AND %s = %s)",
                            SQL.identifier("account_tax_alternatives"),
                            SQL.identifier("src_tax_id"),
                            SQL.identifier(alias, "id"),
                            SQL.identifier("dest_tax_id"),
                            SQL.identifier(alias, "id"),
                        ),
                    )
                # Saltear ambas keys en super para no re-aplicar el filtro
                # restrictivo del core.
                return super(
                    AccountTax,
                    self.with_context(dynamic_fiscal_position_id=None, hide_original_tax_ids=False),
                ).name_search(name, domain, operator, limit)
        return super().name_search(name, domain, operator, limit)

    company_currency_id = fields.Many2one(related="company_id.currency_id")

    # Override Float → Monetary para expresar umbrales en moneda de la compañía
    l10n_ar_non_taxable_amount = fields.Monetary(
        currency_field="company_currency_id",
        string="Non Taxable Amount",
        help="Until this base amount, the tax is not applied.",
    )
    l10n_ar_minimum_threshold = fields.Monetary(
        currency_field="company_currency_id",
        string="Minimum Threshold",
        help="If the calculated withholding/perception amount is lower than this threshold, it is 0.0.",
    )

    # Nuevos umbrales
    l10n_ar_payment_minimum_threshold = fields.Monetary(
        currency_field="company_currency_id",
        string="Minimum Payment",
        help="If the amount of each payment does not exceed this value, the withholding/perception is not applied.",
    )
    l10n_ar_base_minimum_threshold = fields.Monetary(
        currency_field="company_currency_id",
        string="Minimum Base",
        help="If the computed base for the regime does not exceed this value, the withholding/perception is not applied.",
    )
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
    ratio = fields.Float(default=100.00, help="Ratio to apply to tax base amount.")
    l10n_ar_code = fields.Char(string="Código")

    @api.ondelete(at_uninstall=False)
    def _check_tax_used_on_company_tax_fp(self):
        ws = self.env["account.fiscal.position.l10n_ar_tax"].search([("default_tax_id", "in", self.ids)])
        if ws:
            raise UserError(
                "Error se esta usando en ws de estas cias %s" % ws.mapped("fiscal_position_id.company_id.name")
            )

    @api.constrains("ratio")
    def _check_line_ids_percent(self):
        """Check that the total percent is not bigger than 100.0"""
        for tax in self:
            if not tax.ratio or tax.ratio <= 0.0 or tax.ratio > 100.0:
                raise ValidationError(
                    self.env._(
                        "The total percentage (%s) should be greater than 0 and less than or equal to 100.", tax.ratio
                    )
                )

    def _l10n_ar_is_perception_with_base_threshold(self):
        """Percepción de venta argentina con umbral de base mínima configurado.

        Se identifica la percepción de IVA por el código de tributo ARCA del
        grupo de impuestos (06 IVA). Para cubrir las percepciones que
        son provinciales debe tener establecido l10n_ar_state_id.

        Solo se contempla el cálculo por porcentaje (`percent`), que es como se definen
        las percepciones argentinas. Quedan afuera los impuestos incluidos en el precio
        (`price_include`) y los que afectan la base de los impuestos siguientes
        (`include_base_amount`): en ambos casos anular el importe después de que el core
        calculó el resto dejaría inconsistentes el neto o las bases posteriores.
        """
        self.ensure_one()
        return bool(
            self.country_code == "AR"
            and self.type_tax_use == "sale"
            and self.l10n_ar_base_minimum_threshold
            and self.amount_type == "percent"
            and not self.price_include
            and not self.include_base_amount
            and (self.l10n_ar_state_id or self.tax_group_id.l10n_ar_tribute_afip_code == "06")
        )

    @api.model
    def _add_tax_details_in_base_lines(self, base_lines, company):
        """Aplicar el umbral de base mínima de las percepciones de venta argentinas.

        Se hace acá (y no en `_get_tax_details`, que trabaja de a una línea por vez) porque
        el umbral se evalúa **por documento y por impuesto**: se suman las bases de todas
        las líneas que llevan la percepción y recién ahí se compara contra el umbral.
        """
        res = super()._add_tax_details_in_base_lines(base_lines, company)
        self._l10n_ar_apply_perception_base_threshold(base_lines, company)
        return res

    @api.model
    def _l10n_ar_apply_perception_base_threshold(self, base_lines, company):
        """Poner en 0 las percepciones de venta cuya base agregada no supera el umbral.

        :param base_lines: líneas base de UN documento, ya con `tax_details` calculado.
        :param company:    compañía dueña de las líneas base.
        """
        # `account_fiscal_country_id` es el campo canónico para impuestos; se contempla
        # `country_id` por si la compañía todavía no tiene país fiscal configurado.
        if "AR" not in (company.account_fiscal_country_id.code, company.country_id.code):
            return

        # Base acumulada por impuesto, en moneda de la compañía (`raw_base_amount`).
        # `is_eligible` cachea la evaluación para no repetirla por cada línea del documento.
        base_per_tax = {}
        is_eligible = {}
        for base_line in base_lines:
            for tax_data in base_line["tax_details"]["taxes_data"]:
                tax = tax_data["tax"]
                if tax not in is_eligible:
                    is_eligible[tax] = tax._l10n_ar_is_perception_with_base_threshold()
                if is_eligible[tax]:
                    base_per_tax[tax] = base_per_tax.get(tax, 0.0) + tax_data["raw_base_amount"]

        # Solo se evalúa el umbral cuando la base agregada es positiva. Una base negativa
        # significa que estas líneas no son un comprobante sino un fragmento aislado —
        # típicamente las líneas de un descuento global, que el core calcula por separado
        # (`_prepare_global_discount_lines`) antes de sumarlas al documento. Anular la
        # percepción ahí aumentaría el impuesto en vez de reducirlo, y encima quedaría
        # congelada en `manual_tax_amounts`.
        excluded_taxes = {
            tax
            for tax, base_amount in base_per_tax.items()
            if company.currency_id.compare_amounts(base_amount, 0.0) > 0
            and company.currency_id.compare_amounts(base_amount, tax.l10n_ar_base_minimum_threshold) <= 0
        }
        if not excluded_taxes:
            return

        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            for tax_data in tax_details["taxes_data"]:
                if tax_data["tax"] not in excluded_taxes:
                    continue
                tax_details["raw_total_included_currency"] -= tax_data["raw_tax_amount_currency"]
                tax_details["raw_total_included"] -= tax_data["raw_tax_amount"]
                for key in (
                    "base_amount",
                    "tax_amount",
                    "raw_base_amount",
                    "raw_base_amount_currency",
                    "raw_tax_amount",
                    "raw_tax_amount_currency",
                ):
                    tax_data[key] = 0.0
