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
        return res
