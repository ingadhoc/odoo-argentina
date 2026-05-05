from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ar_tax_ids = fields.One2many("account.fiscal.position.l10n_ar_tax", "fiscal_position_id")

    def _l10n_ar_add_taxes(self, partner, company, date, tax_type, payment=None):
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
                partner_tax = fp_tax._get_missing_taxes(partner, date, payment)
            if len(partner_tax) > 1:
                raise RedirectWarning(
                    message=_(
                        "El contacto '%(name)s' (id: %(id)s) tiene múltiples impuestos vigentes para el grupo "
                        "de impuestos '%(tax_group)s' en la fecha '%(date)s' y compañía '%(company)s'. Ver "
                        "solapa 'Contabilidad' de la vista formulario del contacto.",
                        name=partner.name,
                        id=partner.id,
                        tax_group=fp_tax.default_tax_id.tax_group_id.name,
                        date=date,
                        company=company.name,
                    ),
                    action=partner.get_formview_action(),
                    button_text=_("Editar contacto"),
                )
            if partner_tax and partner_tax.l10n_ar_tax_type != "earnings_scale" and partner_tax.amount == 0:
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

    def _get_fpos_validation_functions(self, partner):
        """
        Overrides the `_get_fpos_validation_functions` method to include custom validation
        functions for fiscal positions based on Argentine withholding taxes.
        If the context does not include 'l10n_ar_withholding' or the company's country
        is not Argentina (country code "AR"), the method falls back to the parent class
        implementation.
        When the context includes 'l10n_ar_withholding' and the company's country is
        Argentina, the method adds a validation function that requires fiscal positions
        containing taxes of type 'withholding' (`l10n_ar_tax_ids`).
        For normal fiscal positions in Argentina (not in withholding context), it excludes
        fiscal positions that are only for withholdings (no tax_ids, no account_ids, have
        withholding taxes but no perception taxes).
        Args:
            partner (res.partner): The partner for whom the fiscal position validation
                functions are being determined.
        """
        functions = super()._get_fpos_validation_functions(partner)
        if self.env.context.get("l10n_ar_withholding") and self.env.company.country_id.code == "AR":
            return [
                lambda fpos: any(tax.tax_type == "withholding" for tax in fpos.l10n_ar_tax_ids),
            ] + functions
        elif not self.env.context.get("l10n_ar_withholding") and self.env.company.country_id.code == "AR":
            return [
                lambda fpos: not (
                    not fpos.tax_ids
                    and not fpos.account_ids
                    and any(tax.tax_type == "withholding" for tax in fpos.l10n_ar_tax_ids)
                    and not any(tax.tax_type == "perception" for tax in fpos.l10n_ar_tax_ids)
                ),
            ] + functions
        else:
            return functions

    def map_tax(self, taxes):
        """Map taxes for Argentine fiscal positions that only configure perceptions/withholdings (l10n_ar_tax_ids)
        without any explicit VAT tax mapping (tax_ids).

        In v19 all standard Argentine VAT taxes have fiscal_position_ids pointing to the domestic FP (e.g. "Compras / Ventas al exterior").
        Because of this, taxes.fiscal_position_ids is always truthy for any IVA tax, which causes the
        base map_tax() to remove all taxes when the fiscal position has no tax_ids.

        For perception/withholding-only fiscal positions we return taxes unchanged instead of delegating to
        domestic_FP.map_tax(). Delegating is unsafe because any tax replacement configured on the domestic FP
        (e.g. IVA 0% replacing IVA 21%) would be incorrectly applied to every perc/with-only FP, regardless
        of which one is actually active on the document.

        FPs that do have explicit tax_ids (e.g. foreign or exempt positions with VAT mapping) are
        not affected and always fall through to super().
        """
        if not self.tax_ids and self.l10n_ar_tax_ids and self != self.company_id.domestic_fiscal_position_id:
            return taxes
        return super().map_tax(taxes)
