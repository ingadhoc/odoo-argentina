##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
import re

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
            if tax := self.env.ref("account.%s_%s" % (company.id, tax_ref), raise_if_not_found=False):
                if not tax.l10n_ar_state_id:
                    tax.l10n_ar_state_id = self.env.ref(state_ref).id

        self._add_iibb_withholding_taxes(company)
        self._add_profits_iva_wh_tax_groups(company)

        # creacion de secuencias y agregado de etiquetas para liquidación de impuestos
        withholdings_domain = [
            ("company_id", "=", company.id),
            ("country_id.code", "=", "AR"),
            ("type_tax_use", "=", "none"),
            ("l10n_ar_withholding_payment_type", "=", "supplier"),
        ]
        non_profits_domain = withholdings_domain + [("l10n_ar_tax_type", "not in", ["earnings", "earnings_scale"])]

        for tax in self.env["account.tax"].with_context(active_test=False).search(non_profits_domain):
            if not tax.l10n_ar_withholding_sequence_id:
                sequence_name = re.sub(r"\s+\d+[,.]?\d*\s*%", "", tax.invoice_label or tax.name).strip()
                sequence = self.env["ir.sequence"].create(
                    {
                        "name": sequence_name,
                        "prefix": "%(year)s-",
                        "padding": 8,
                        "number_increment": 1,
                        "implementation": "standard",
                        "company_id": company.id,
                    }
                )
                tax.l10n_ar_withholding_sequence_id = sequence.id

        profits_domain = withholdings_domain + [("l10n_ar_tax_type", "in", ["earnings", "earnings_scale"])]
        profits_taxes = self.env["account.tax"].with_context(active_test=False).search(profits_domain)
        # Todos los impuestos de retención de ganancias deben compartir la misma secuencia
        if not all(prof_tax.l10n_ar_withholding_sequence_id for prof_tax in profits_taxes):
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
            profits_taxes.filtered(
                lambda tax: not tax.l10n_ar_withholding_sequence_id
            ).l10n_ar_withholding_sequence_id = sequence.id

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
                ("tax_id.country_id.code", "=", "AR"),
                ("tax_id.l10n_ar_state_id", "!=", False),
                "|",
                ("tax_id.type_tax_use", "=", "purchase"),
                "&",
                ("tax_id.type_tax_use", "=", "none"),
                ("tax_id.l10n_ar_withholding_payment_type", "=", "customer"),
            ]
            repartition_lines = self.env["account.tax.repartition.line"].search(domain)
            if repartition_lines_without_tag := repartition_lines.filtered(lambda line: tag not in line.tag_ids):
                repartition_lines_without_tag.tag_ids = [Command.link(tag.id)]

    @api.model
    def _ensure_iibb_wh_tax_groups(self, company):
        """Garantiza que los tax groups de retenciones IIBB existan con ext ID account.{id}_* para la empresa."""
        template_code = company.chart_template
        if not template_code:
            return
        tax_group_data = self._get_chart_template_model_data(template_code, "account.tax.group")
        self.with_company(company.id)._load_data({"account.tax.group": tax_group_data})

    @api.model
    def _add_iibb_withholding_taxes(self, company):
        """Asigna provincia y grupo de impuesto a las retenciones IIBB por provincia (sufridas y aplicadas).

        Ejemplos de identificadores externos para Santiago del Estero (prov=se, company_id=N):

        Retención sufrida (incurred):
          v16: l10n_ar_account_withholding.N_ri_tax_retencion_iibb_se_sufrida
          v17: account.N_ri_tax_withholding_iibb_se_incurred
          v18: account.N_base_tax_withholding_iibb_se_incurred
          v19: account.N_base_tax_withholding_iibb_se_incurred

        Retención aplicada (applied):
          v16: l10n_ar_account_withholding.N_ri_tax_retencion_iibb_se_aplicada
          v17: account.N_ri_tax_withholding_iibb_se_applied
          v18: account.N_ex_tax_withholding_iibb_se_applied
          v19: account.N_ex_tax_withholding_iibb_se_applied

        Tierra del Fuego (TAIS) no tiene entrada v17.
        """
        self._ensure_iibb_wh_tax_groups(company)
        # fuente única: (state_ref, incurred_refs, applied_refs, group_suffix)
        # incurred_refs / applied_refs: lista de (module, ref) a intentar en orden (v18/v19, v17, v16)
        # group xml_id: "l10n_ar_withholding.<group_suffix>"
        wh = "account"
        aw = "l10n_ar_account_withholding"
        iibb_withholding_config = [
            (
                "base.state_ar_c",
                [
                    (wh, "base_tax_withholding_iibb_caba_incurred"),
                    (wh, "ri_tax_withholding_iibb_caba_incurred"),
                    (aw, "ri_tax_retencion_iibb_caba_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_caba_applied"),
                    (wh, "ri_tax_withholding_iibb_caba_applied"),
                    (aw, "ri_tax_retencion_iibb_caba_aplicada"),
                ],
                "tax_group_withholding_iibb_caba",
            ),
            (
                "base.state_ar_b",
                [
                    (wh, "base_tax_withholding_iibb_ba_incurred"),
                    (wh, "ri_tax_withholding_iibb_ba_incurred"),
                    (aw, "ri_tax_retencion_iibb_ba_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_ba_applied"),
                    (wh, "ri_tax_withholding_iibb_ba_applied"),
                    (aw, "ri_tax_retencion_iibb_ba_aplicada"),
                ],
                "tax_group_withholding_iibb_ba",
            ),
            (
                "base.state_ar_k",
                [
                    (wh, "base_tax_withholding_iibb_c_incurred"),
                    (wh, "ri_tax_withholding_iibb_ca_incurred"),
                    (aw, "ri_tax_retencion_iibb_ca_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_c_applied"),
                    (wh, "ri_tax_withholding_iibb_ca_applied"),
                    (aw, "ri_tax_retencion_iibb_ca_aplicada"),
                ],
                "tax_group_withholding_iibb_c",
            ),
            (
                "base.state_ar_x",
                [
                    (wh, "base_tax_withholding_iibb_cba_incurred"),
                    (wh, "ri_tax_withholding_iibb_co_incurred"),
                    (aw, "ri_tax_retencion_iibb_co_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_cba_applied"),
                    (wh, "ri_tax_withholding_iibb_co_applied"),
                    (aw, "ri_tax_retencion_iibb_co_aplicada"),
                ],
                "tax_group_withholding_iibb_cba",
            ),
            (
                "base.state_ar_w",
                [
                    (wh, "base_tax_withholding_iibb_cts_incurred"),
                    (wh, "ri_tax_withholding_iibb_rr_incurred"),
                    (aw, "ri_tax_retencion_iibb_rr_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_cts_applied"),
                    (wh, "ri_tax_withholding_iibb_rr_applied"),
                    (aw, "ri_tax_retencion_iibb_rr_aplicada"),
                ],
                "tax_group_withholding_iibb_cts",
            ),
            (
                "base.state_ar_e",
                [
                    (wh, "base_tax_withholding_iibb_er_incurred"),
                    (wh, "ri_tax_withholding_iibb_er_incurred"),
                    (aw, "ri_tax_retencion_iibb_er_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_er_applied"),
                    (wh, "ri_tax_withholding_iibb_er_applied"),
                    (aw, "ri_tax_retencion_iibb_er_aplicada"),
                ],
                "tax_group_withholding_iibb_er",
            ),
            (
                "base.state_ar_y",
                [
                    (wh, "base_tax_withholding_iibb_j_incurred"),
                    (wh, "ri_tax_withholding_iibb_ju_incurred"),
                    (aw, "ri_tax_retencion_iibb_ju_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_j_applied"),
                    (wh, "ri_tax_withholding_iibb_ju_applied"),
                    (aw, "ri_tax_retencion_iibb_ju_aplicada"),
                ],
                "tax_group_withholding_iibb_j",
            ),
            (
                "base.state_ar_m",
                [
                    (wh, "base_tax_withholding_iibb_mza_incurred"),
                    (wh, "ri_tax_withholding_iibb_za_incurred"),
                    (aw, "ri_tax_retencion_iibb_za_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_mza_applied"),
                    (wh, "ri_tax_withholding_iibb_za_applied"),
                    (aw, "ri_tax_retencion_iibb_za_aplicada"),
                ],
                "tax_group_withholding_iibb_mza",
            ),
            (
                "base.state_ar_f",
                [
                    (wh, "base_tax_withholding_iibb_lr_incurred"),
                    (wh, "ri_tax_withholding_iibb_lr_incurred"),
                    (aw, "ri_tax_retencion_iibb_lr_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_lr_applied"),
                    (wh, "ri_tax_withholding_iibb_lr_applied"),
                    (aw, "ri_tax_retencion_iibb_lr_aplicada"),
                ],
                "tax_group_withholding_iibb_lr",
            ),
            (
                "base.state_ar_a",
                [
                    (wh, "base_tax_withholding_iibb_s_incurred"),
                    (wh, "ri_tax_withholding_iibb_sa_incurred"),
                    (aw, "ri_tax_retencion_iibb_sa_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_s_applied"),
                    (wh, "ri_tax_withholding_iibb_sa_applied"),
                    (aw, "ri_tax_retencion_iibb_sa_aplicada"),
                ],
                "tax_group_withholding_iibb_s",
            ),
            (
                "base.state_ar_j",
                [
                    (wh, "base_tax_withholding_iibb_sj_incurred"),
                    (wh, "ri_tax_withholding_iibb_nn_incurred"),
                    (aw, "ri_tax_retencion_iibb_nn_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_sj_applied"),
                    (wh, "ri_tax_withholding_iibb_nn_applied"),
                    (aw, "ri_tax_retencion_iibb_nn_aplicada"),
                ],
                "tax_group_withholding_iibb_sj",
            ),
            (
                "base.state_ar_d",
                [
                    (wh, "base_tax_withholding_iibb_sl_incurred"),
                    (wh, "ri_tax_withholding_iibb_sl_incurred"),
                    (aw, "ri_tax_retencion_iibb_sl_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_sl_applied"),
                    (wh, "ri_tax_withholding_iibb_sl_applied"),
                    (aw, "ri_tax_retencion_iibb_sl_aplicada"),
                ],
                "tax_group_withholding_iibb_sl",
            ),
            (
                "base.state_ar_s",
                [
                    (wh, "base_tax_withholding_iibb_sf_incurred"),
                    (wh, "ri_tax_withholding_iibb_sf_incurred"),
                    (aw, "ri_tax_retencion_iibb_sf_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_sf_applied"),
                    (wh, "ri_tax_withholding_iibb_sf_applied"),
                    (aw, "tax_retencion_iibb_sf_aplicada"),
                ],
                "tax_group_withholding_iibb_sf",
            ),
            (
                "base.state_ar_g",
                [
                    (wh, "base_tax_withholding_iibb_se_incurred"),
                    (wh, "ri_tax_withholding_iibb_se_incurred"),
                    (aw, "ri_tax_retencion_iibb_se_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_se_applied"),
                    (wh, "ri_tax_withholding_iibb_se_applied"),
                    (aw, "ri_tax_retencion_iibb_se_aplicada"),
                ],
                "tax_group_withholding_iibb_se",
            ),
            (
                "base.state_ar_t",
                [
                    (wh, "base_tax_withholding_iibb_t_incurred"),
                    (wh, "ri_tax_withholding_iibb_tn_incurred"),
                    (aw, "ri_tax_retencion_iibb_tn_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_t_applied"),
                    (wh, "ri_tax_withholding_iibb_tn_applied"),
                    (aw, "ri_tax_retencion_iibb_tn_aplicada"),
                ],
                "tax_group_withholding_iibb_t",
            ),
            (
                "base.state_ar_h",
                [
                    (wh, "base_tax_withholding_iibb_cho_incurred"),
                    (wh, "ri_tax_withholding_iibb_ha_incurred"),
                    (aw, "ri_tax_retencion_iibb_ha_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_cho_applied"),
                    (wh, "ri_tax_withholding_iibb_ha_applied"),
                    (aw, "ri_tax_retencion_iibb_ha_aplicada"),
                ],
                "tax_group_withholding_iibb_cho",
            ),
            (
                "base.state_ar_u",
                [
                    (wh, "base_tax_withholding_iibb_cht_incurred"),
                    (wh, "ri_tax_withholding_iibb_ct_incurred"),
                    (aw, "ri_tax_retencion_iibb_ct_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_cht_applied"),
                    (wh, "ri_tax_withholding_iibb_ct_applied"),
                    (aw, "ri_tax_retencion_iibb_ct_aplicada"),
                ],
                "tax_group_withholding_iibb_cht",
            ),
            (
                "base.state_ar_p",
                [
                    (wh, "base_tax_withholding_iibb_f_incurred"),
                    (wh, "ri_tax_withholding_iibb_fo_incurred"),
                    (aw, "ri_tax_retencion_iibb_fo_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_f_applied"),
                    (wh, "ri_tax_withholding_iibb_fo_applied"),
                    (aw, "ri_tax_retencion_iibb_fo_aplicada"),
                ],
                "tax_group_withholding_iibb_f",
            ),
            (
                "base.state_ar_n",
                [
                    (wh, "base_tax_withholding_iibb_ms_incurred"),
                    (wh, "ri_tax_withholding_iibb_mi_incurred"),
                    (aw, "ri_tax_retencion_iibb_mi_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_ms_applied"),
                    (wh, "ri_tax_withholding_iibb_mi_applied"),
                    (aw, "ri_tax_retencion_iibb_mi_aplicada"),
                ],
                "tax_group_withholding_iibb_ms",
            ),
            (
                "base.state_ar_q",
                [
                    (wh, "base_tax_withholding_iibb_n_incurred"),
                    (wh, "ri_tax_withholding_iibb_ne_incurred"),
                    (aw, "ri_tax_retencion_iibb_ne_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_n_applied"),
                    (wh, "ri_tax_withholding_iibb_ne_applied"),
                    (aw, "ri_tax_retencion_iibb_ne_aplicada"),
                ],
                "tax_group_withholding_iibb_n",
            ),
            (
                "base.state_ar_l",
                [
                    (wh, "base_tax_withholding_iibb_lp_incurred"),
                    (wh, "ri_tax_withholding_iibb_lp_incurred"),
                    (aw, "ri_tax_retencion_iibb_lp_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_lp_applied"),
                    (wh, "ri_tax_withholding_iibb_lp_applied"),
                    (aw, "ri_tax_retencion_iibb_lp_aplicada"),
                ],
                "tax_group_withholding_iibb_lp",
            ),
            (
                "base.state_ar_r",
                [
                    (wh, "base_tax_withholding_iibb_rn_incurred"),
                    (wh, "ri_tax_withholding_iibb_rn_incurred"),
                    (aw, "ri_tax_retencion_iibb_rn_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_rn_applied"),
                    (wh, "ri_tax_withholding_iibb_rn_applied"),
                    (aw, "ri_tax_retencion_iibb_rn_aplicada"),
                ],
                "tax_group_withholding_iibb_rn",
            ),
            (
                "base.state_ar_z",
                [
                    (wh, "base_tax_withholding_iibb_sc_incurred"),
                    (wh, "ri_tax_withholding_iibb_az_incurred"),
                    (aw, "ri_tax_retencion_iibb_az_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_sc_applied"),
                    (wh, "ri_tax_withholding_iibb_az_applied"),
                    (aw, "ri_tax_retencion_iibb_az_aplicada"),
                ],
                "tax_group_withholding_iibb_sc",
            ),
            (
                "base.state_ar_v",
                [
                    (wh, "base_tax_withholding_iibb_tais_incurred"),
                    (wh, "ri_tax_withholding_iibb_tf_incurred"),
                    (aw, "ri_tax_retencion_iibb_tf_sufrida"),
                ],
                [
                    (wh, "ex_tax_withholding_iibb_tais_applied"),
                    (wh, "ri_tax_withholding_iibb_tf_applied"),
                    (aw, "ri_tax_retencion_iibb_tf_aplicada"),
                ],
                "tax_group_withholding_iibb_tais",
            ),
        ]
        for state_ref, incurred_refs, applied_refs, _group_suffix in iibb_withholding_config:
            for module, ref in incurred_refs:
                if t := self.env.ref("%s.%s_%s" % (module, company.id, ref), raise_if_not_found=False):
                    if not t.l10n_ar_state_id:
                        t.l10n_ar_state_id = self.env.ref(state_ref).id
            for module, ref in applied_refs:
                if t := self.env.ref("%s.%s_%s" % (module, company.id, ref), raise_if_not_found=False):
                    if not t.l10n_ar_state_id:
                        t.l10n_ar_state_id = self.env.ref(state_ref).id

        state_id_to_group = {}
        for state_ref, _incurred_refs, _applied_refs, group_suffix in iibb_withholding_config:
            state = self.env.ref(state_ref, raise_if_not_found=False)
            tax_group = self.env.ref("account.%s_%s" % (company.id, group_suffix), raise_if_not_found=False)
            if state and tax_group:
                state_id_to_group[state.id] = tax_group
        if state_id_to_group:
            all_taxes = (
                self.env["account.tax"]
                .with_context(active_test=False)
                .search(
                    [
                        ("company_id", "=", company.id),
                        ("country_id.code", "=", "AR"),
                        ("type_tax_use", "=", "none"),
                        ("l10n_ar_state_id", "in", list(state_id_to_group)),
                    ]
                )
            )
            for state_id, tax_group in state_id_to_group.items():
                if taxes_to_update := all_taxes.filtered(
                    lambda t, sid=state_id, tg=tax_group: t.l10n_ar_state_id.id == sid and t.tax_group_id != tg
                ):
                    taxes_to_update.tax_group_id = tax_group.id

    @api.model
    def _add_profits_iva_wh_tax_groups(self, company):
        """Asigna tax_group_withholding_profits a retenciones de ganancias y
        tax_group_withholding_iva a retenciones de IVA.

        En migraciones desde v17 todos estos impuestos comparten tax_group_withholding_vat
        (único grupo de retenciones en v17). En v18/v19 se usan grupos separados.
        Idempotente: solo actúa sobre impuestos cuyo grupo difiere del esperado.
        """
        profits_group = self.env.ref("account.%s_tax_group_withholding_profits" % company.id, raise_if_not_found=False)
        if profits_group:
            # Retenciones aplicadas de ganancias: identificadas por l10n_ar_tax_type
            ganancias_taxes = (
                self.env["account.tax"]
                .with_context(active_test=False)
                .search(
                    [
                        ("company_id", "=", company.id),
                        ("country_id.code", "=", "AR"),
                        ("type_tax_use", "=", "none"),
                        ("l10n_ar_tax_type", "in", ["earnings", "earnings_scale"]),
                        ("tax_group_id", "!=", profits_group.id),
                    ]
                )
            )
            if ganancias_taxes:
                ganancias_taxes.tax_group_id = profits_group.id
            # Retención sufrida de ganancias (sin l10n_ar_tax_type, misma xmlid en v17/v18/v19)
            if t := self.env.ref("account.%s_ex_tax_retencion_profits_incurred" % company.id, raise_if_not_found=False):
                if t.tax_group_id != profits_group:
                    t.tax_group_id = profits_group.id

        iva_group = self.env.ref("account.%s_tax_group_withholding_iva" % company.id, raise_if_not_found=False)
        if iva_group:
            for ref in (
                "ri_tax_withholding_vat_incurred",  # v17/v18/v19 template RI
                "ex_tax_withholding_vat_applied",  # v18/v19 template EX
            ):
                if t := self.env.ref("account.%s_%s" % (company.id, ref), raise_if_not_found=False):
                    if t.tax_group_id != iva_group:
                        t.tax_group_id = iva_group.id

    def _load(self, template_code, company, install_demo, force_create=True):
        """Luego de que creen los impuestos del archivo account.tax-ar_ri.csv de l10n_ar al instalar el plan de cuentas en la nueva compañìa argentina agregamos en este método las etiquetas que correspondan en los repartition lines."""
        # Llamamos a super para que se creen los impuestos
        res = super()._load(template_code, company, install_demo, force_create)
        company = company or self.env.company
        if company.chart_template in ("ar_ri", "ar_ex", "ar_base"):
            self.sudo()._add_wh_taxes(company)
        return res
