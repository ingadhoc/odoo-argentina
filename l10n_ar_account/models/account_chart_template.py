# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields
import logging
_logger = logging.getLogger(__name__)


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    # TODO perhups we should use tags instead of groups
    tax_group_id = fields.Many2one(
        'account.tax.group',
        string="Tax Group",
    )

    def _get_tax_vals(self, company):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company)
        if self.tax_group_id:
            vals['tax_group_id'] = self.tax_group_id.id
        return vals


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def generate_fiscal_position(
            self, tax_template_ref, acc_template_ref, company):
        """
        if chart is argentina localization, then we add afip_code to fiscal
        positions.
        We also add other data to add fiscal positions automatically
        """
        res = super(AccountChartTemplate, self).generate_fiscal_position(
            tax_template_ref, acc_template_ref, company)
        if self.localization != 'argentina':
            return res
        positions = self.env['account.fiscal.position.template'].search(
            [('chart_template_id', '=', self.id)])
        for position in positions:
            created_position = self.env['account.fiscal.position'].search([
                ('company_id', '=', company.id),
                ('name', '=', position.name),
                ('note', '=', position.note)], limit=1)
            if created_position:
                created_position.update({
                    'afip_code': position.afip_code,
                    'afip_responsability_type_ids': (
                        position.afip_responsability_type_ids),
                    # TODO this should be done in odoo core
                    'country_id': position.country_id.id,
                    'country_group_id': position.country_group_id.id,
                    'state_ids': position.state_ids.ids,
                    'zip_to': position.zip_to,
                    'zip_from': position.zip_from,
                    'auto_apply': position.auto_apply,
                })
        return res

    @api.model
    def _prepare_all_journals(
            self, acc_template_ref, company, journals_dict=None):
        """
        Inherit this function in order to add use document and other
        configuration if company use argentinian localization
        """
        journal_data = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)
        # if argentinian chart, we set use_argentinian_localization for company
        if company.localization == 'argentina':
            for vals_journal in journal_data:
                # for sale journals we use get_name_and_code function
                if vals_journal['type'] == 'sale':
                    point_of_sale_type = self._context.get(
                        'point_of_sale_type', 'manual')
                    # for compatibility with afip_ws
                    afip_ws = self._context.get(
                        'afip_ws', False)
                    point_of_sale_number = self._context.get(
                        'point_of_sale_number', 1)
                    name, code = self.env['account.journal'].get_name_and_code(
                        point_of_sale_type, point_of_sale_number)
                    vals_journal['name'] = name
                    vals_journal['code'] = code
                    if afip_ws:
                        vals_journal['afip_ws'] = afip_ws
                    vals_journal['point_of_sale_number'] = point_of_sale_number
                    vals_journal['point_of_sale_type'] = point_of_sale_type
        return journal_data

    # @api.model
    # def configure_chart(
    #         self, company_id, currency_id,
    #         chart_template_id, sale_tax_id, purchase_tax_id):
    #     # return True
    #     if self.env['account.account'].search(
    #             [('company_id', '=', company_id)]):
    #         _logger.warning(
    #             'There is already a chart of account for company_id %i' % (
    #                 company_id))
    #         return True
    #     _logger.info(
    #         'Configuring chart %i for company %i' % (
    #             chart_template_id, company_id))
    #     wizard = self.with_context(company_id=company_id).create({
    #         'company_id': company_id,
    #         'currency_id': currency_id,
    #         'only_one_chart_template': True,
    #         'chart_template_id': chart_template_id,
    #         'code_digits': 7,
    #         "sale_tax": sale_tax_id,
    #         "purchase_tax": purchase_tax_id,
    #         # 'sale_tax_rate': ,
    #         # 'purchase_tax_rate': ,
    #         # 'complete_tax_set': fie
    #         })
    #     wizard.execute()

    #     # add default tax to current products
    #     _logger.info('Updating products taxes')
    #     tax_vals = {}
    #     sale_tax_template = self.env['account.tax.template'].browse(
    #         sale_tax_id)
    #     sale_tax = self.env['account.tax'].search([
    #         ('company_id', '=', company_id),
    #         ('name', '=', sale_tax_template.name)], limit=1)
    #     if sale_tax:
    #         tax_vals['taxes_id'] = [(4, sale_tax.id)]

    #     purchase_tax_template = self.env['account.tax.template'].browse(
    #         purchase_tax_id)
    #     purchase_tax = self.env['account.tax'].search([
    #         ('company_id', '=', company_id),
    #         ('name', '=', purchase_tax_template.name)], limit=1)
    #     if purchase_tax:
    #         tax_vals['supplier_taxes_id'] = [(4, purchase_tax.id)]

    #     for product in self.env['product.product'].search([]):
    #         product.write(tax_vals)
    #     return True
