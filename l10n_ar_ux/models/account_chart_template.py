##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountChartTemplate(models.AbstractModel):

    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo):
        """ Set non monetary tag when installing chart of account """
        res = super()._load(template_code, company, install_demo)
        if template_code in ('ar_base', 'ar_ex', 'ar_ri'):
            self.env['account.account'].set_non_monetary_tag(company)

            # Dejamos las cuentas de tipo cash con bypass
            company = self.env.context['allowed_company_ids'][0]
            cash_journals = self.env['account.journal'].search([('company_id', '=', company), ('type', '=', 'cash')])
            for journal in cash_journals:
                journal.inbound_payment_method_line_ids.write({'payment_account_id': journal.default_account_id.id})
                journal.outbound_payment_method_line_ids.write({'payment_account_id': journal.default_account_id.id})
        return res
