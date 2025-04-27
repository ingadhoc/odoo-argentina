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

        # creacion de secuencias y agregado de etiquetas para liquidación de impuestos
        withholdings_domain = [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "none"),
            ("country_code", "=", "AR"),
            ("l10n_ar_withholding_payment_type", "=", "supplier"),
        ]
        profits_domain = withholdings_domain + [("l10n_ar_tax_type", "in", ["earnings", "earnings_scale"])]
        sicore_taxes = self.env["account.tax"].with_context(active_test=False).search(profits_domain)

        # agregado de etiquetas para liquidacion de impuestos sicore
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
