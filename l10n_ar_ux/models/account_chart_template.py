##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountChartTemplate(models.AbstractModel):

    _inherit = 'account.chart.template'

    def _load_data(self, data, ignore_duplicates=False):
        res = super()._load_data(data, ignore_duplicates=ignore_duplicates)
        if res.get('res.company'):
            self.env['account.account'].set_non_monetary_tag(res['res.company'])
        return res
