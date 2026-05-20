##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _add_wh_taxes(self, company):
        """Agregamos tax groups en impuestos y secuencias en impuestos"""
        # TODO deberia ir en odoo nativo
        company.ensure_one()

        # agregado de jurisdiccion a tax_groups
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
            if tax_group := self.env.ref("account.%s_%s" % (company.id, tax_group_ref), raise_if_not_found=False):
                tax_group.l10n_ar_state_id = self.env.ref(state_ref).id

                sequence = self.env["ir.sequence"].create(
                    {
                        "name": tax_group.name,
                        "prefix": "%(year)s-",
                        "padding": 8,
                        "number_increment": 1,
                        "implementation": "standard",
                        "company_id": company.id,
                    }
                )
                tax_group.l10n_ar_withholding_sequence_id = sequence.id

        # creacion de secuencia para ret ganancias
        withholdings_domain = [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "none"),
            ("country_code", "=", "AR"),
            ("l10n_ar_withholding_payment_type", "=", "supplier"),
        ]

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
        profits_taxes.tax_group_id.l10n_ar_withholding_sequence_id = sequence.id

    def _load(self, template_code, company, install_demo, force_create=True):
        """Luego de que creen los impuestos del archivo account.tax-ar_ri.csv de l10n_ar al instalar el plan de cuentas en la nueva compañìa argentina agregamos en este método las etiquetas que correspondan en los repartition lines."""
        # Llamamos a super para que se creen los impuestos
        res = super()._load(template_code, company, install_demo, force_create)
        company = company or self.env.company
        if company.chart_template in ("ar_ri", "ar_ex", "ar_base"):
            self.sudo()._add_wh_taxes(company)
        return res
