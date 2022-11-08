##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _load(self, company):
        """ Set non monetary tag when installing chart of account """
        res = super()._load(company)
        if company.country_id == self.env.ref('base.ar'):
            self.env['account.account'].set_non_monetary_tag(company)
        return res
