##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields
import logging
_logger = logging.getLogger(__name__)


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    # TODO perhups we should use tags instead of groups
    tax_group_id = fields.Many2one(
        'account.tax.group',
        string="Tax Group",
    )

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(
            company, tax_template_to_tax)
        if self.tax_group_id:
            vals['tax_group_id'] = self.tax_group_id.id
        return vals


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    opening_clousure_account_id = fields.Many2one(
        'account.account.template',
        string='Opening / Closure Account',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
    )

    @api.multi
    def _get_fp_vals(self, company, position):
        res = super()._get_fp_vals(company, position)
        if company.localization == 'argentina':
            res['afip_responsability_type_ids'] = [
                (6, False, position.afip_responsability_type_ids.ids)]
        return res

    @api.multi
    def _prepare_all_journals(
            self, acc_template_ref, company, journals_dict=None):
        """
        Inherit this function in order to add use document and other
        configuration if company use argentinian localization
        """
        journal_data = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)

        # add more journals commonly used in argentina localization
        # TODO we should move this to another module beacuse not only
        # argentina use this
        opening_clousure_account_id = acc_template_ref.get(
            self.opening_clousure_account_id.id)
        journals = [
            ('Liquidación de Impuestos', 'LIMP', 'general', False),
            ('Sueldos y Jornales', 'SYJ', 'general', False),
            ('Asientos de Apertura / Cierre', 'A/C', 'general',
                opening_clousure_account_id),
        ]
        for name, code, journal_type, default_account_id in journals:
            journal_data.append({
                'type': journal_type,
                'name': name,
                'code': code,
                'default_credit_account_id': default_account_id,
                'default_debit_account_id': default_account_id,
                'company_id': company.id,
                'show_on_dashboard': False,
                'update_posted': True,
            })

        # do no create sals journal for argentina
        if company.localization == 'argentina':
            for vals in journal_data:
                if vals['type'] == 'sale':
                    journal_data.remove(vals)
        return journal_data

    @api.multi
    def _create_bank_journals(self, company, acc_template_ref):
        # hacemos que se cree diario de retenciones si modulo instaldo
        if company.localization == 'argentina':
            self = self.with_context(create_withholding_journal=True)
        return super(
            AccountChartTemplate, self)._create_bank_journals(
            company, acc_template_ref)
