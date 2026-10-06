##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ar_base", "res.company")
    def _get_ar_base_res_company(self):
        res = super()._get_ar_base_res_company()
        res[self.env.company.id]["display_invoice_tax_company_currency"] = False
        return res
