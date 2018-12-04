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

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(
            company, tax_template_to_tax)
        if self.tax_group_id:
            vals['tax_group_id'] = self.tax_group_id.id
        return vals


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        # hacemos que se cree diario de retenciones si modulo instaldo
        if company.localization == 'argentina':
            self = self.with_context(create_withholding_journal=True)

        # al final esto lo hacemos como customizacion
        # on argentinian localization we prefer to create banks manually
        # for tests, demo data requires a bank journal to be loaded, we
        # send this on context
        # NEW: we also prefer to create cashbox manually
        # if company.localization == 'argentina' and not self._context.get(
        #         'with_bank_journal'):
        #     for rec in self.bank_account_ids:
        #         if rec.account_type == 'bank':
        #             rec.unlink()
        return super(
            WizardMultiChartsAccounts, self)._create_bank_journals_from_o2m(
            company, acc_template_ref)

    @api.multi
    def execute(self):
        res = super(WizardMultiChartsAccounts, self).execute()
        if self.company_id.localization == 'argentina':
            self.env['account.account'].set_no_monetaria_tag(self.company_id)
        return res


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    opening_clousure_account_id = fields.Many2one(
        'account.account.template',
        string='Opening / Closure Account',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
    )

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

    @api.multi
    def _prepare_all_journals(
            self, acc_template_ref, company, journals_dict=None):
        """
        Inherit this function in order to add use document and other
        configuration if company use argentinian localization
        """
        journal_data = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)

        # add more journals commonly used in argentina localization
        # TODO we should move this to another module beacuse not only
        # argentina use this
        opening_clousure_account_id = acc_template_ref.get(
            self.opening_clousure_account_id.id)
        journals = [
            ('Liquidación de Impuestos', 'LIMP', 'general', False),
            ('Sueldos y Jornales', 'SYJ', 'general', False),
            ('Asientos de Apertura / Cierre', 'A/C', 'general',
                opening_clousure_account_id),
        ]
        for name, code, type, default_account_id in journals:
            journal_data.append({
                'type': type,
                'name': name,
                'code': code,
                'default_credit_account_id': default_account_id,
                'default_debit_account_id': default_account_id,
                'company_id': company.id,
                'show_on_dashboard': False,
                'update_posted': True,
            })

        # if argentinian chart, we set use_argentinian_localization for company
        if company.localization == 'argentina':
            new_journal_data = []
            for vals_journal in journal_data:
                # for sale journals we use get_name_and_code function
                if vals_journal['type'] == 'sale':
                    # we only create point of sale if explicitly sent in
                    # context
                    if not self._context.get('create_point_of_sale_type'):
                        continue
                    # TODO esto en realidad se esta usando solamente en demo
                    # al instalar plan de cuentas, se podria usar tmb desde
                    # config como haciamos antes
                    point_of_sale_type = self._context.get(
                        'point_of_sale_type', 'manual')
                    # for compatibility with afip_ws
                    afip_ws = self._context.get(
                        'afip_ws', False)
                    point_of_sale_number = self._context.get(
                        'point_of_sale_number', 1)
                    if afip_ws:
                        vals_journal['afip_ws'] = afip_ws
                    vals_journal['point_of_sale_number'] = point_of_sale_number
                    vals_journal['point_of_sale_type'] = point_of_sale_type
                    new_journal = self.env['account.journal'].new(vals_journal)
                    new_journal.with_context(
                        set_point_of_sale_name=True
                    ).change_to_set_name_and_code()
                    name = new_journal.name
                    code = new_journal.code
                    vals_journal['name'] = name
                    vals_journal['code'] = code
                new_journal_data.append(vals_journal)
            return new_journal_data
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
