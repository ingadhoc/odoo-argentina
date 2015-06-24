# -*- coding: utf-8 -*-
from openerp import models, api
import logging
_logger = logging.getLogger(__name__)


class wizard_multi_charts_accounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def configure_chart(
            self, company_id, currency_id,
            chart_template_id, sale_tax_id, purchase_tax_id):
        if self.env['account.account'].search(
                [('company_id', '=', company_id)]):
            _logger.warning(
                'There is already a chart of account for company_id %i' % (
                    company_id))
            return True
        _logger.info(
            'Configuring chart %i for company %i' % (
                chart_template_id, company_id))
        wizard = self.with_context(company_id=company_id).create({
            'company_id': company_id,
            'currency_id': currency_id,
            'only_one_chart_template': True,
            'chart_template_id': chart_template_id,
            'code_digits': 7,
            "sale_tax": sale_tax_id,
            "purchase_tax": purchase_tax_id,
            # 'sale_tax_rate': ,
            # 'purchase_tax_rate': ,
            # 'complete_tax_set': fie
            })
        return wizard.execute()
