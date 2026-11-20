##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import Command, api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _add_wh_taxes(self, company):
        """Agregamos etiquetas en repartition lines de impuestos de percepciones de iva, ganancias e ingresos brutos."""
        # TODO deberia ir en odoo nativo
        company.ensure_one()

        # jurisdiccion de percepciones y retenciones de IIBB: va en el grupo y los impuestos la toman de ahi
        tax_group_state_tupples = [
            ("tax_group_percepcion_iibb_caba", "base.state_ar_c"),
            ("tax_group_percepcion_iibb_ba", "base.state_ar_b"),
            ("tax_group_percepcion_iibb_co", "base.state_ar_x"),
            ("tax_group_percepcion_iibb_sf", "base.state_ar_s"),
            ("tax_group_percepcion_iibb_ca", "base.state_ar_k"),
            ("tax_group_percepcion_iibb_rr", "base.state_ar_w"),
            ("tax_group_percepcion_iibb_er", "base.state_ar_e"),
            ("tax_group_percepcion_iibb_ju", "base.state_ar_y"),
            ("tax_group_percepcion_iibb_za", "base.state_ar_m"),
            ("tax_group_percepcion_iibb_lr", "base.state_ar_f"),
            ("tax_group_percepcion_iibb_sa", "base.state_ar_a"),
            ("tax_group_percepcion_iibb_nn", "base.state_ar_j"),
            ("tax_group_percepcion_iibb_sl", "base.state_ar_d"),
            ("tax_group_percepcion_iibb_se", "base.state_ar_g"),
            ("tax_group_percepcion_iibb_tn", "base.state_ar_t"),
            ("tax_group_percepcion_iibb_ha", "base.state_ar_h"),
            ("tax_group_percepcion_iibb_ct", "base.state_ar_u"),
            ("tax_group_percepcion_iibb_fo", "base.state_ar_p"),
            ("tax_group_percepcion_iibb_mi", "base.state_ar_n"),
            ("tax_group_percepcion_iibb_ne", "base.state_ar_q"),
            ("tax_group_percepcion_iibb_lp", "base.state_ar_l"),
            ("tax_group_percepcion_iibb_rn", "base.state_ar_r"),
            ("tax_group_percepcion_iibb_az", "base.state_ar_z"),
            ("tax_group_percepcion_iibb_tf", "base.state_ar_v"),
            ("tax_group_withholding_iibb_caba", "base.state_ar_c"),
            ("tax_group_withholding_iibb_ba", "base.state_ar_b"),
            ("tax_group_withholding_iibb_c", "base.state_ar_k"),
            ("tax_group_withholding_iibb_cba", "base.state_ar_x"),
            ("tax_group_withholding_iibb_cts", "base.state_ar_w"),
            ("tax_group_withholding_iibb_er", "base.state_ar_e"),
            ("tax_group_withholding_iibb_j", "base.state_ar_y"),
            ("tax_group_withholding_iibb_mza", "base.state_ar_m"),
            ("tax_group_withholding_iibb_lr", "base.state_ar_f"),
            ("tax_group_withholding_iibb_s", "base.state_ar_a"),
            ("tax_group_withholding_iibb_sj", "base.state_ar_j"),
            ("tax_group_withholding_iibb_sl", "base.state_ar_d"),
            ("tax_group_withholding_iibb_sf", "base.state_ar_s"),
            ("tax_group_withholding_iibb_se", "base.state_ar_g"),
            ("tax_group_withholding_iibb_t", "base.state_ar_t"),
            ("tax_group_withholding_iibb_cho", "base.state_ar_h"),
            ("tax_group_withholding_iibb_cht", "base.state_ar_u"),
            ("tax_group_withholding_iibb_f", "base.state_ar_p"),
            ("tax_group_withholding_iibb_ms", "base.state_ar_n"),
            ("tax_group_withholding_iibb_n", "base.state_ar_q"),
            ("tax_group_withholding_iibb_lp", "base.state_ar_l"),
            ("tax_group_withholding_iibb_rn", "base.state_ar_r"),
            ("tax_group_withholding_iibb_sc", "base.state_ar_z"),
            ("tax_group_withholding_iibb_tais", "base.state_ar_v"),
        ]
        for tax_group_ref, state_ref in tax_group_state_tupples:
            tax_group = self.env.ref("account.%s_%s" % (company.id, tax_group_ref), raise_if_not_found=False)
            if tax_group and not tax_group.l10n_ar_state_id:
                tax_group.l10n_ar_state_id = self.env.ref(state_ref).id

        # secuencias de retenciones a proveedor: una por grupo, la toman sus impuestos
        withholdings_domain = [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "purchase"),
            ("is_withholding_tax", "=", True),
            ("country_code", "=", "AR"),
        ]
        non_profits_domain = withholdings_domain + [
            ("l10n_ar_withholding_tax_type", "not in", ["earnings", "earnings_scale"])
        ]
        non_profits_taxes = self.env["account.tax"].with_context(active_test=False).search(non_profits_domain)
        for tax_group in non_profits_taxes.tax_group_id.filtered(lambda group: not group.withholding_sequence_id):
            tax_group.withholding_sequence_id = self.env["ir.sequence"].create(
                {
                    "name": tax_group.name,
                    "prefix": "%(year)s-",
                    "padding": 8,
                    "number_increment": 1,
                    "implementation": "standard",
                    "company_id": company.id,
                }
            )

        profits_domain = withholdings_domain + [("l10n_ar_withholding_tax_type", "in", ["earnings", "earnings_scale"])]
        profits_taxes = self.env["account.tax"].with_context(active_test=False).search(profits_domain)
        # Todos los impuestos de retención de ganancias comparten la secuencia de su grupo
        for tax_group in profits_taxes.tax_group_id.filtered(lambda group: not group.withholding_sequence_id):
            tax_group.withholding_sequence_id = self.env["ir.sequence"].create(
                {
                    "name": "Retención de Ganancias",
                    "prefix": "%(year)s-",
                    "padding": 8,
                    "number_increment": 1,
                    "implementation": "standard",
                    "company_id": company.id,
                }
            )

        # agregado de etiquetas para liquidacion de impuestos sicore
        sicore_taxes = profits_taxes
        tag = self.env.ref("l10n_ar_ux.tag_ret_perc_sicore_aplicada", raise_if_not_found=False)
        if tag:
            for xml_id in ["ri_tax_percepcion_iva_aplicada", "ri_tax_percepcion_ganancias_aplicada"]:
                xml_id_percep = "account.%s_%s" % (company.id, xml_id)
                # en profits_taxes tenemos todas las retenciones, agregamos el impuesto de percepcion de ganancias y de iva
                tax = self.env.ref(xml_id_percep, raise_if_not_found=False)
                if tax:
                    sicore_taxes += tax
            sicore_tags = self.env["account.tax.repartition.line"].search(
                [("tax_id", "in", sicore_taxes.ids), ("repartition_type", "=", "tax")]
            )
            sicore_tags_to_update = sicore_tags.filtered(lambda line: tag not in line.tag_ids)
            sicore_tags_to_update.tag_ids = [Command.link(tag.id)]

        # agregado de etiquetas para liquidacion de impuestos pago IIBB a cuenta (sifere web)
        # consideramos de IIBB a todo lo que tiene 10n_ar_state_id
        tag = self.env.ref("l10n_ar_ux.tax_tag_a_cuenta_iibb", raise_if_not_found=False)
        if tag:
            domain = [
                ("repartition_type", "=", "tax"),
                ("tax_id.company_id", "=", company.id),
                ("tax_id.l10n_ar_state_id", "!=", False),
                ("tax_id.country_code", "=", "AR"),
                "|",
                "&",
                ("tax_id.type_tax_use", "=", "purchase"),
                ("tax_id.is_withholding_tax", "=", False),
                "&",
                ("tax_id.type_tax_use", "=", "sale"),
                ("tax_id.is_withholding_tax", "=", True),
            ]
            repartition_lines = self.env["account.tax.repartition.line"].search(domain)
            if repartition_lines_without_tag := repartition_lines.filtered(lambda line: tag not in line.tag_ids):
                repartition_lines_without_tag.tag_ids = [Command.link(tag.id)]

    def _load(self, template_code, company, install_demo, force_create=True):
        """Luego de que creen los impuestos del archivo account.tax-ar_ri.csv de l10n_ar al instalar el plan de cuentas en la nueva compañìa argentina agregamos en este método las etiquetas que correspondan en los repartition lines."""
        # Llamamos a super para que se creen los impuestos
        res = super()._load(template_code, company, install_demo, force_create)
        company = company or self.env.company
        if company.chart_template in ("ar_ri", "ar_ex", "ar_base"):
            self.sudo()._add_wh_taxes(company)
        return res
