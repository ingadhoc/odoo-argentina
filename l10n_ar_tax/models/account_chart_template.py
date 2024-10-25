##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, Command
import logging
_logger = logging.getLogger(__name__)
from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ar_ri', 'account.tax')
    def _get_ar_ri_withholding_account_tax(self):
        """ En caso de que se creen nuevas compañías argentinas responsable inscripto con su plan de cuentas correspondiente entonces a los impuestos creados de retenciones de ganancias e iva les agregamos el código de impuesto. """
        taxes_creados = super()._get_ar_ri_withholding_account_tax()
        if taxes_creados.get('ri_tax_withholding_ganancias_applied'):
            taxes_creados.get('ri_tax_withholding_ganancias_applied')['l10n_ar_code'] = '01'
        if taxes_creados.get('ri_tax_withholding_vat_applied'):
            taxes_creados.get('ri_tax_withholding_vat_applied')['l10n_ar_code'] = '02'
        return taxes_creados

    @api.model
    def _add_wh_taxes(self, company):
        """ Agregamos etiquetas en repartition lines de impuestos de percepciones de iva, ganancias e ingresos brutos.  """
        # TODO deberia ir en odoo nativo
        company.ensure_one()
        # Retenciones aplicadas de iva
        impuesto_ret_iva_aplic = self.env.ref("account.%s_%s" % (company.id, 'ri_tax_withholding_vat_applied'), raise_if_not_found=False)
        if impuesto_ret_iva_aplic:
            impuesto_ret_iva_aplic.l10n_ar_code = '02'
        tax_state_tupples = [
            ('ri_tax_percepcion_iibb_caba_sufrida', 'base.state_ar_c'),
            ('ri_tax_percepcion_iibb_ba_sufrida', 'base.state_ar_b'),
            ('ri_tax_percepcion_iibb_co_sufrida', 'base.state_ar_x'),
            ('ri_tax_percepcion_iibb_sf_sufrida', 'base.state_ar_s'),
            ('ri_tax_percepcion_iibb_ca_sufrida', 'base.state_ar_k'),
            ('ri_tax_percepcion_iibb_rr_sufrida', 'base.state_ar_w'),
            ('ri_tax_percepcion_iibb_er_sufrida', 'base.state_ar_e'),
            ('ri_tax_percepcion_iibb_ju_sufrida', 'base.state_ar_y'),
            ('ri_tax_percepcion_iibb_za_sufrida', 'base.state_ar_m'),
            ('ri_tax_percepcion_iibb_lr_sufrida', 'base.state_ar_f'),
            ('ri_tax_percepcion_iibb_sa_sufrida', 'base.state_ar_a'),
            ('ri_tax_percepcion_iibb_nn_sufrida', 'base.state_ar_j'),
            ('ri_tax_percepcion_iibb_sl_sufrida', 'base.state_ar_d'),
            ('ri_tax_percepcion_iibb_se_sufrida', 'base.state_ar_g'),
            ('ri_tax_percepcion_iibb_tn_sufrida', 'base.state_ar_t'),
            ('ri_tax_percepcion_iibb_ha_sufrida', 'base.state_ar_h'),
            ('ri_tax_percepcion_iibb_ct_sufrida', 'base.state_ar_u'),
            ('ri_tax_percepcion_iibb_fo_sufrida', 'base.state_ar_p'),
            ('ri_tax_percepcion_iibb_mi_sufrida', 'base.state_ar_n'),
            ('ri_tax_percepcion_iibb_ne_sufrida', 'base.state_ar_q'),
            ('ri_tax_percepcion_iibb_lp_sufrida', 'base.state_ar_l'),
            ('ri_tax_percepcion_iibb_rn_sufrida', 'base.state_ar_r'),
            ('ri_tax_percepcion_iibb_az_sufrida', 'base.state_ar_z'),
            ('ri_tax_percepcion_iibb_tf_sufrida', 'base.state_ar_v'),
            ('ri_tax_withholding_iibb_caba_incurred', 'base.state_ar_c'),
            ('ri_tax_withholding_iibb_ba_incurred', 'base.state_ar_b'),
            ('ri_tax_withholding_iibb_ca_incurred', 'base.state_ar_x'),
            ('ri_tax_withholding_iibb_co_incurred', 'base.state_ar_s'),
            ('ri_tax_withholding_iibb_rr_incurred', 'base.state_ar_k'),
            ('ri_tax_withholding_iibb_er_incurred', 'base.state_ar_w'),
            ('ri_tax_withholding_iibb_ju_incurred', 'base.state_ar_e'),
            ('ri_tax_withholding_iibb_za_incurred', 'base.state_ar_y'),
            ('ri_tax_withholding_iibb_lr_incurred', 'base.state_ar_m'),
            ('ri_tax_withholding_iibb_sa_incurred', 'base.state_ar_f'),
            ('ri_tax_withholding_iibb_nn_incurred', 'base.state_ar_a'),
            ('ri_tax_withholding_iibb_sl_incurred', 'base.state_ar_j'),
            ('ri_tax_withholding_iibb_sf_incurred', 'base.state_ar_d'),
            ('ri_tax_withholding_iibb_se_incurred', 'base.state_ar_g'),
            ('ri_tax_withholding_iibb_tn_incurred', 'base.state_ar_t'),
            ('ri_tax_withholding_iibb_ha_incurred', 'base.state_ar_h'),
            ('ri_tax_withholding_iibb_ct_incurred', 'base.state_ar_u'),
            ('ri_tax_withholding_iibb_fo_incurred', 'base.state_ar_p'),
            ('ri_tax_withholding_iibb_mi_incurred', 'base.state_ar_n'),
            ('ri_tax_withholding_iibb_ne_incurred', 'base.state_ar_q'),
            ('ri_tax_withholding_iibb_lp_incurred', 'base.state_ar_l'),
            ('ri_tax_withholding_iibb_rn_incurred', 'base.state_ar_r'),
            ('ri_tax_withholding_iibb_az_incurred', 'base.state_ar_z'),
            ('ri_tax_withholding_iibb_tf_incurred', 'base.state_ar_v'),
            ('ri_tax_percepcion_iibb_caba_aplicada', 'base.state_ar_c'),
            ('ri_tax_percepcion_iibb_ba_aplicada', 'base.state_ar_b'),
            ('ri_tax_percepcion_iibb_co_aplicada', 'base.state_ar_x'),
            ('ri_tax_percepcion_iibb_sf_aplicada', 'base.state_ar_s'),
            ('ri_tax_percepcion_iibb_ca_aplicada', 'base.state_ar_k'),
            ('ri_tax_percepcion_iibb_rr_aplicada', 'base.state_ar_w'),
            ('ri_tax_percepcion_iibb_er_aplicada', 'base.state_ar_e'),
            ('ri_tax_percepcion_iibb_ju_aplicada', 'base.state_ar_y'),
            ('ri_tax_percepcion_iibb_za_aplicada', 'base.state_ar_m'),
            ('ri_tax_percepcion_iibb_lr_aplicada', 'base.state_ar_f'),
            ('ri_tax_percepcion_iibb_sa_aplicada', 'base.state_ar_a'),
            ('ri_tax_percepcion_iibb_nn_aplicada', 'base.state_ar_j'),
            ('ri_tax_percepcion_iibb_sl_aplicada', 'base.state_ar_d'),
            ('ri_tax_percepcion_iibb_se_aplicada', 'base.state_ar_g'),
            ('ri_tax_percepcion_iibb_tn_aplicada', 'base.state_ar_t'),
            ('ri_tax_percepcion_iibb_ha_aplicada', 'base.state_ar_h'),
            ('ri_tax_percepcion_iibb_ct_aplicada', 'base.state_ar_u'),
            ('ri_tax_percepcion_iibb_fo_aplicada', 'base.state_ar_p'),
            ('ri_tax_percepcion_iibb_mi_aplicada', 'base.state_ar_n'),
            ('ri_tax_percepcion_iibb_ne_aplicada', 'base.state_ar_q'),
            ('ri_tax_percepcion_iibb_lp_aplicada', 'base.state_ar_l'),
            ('ri_tax_percepcion_iibb_rn_aplicada', 'base.state_ar_r'),
            ('ri_tax_percepcion_iibb_az_aplicada', 'base.state_ar_z'),
            ('ri_tax_percepcion_iibb_tf_aplicada', 'base.state_ar_v'),
            ('ri_tax_withholding_iibb_caba_applied', 'base.state_ar_c'),
            ('ri_tax_withholding_iibb_ba_applied', 'base.state_ar_b'),
            ('ri_tax_withholding_iibb_ca_applied', 'base.state_ar_x'),
            ('ri_tax_withholding_iibb_co_applied', 'base.state_ar_s'),
            ('ri_tax_withholding_iibb_rr_applied', 'base.state_ar_k'),
            ('ri_tax_withholding_iibb_er_applied', 'base.state_ar_w'),
            ('ri_tax_withholding_iibb_ju_applied', 'base.state_ar_e'),
            ('ri_tax_withholding_iibb_za_applied', 'base.state_ar_y'),
            ('ri_tax_withholding_iibb_lr_applied', 'base.state_ar_m'),
            ('ri_tax_withholding_iibb_sa_applied', 'base.state_ar_f'),
            ('ri_tax_withholding_iibb_nn_applied', 'base.state_ar_a'),
            ('ri_tax_withholding_iibb_sl_applied', 'base.state_ar_j'),
            ('ri_tax_withholding_iibb_sf_applied', 'base.state_ar_d'),
            ('ri_tax_withholding_iibb_se_applied', 'base.state_ar_g'),
            ('ri_tax_withholding_iibb_tn_applied', 'base.state_ar_t'),
            ('ri_tax_withholding_iibb_ha_applied', 'base.state_ar_h'),
            ('ri_tax_withholding_iibb_ct_applied', 'base.state_ar_u'),
            ('ri_tax_withholding_iibb_fo_applied', 'base.state_ar_p'),
            ('ri_tax_withholding_iibb_mi_applied', 'base.state_ar_n'),
            ('ri_tax_withholding_iibb_ne_applied', 'base.state_ar_q'),
            ('ri_tax_withholding_iibb_lp_applied', 'base.state_ar_l'),
            ('ri_tax_withholding_iibb_rn_applied', 'base.state_ar_r'),
            ('ri_tax_withholding_iibb_az_applied', 'base.state_ar_z'),
            ('ri_tax_withholding_iibb_tf_applied', 'base.state_ar_v'),

        ]
        for tax_ref, state_ref in tax_state_tupples:
            # Identificamos el impuesto al que se le va a agregar la/s etiqueta/s
            tax = self.env.ref( "account.%s_%s" % (company.id, tax_ref), raise_if_not_found=False)
            if tax:
                tax.l10n_ar_state_id = self.env.ref(state_ref).id
                tax.amount_type = 'percent'

        # Listado de impuesto-etiquetas a agregar, el primer elemento de cada tupla es el id del impuesto, etiqueta
        # esto es para que luego funcione bien la liquidación de impuestos
        imp_etiq_list = [
            ('ri_tax_percepcion_iva_aplicada', 'tag_ret_perc_sicore_aplicada'),
            ('ri_tax_withholding_ganancias_applied', 'tag_ret_perc_sicore_aplicada'),
            ('ri_tax_percepcion_ganancias_aplicada', 'tag_ret_perc_sicore_aplicada'),
            ('ri_tax_percepcion_iibb_caba_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_ba_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_co_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_sf_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_ca_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_rr_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_er_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_ju_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_za_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_lr_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_sa_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_nn_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_sl_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_se_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_tn_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_ha_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_ct_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_fo_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_mi_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_ne_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_lp_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_rn_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_az_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_percepcion_iibb_tf_sufrida', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_caba_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_ba_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_ca_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_co_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_rr_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_er_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_ju_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_za_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_lr_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_sa_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_nn_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_sl_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_sf_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_se_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_tn_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_ha_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_ct_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_fo_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_mi_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_ne_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_lp_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_rn_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_az_incurred', 'tax_tag_a_cuenta_iibb'),
            ('ri_tax_withholding_iibb_tf_incurred', 'tax_tag_a_cuenta_iibb'),
        ]
        for tax_xmlid, tag_xmlid in imp_etiq_list:
            xml_id_percep = "account.%s_%s" % (company.id, tax_xmlid)
            # Identificamos el impuesto al que se le va a agregar la/s etiqueta/s
            tax = self.env.ref(xml_id_percep, raise_if_not_found=False)
            tag = self.env.ref('l10n_ar_ux.%s' % (tag_xmlid), raise_if_not_found=False)
            if not tax or not tag:
                continue
            self.env['account.tax.repartition.line'].search([('tax_id', '=', tax.id), ('repartition_type', '=', 'tax')]).tag_ids = [Command.link(tag.id)]

    def _load(self, template_code, company, install_demo):
        """ Luego de que creen los impuestos del archivo account.tax-ar_ri.csv de l10n_ar al instalar el plan de cuentas en la nueva compañìa argentina agregamos en este método las etiquetas que correspondan en los repartition lines. """
        # Llamamos a super para que se creen los impuestos
        res = super()._load(template_code, company, install_demo)
        company = company or self.env.company
        if company.chart_template in ('ar_ri', 'ar_ex'):
            self._add_wh_taxes(company)
        return res
