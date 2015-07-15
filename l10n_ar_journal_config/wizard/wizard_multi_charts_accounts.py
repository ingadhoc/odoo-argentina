# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api
import logging
_logger = logging.getLogger(__name__)


class wizard_multi_charts_accounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def generate_journals(
            self, chart_template_id, acc_template_ref, company_id):
        """
        Overwrite this function so that no journal is created on chart
        installation
        """
        return True

    @api.model
    def _create_bank_journals_from_o2m(
            self, obj_wizard, company_id, acc_template_ref):
        """
        Overwrite this function so that no journal is created on chart
        installation
        """
        return True
