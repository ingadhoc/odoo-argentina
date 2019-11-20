from odoo import models
from odoo.http import request


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        """ extend in orer to set not monetary tag to certain accounts """
        self.ensure_one()

        res = super().load_for_current_company(sale_tax_rate, purchase_tax_rate)

        # do not use `request.env` here, it can cause deadlocks
        if request and request.session.uid:
            current_user = self.env['res.users'].browse(request.uid)
            company = current_user.company_id
        else:
            # fallback to company of current user, most likely __system__
            # (won't work well for multi-company)
            company = self.env.user.company_id

        if company.localization == 'argentina':
            self.env['account.account'].set_no_monetaria_tag(company)

        return res
