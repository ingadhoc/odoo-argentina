# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
import logging
_logger = logging.getLogger(__name__)


class wizard_multi_charts_accounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def _load_template(
            self, template_id, company_id, code_digits=None, obj_wizard=None,
            account_ref=None, taxes_ref=None, tax_code_ref=None):
        res = super(wizard_multi_charts_accounts, self)._load_template(
            template_id, company_id, code_digits=code_digits,
            obj_wizard=obj_wizard, account_ref=account_ref,
            taxes_ref=taxes_ref, tax_code_ref=tax_code_ref)
        # company = self.env['res.company'].browse(company_id)
        # generate always, not only for arg. companies
        # if company.use_argentinian_localization:
        self.generate_receiptbooks(template_id, account_ref, company_id)
        return res

    @api.model
    def generate_receiptbooks(
            self, chart_template_id, acc_template_ref, company_id):
        """
        Overwrite this function so that no journal is created on chart
        installation
        """
        receiptbook_data = self._prepare_all_receiptbook_data(
            chart_template_id, acc_template_ref, company_id)
        for receiptbook_vals in receiptbook_data:
            self.check_created_receiptbooks(receiptbook_vals, company_id)
        return True

    @api.model
    def check_created_receiptbooks(self, receiptbook_vals, company_id):
        """
        This method used for checking new receipbooks already created or not.
        If not then create new receipbook.
        """
        receipbook = self.env['account.voucher.receiptbook'].search([
            ('name', '=', receiptbook_vals['name']),
            ('company_id', '=', company_id)])
        if not receipbook:
            receipbook.create(receiptbook_vals)
        return True

    @api.model
    def _prepare_all_receiptbook_data(
            self, chart_template_id, acc_template_ref, company_id):
        """
        """
        receiptbook_data = []
        voucher_types = {
            'payment': _('Pagos'),
            'receipt': _('Recibos'),
        }
        sequence_types = {
            'automatic': _(''),
            'manual': _('Manuales'),
        }
        # we use for sequences and for prefix
        sequences = {
            'automatic': 1,
            'manual': 2,
        }
        for sequence_type in ['automatic', 'manual']:
            for voucher_type in ['receipt', 'payment']:
                vals = {
                    'name': "%s %s" % (
                        voucher_types[voucher_type],
                        sequence_types[sequence_type],),
                    'type': voucher_type,
                    'sequence_type': sequence_type,
                    'padding': 8,
                    'company_id': company_id,
                    'document_class_id': self.env.ref(
                        'l10n_ar_account.dc_recibo_x').id,
                    'manual_prefix': (
                        '%%0%sd-' % 4 % sequences[sequence_type]),
                    'sequence': sequences[sequence_type],
                }
                receiptbook_data.append(vals)
        return receiptbook_data
