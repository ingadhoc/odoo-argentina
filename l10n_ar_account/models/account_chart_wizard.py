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

    # @api.model
    # def generate_journals(
    #         self, chart_template_id, acc_template_ref, company_id):
    #     """
    #     Overwrite this function so that no journal is created on chart
    #     installation
    #     """
    #     return True

    @api.model
    def _prepare_all_journals(
            self, chart_template_id, acc_template_ref, company_id):
        """
        Inherit this function so that we dont create sale and purchase journals
        """
        journal_data = super(
            wizard_multi_charts_accounts, self)._prepare_all_journals(
            chart_template_id, acc_template_ref, company_id)

        # remove sale and purchase journals data
        new_journal_data = [
            journal for journal in journal_data if journal['type'] not in [
                'sale', 'purchase', 'sale_refund', 'purchase_refund']]
        return new_journal_data

    @api.model
    def _create_bank_journals_from_o2m(
            self, obj_wizard, company_id, acc_template_ref):
        """
        Overwrite this function so that no journal is created on chart
        installation
        """
        return True

    # @api.model
    # def _prepare_all_journals(
    #         self, chart_template_id, acc_template_ref, company_id):
    #     """
    #     Inherit this function in order to add use document and other
    #     configuration if company use argentinian localization
    #     """
    #     journal_data = super(
    #         wizard_multi_charts_accounts, self)._prepare_all_journals(
    #         chart_template_id, acc_template_ref, company_id)

    #     # if argentinian chart, we set use_argentinian_localization for company
    #     company = self.env['res.company'].browse(company_id)

    #     if company.use_argentinian_localization:
    #         point_of_sale = self.env['afip.point_of_sale'].search([
    #             ('number', '=', 1),
    #             ('company_id', '=', company_id),
    #             ], limit=1)
    #         if not point_of_sale:
    #             point_of_sale = point_of_sale.create({
    #                 'name': 'Punto de venta 1',
    #                 'number': 1,
    #                 'company_id': company_id,
    #                 })
    #         for vals_journal in journal_data:
    #             if vals_journal['type'] in [
    #                     'sale', 'sale_refund', 'purchase', 'purchase_refund']:
    #                 vals_journal['use_documents'] = True
    #                 vals_journal['point_of_sale_id'] = point_of_sale.id
    #     return journal_data

    @api.model
    def configure_chart(
            self, company_id, currency_id,
            chart_template_id, sale_tax_id, purchase_tax_id):
        # return True
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
        wizard.execute()

        # add default tax to current products
        _logger.info('Updating products taxes')
        tax_vals = {}
        sale_tax_template = self.env['account.tax.template'].browse(
            sale_tax_id)
        sale_tax = self.env['account.tax'].search([
            ('company_id', '=', company_id),
            ('name', '=', sale_tax_template.name)], limit=1)
        if sale_tax:
            tax_vals['taxes_id'] = [(4, sale_tax.id)]

        purchase_tax_template = self.env['account.tax.template'].browse(
            purchase_tax_id)
        purchase_tax = self.env['account.tax'].search([
            ('company_id', '=', company_id),
            ('name', '=', purchase_tax_template.name)], limit=1)
        if purchase_tax:
            tax_vals['supplier_taxes_id'] = [(4, purchase_tax.id)]

        for product in self.env['product.product'].search([]):
            product.write(tax_vals)
        return True
