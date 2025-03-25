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

        # agregado de jurisdiccion a percepciones
        tax_state_tupples = [
            ("ri_tax_percepcion_iibb_caba_sufrida", "base.state_ar_c"),
            ("ri_tax_percepcion_iibb_ba_sufrida", "base.state_ar_b"),
            ("ri_tax_percepcion_iibb_co_sufrida", "base.state_ar_x"),
            ("ri_tax_percepcion_iibb_sf_sufrida", "base.state_ar_s"),
            ("ri_tax_percepcion_iibb_ca_sufrida", "base.state_ar_k"),
            ("ri_tax_percepcion_iibb_rr_sufrida", "base.state_ar_w"),
            ("ri_tax_percepcion_iibb_er_sufrida", "base.state_ar_e"),
            ("ri_tax_percepcion_iibb_ju_sufrida", "base.state_ar_y"),
            ("ri_tax_percepcion_iibb_za_sufrida", "base.state_ar_m"),
            ("ri_tax_percepcion_iibb_lr_sufrida", "base.state_ar_f"),
            ("ri_tax_percepcion_iibb_sa_sufrida", "base.state_ar_a"),
            ("ri_tax_percepcion_iibb_nn_sufrida", "base.state_ar_j"),
            ("ri_tax_percepcion_iibb_sl_sufrida", "base.state_ar_d"),
            ("ri_tax_percepcion_iibb_se_sufrida", "base.state_ar_g"),
            ("ri_tax_percepcion_iibb_tn_sufrida", "base.state_ar_t"),
            ("ri_tax_percepcion_iibb_ha_sufrida", "base.state_ar_h"),
            ("ri_tax_percepcion_iibb_ct_sufrida", "base.state_ar_u"),
            ("ri_tax_percepcion_iibb_fo_sufrida", "base.state_ar_p"),
            ("ri_tax_percepcion_iibb_mi_sufrida", "base.state_ar_n"),
            ("ri_tax_percepcion_iibb_ne_sufrida", "base.state_ar_q"),
            ("ri_tax_percepcion_iibb_lp_sufrida", "base.state_ar_l"),
            ("ri_tax_percepcion_iibb_rn_sufrida", "base.state_ar_r"),
            ("ri_tax_percepcion_iibb_az_sufrida", "base.state_ar_z"),
            ("ri_tax_percepcion_iibb_tf_sufrida", "base.state_ar_v"),
            ("ri_tax_percepcion_iibb_caba_aplicada", "base.state_ar_c"),
            ("ri_tax_percepcion_iibb_ba_aplicada", "base.state_ar_b"),
            ("ri_tax_percepcion_iibb_co_aplicada", "base.state_ar_x"),
            ("ri_tax_percepcion_iibb_sf_aplicada", "base.state_ar_s"),
            ("ri_tax_percepcion_iibb_ca_aplicada", "base.state_ar_k"),
            ("ri_tax_percepcion_iibb_rr_aplicada", "base.state_ar_w"),
            ("ri_tax_percepcion_iibb_er_aplicada", "base.state_ar_e"),
            ("ri_tax_percepcion_iibb_ju_aplicada", "base.state_ar_y"),
            ("ri_tax_percepcion_iibb_za_aplicada", "base.state_ar_m"),
            ("ri_tax_percepcion_iibb_lr_aplicada", "base.state_ar_f"),
            ("ri_tax_percepcion_iibb_sa_aplicada", "base.state_ar_a"),
            ("ri_tax_percepcion_iibb_nn_aplicada", "base.state_ar_j"),
            ("ri_tax_percepcion_iibb_sl_aplicada", "base.state_ar_d"),
            ("ri_tax_percepcion_iibb_se_aplicada", "base.state_ar_g"),
            ("ri_tax_percepcion_iibb_tn_aplicada", "base.state_ar_t"),
            ("ri_tax_percepcion_iibb_ha_aplicada", "base.state_ar_h"),
            ("ri_tax_percepcion_iibb_ct_aplicada", "base.state_ar_u"),
            ("ri_tax_percepcion_iibb_fo_aplicada", "base.state_ar_p"),
            ("ri_tax_percepcion_iibb_mi_aplicada", "base.state_ar_n"),
            ("ri_tax_percepcion_iibb_ne_aplicada", "base.state_ar_q"),
            ("ri_tax_percepcion_iibb_lp_aplicada", "base.state_ar_l"),
            ("ri_tax_percepcion_iibb_rn_aplicada", "base.state_ar_r"),
            ("ri_tax_percepcion_iibb_az_aplicada", "base.state_ar_z"),
            ("ri_tax_percepcion_iibb_tf_aplicada", "base.state_ar_v"),
        ]
        for tax_ref, state_ref in tax_state_tupples:
            # Identificamos el impuesto al que se le va a agregar la/s etiqueta/s
            tax = self.env.ref("account.%s_%s" % (company.id, tax_ref), raise_if_not_found=False)
            if tax:
                tax.l10n_ar_state_id = self.env.ref(state_ref).id

        # creacion de secuencias y agregado de etiquetas para liquidación de impuestos
        withholdings_domain = [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "none"),
            ("country_code", "=", "AR"),
            ("l10n_ar_withholding_payment_type", "=", "supplier"),
        ]
        non_profits_domain = withholdings_domain + [("l10n_ar_tax_type", "not in", ["earnings", "earnings_scale"])]

        for tax in self.env["account.tax"].with_context(active_test=False).search(non_profits_domain):
            sequence = self.env["ir.sequence"].create(
                {
                    "name": tax.invoice_label or tax.name,
                    "prefix": "%(year)s-",
                    "padding": 8,
                    "number_increment": 1,
                    "implementation": "standard",
                    "company_id": company.id,
                }
            )
            tax.l10n_ar_withholding_sequence_id = sequence.id

        profits_domain = withholdings_domain + [("l10n_ar_tax_type", "in", ["earnings", "earnings_scale"])]
        sequence = self.env["ir.sequence"].create(
            {
                "name": "Retención de Ganancias",
                "prefix": "%(year)s-",
                "padding": 8,
                "number_increment": 1,
                "implementation": "standard",
                "company_id": company.id,
            }
        )
        profits_taxes = self.env["account.tax"].with_context(active_test=False).search(profits_domain)
        profits_taxes.l10n_ar_withholding_sequence_id = sequence.id

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
            self.env["account.tax.repartition.line"].search(
                [("tax_id", "in", sicore_taxes.ids), ("repartition_type", "=", "tax")]
            ).tag_ids = [Command.link(tag.id)]

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
                ("tax_id.type_tax_use", "=", "purchase"),
                "&",
                ("tax_id.type_tax_use", "=", "none"),
                ("tax_id.l10n_ar_withholding_payment_type", "=", "customer"),
            ]
            self.env["account.tax.repartition.line"].search(domain).tag_ids = [Command.link(tag.id)]

    def _load(self, template_code, company, install_demo, force_create=True):
        """Luego de que creen los impuestos del archivo account.tax-ar_ri.csv de l10n_ar al instalar el plan de cuentas en la nueva compañìa argentina agregamos en este método las etiquetas que correspondan en los repartition lines."""
        # Llamamos a super para que se creen los impuestos
        res = super()._load(template_code, company, install_demo, force_create)
        company = company or self.env.company
        if company.chart_template in ("ar_ri", "ar_ex", "ar_base"):
            self.sudo()._add_wh_taxes(company)
        return res
