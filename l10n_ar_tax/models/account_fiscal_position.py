from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ar_tax_ids = fields.One2many("account.fiscal.position.l10n_ar_tax", "fiscal_position_id")

    def _l10n_ar_add_taxes(self, partner, company, date, tax_type):
        # TODO deberiamos unificar mucho de este codigo con _get_tax_domain, _compute_withholdings y _check_tax_group_overlap
        self.ensure_one()
        taxes = self.env["account.tax"]
        # garantizamos de siempre evaluar segun commercial partner que es donde se guardan y ven los impuestos
        partner = partner.commercial_partner_id
        for fp_tax in self.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == tax_type):
            domain = self.env["l10n_ar.partner.tax"]._check_company_domain(company)
            domain += [("tax_id.tax_group_id", "=", fp_tax.default_tax_id.tax_group_id.id)]
            if tax_type == "withholding":
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [("tax_id.l10n_ar_state_id", "=", fp_tax.default_tax_id.l10n_ar_state_id.id)]
            domain += [
                "|",
                ("from_date", "<=", date),
                ("from_date", "=", False),
                "|",
                ("to_date", ">=", date),
                ("to_date", "=", False),
            ]
            if tax_type == "perception":
                partner_tax = partner.l10n_ar_partner_perception_ids.filtered_domain(domain).mapped("tax_id")
            elif tax_type == "withholding":
                partner_tax = partner.l10n_ar_partner_tax_ids.filtered_domain(domain).mapped("tax_id")
            # agregamos taxes para grupos de impuestos que no estaban seteados en el partner
            if not partner_tax:
                partner_tax = fp_tax._get_missing_taxes(partner, date)
            if partner_tax.l10n_ar_tax_type != "earnings_scale" and partner_tax.amount == 0:
                # se eliminan todos los impuestos cuyo monto sea 0, excepto los de tipo "earnings_scale"
                continue
            taxes |= partner_tax
        return taxes

    @api.constrains("l10n_ar_tax_ids")
    def _check_tax_type(self):
        """Aquellas retenciones/percepciones en la posición fiscal que tengan un impuesto por defecto de retención
        entonces deberán tener tipo 'retención' y si son de percepción entonces deberán tener tipo 'percepcion'."""
        if wrong_tax_type_records := self.l10n_ar_tax_ids.filtered(
            lambda x: x.tax_type == "withholding"
            and x.default_tax_id.type_tax_use != "none"
            or x.tax_type == "perception"
            and x.default_tax_id.type_tax_use == "none"
        ):
            raise ValidationError(
                self.env._(
                    "Perceptions/Withholdings with wrong document type %s."
                    % ", ".join(wrong_tax_type_records.default_tax_id.mapped("name"))
                )
            )

    def _get_fpos_ranking_functions(self, partner):
        """
        Overrides the `_get_fpos_ranking_functions` method to include a custom ranking
        function for fiscal positions based on Argentine withholding taxes.
        If the context does not include 'l10n_ar_withholding' or the company's country
        is not Argentina (country code "AR"), the method falls back to the parent class
        implementation.
        When the context includes 'l10n_ar_withholding' and the company's country is
        Argentina, the method adds a ranking function that prioritizes fiscal positions
        containing taxes of type 'withholding' (`l10n_ar_tax_ids`).
        Args:
            partner (res.partner): The partner for whom the fiscal position ranking
                functions are being determined.
        """
        if not self._context.get("l10n_ar_withholding") or self.env.company.country_id.code != "AR":
            return super()._get_fpos_ranking_functions(partner)
        return [
            ("l10n_ar_tax_ids", lambda fpos: (any(tax.tax_type == "withholding" for tax in fpos.l10n_ar_tax_ids)))
        ] + super()._get_fpos_ranking_functions(partner)
