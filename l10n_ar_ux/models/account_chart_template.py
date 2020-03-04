##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """ Set non monetary tag when installing chart of account """
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        self.env['account.account'].set_non_monetary_tag(company)
        return res

    def _create_bank_journals(self, company, acc_template_ref):
        """ We create the withholding journal if withholding module installed """
        if company.country_id == self.env.ref('base.ar'):
            return super(AccountChartTemplate, self.with_context(
                create_withholding_journal=True))._create_bank_journals(company, acc_template_ref)
        return super()._create_bank_journals(company, acc_template_ref)
