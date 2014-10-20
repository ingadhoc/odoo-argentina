# -*- coding: utf-8 -*-
import time
# from datetime import date, datetime
from openerp import models, fields, api, _
from openerp.exceptions import Warning
# from dateutil.relativedelta import relativedelta
# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


# def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
#     return len((datetime.now()).strftime(date_format))


class account_vat_ledger(models.Model):

    _name = "account.vat.ledger"
    _description = "Account VAT Ledger"
    _inherit = ['mail.thread']
    _order = 'period_id desc'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env[
            'res.company']._company_default_get('account.vat.ledger'))
    fiscalyear_id = fields.Many2one(
        'account.fiscalyear', 'Fiscal Year', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help='Keep empty for all open fiscal year')
    type = fields.Selection(
        [('sale', 'Sale'), ('purchase', 'Purchase')],
        "Type", required=True)
    period_id = fields.Many2one(
        'account.period', 'Period', required=True,
        readonly=True, states={'draft': [('readonly', False)]},)
    journal_ids = fields.Many2many(
        'account.journal', 'account_vat_ledger_journal_rel',
        'vat_ledger_id', 'journal_id', string='Journals', required=True,
        readonly=True, states={'draft': [('readonly', False)]},)
    first_page = fields.Integer(
        "First Page", required=True,
        readonly=True, states={'draft': [('readonly', False)]},)
    last_page = fields.Integer(
        "Last Page",
        readonly=True, states={'draft': [('readonly', False)]},)
    presented_ledger = fields.Binary(
        "Presented Ledger",
        readonly=True, states={'draft': [('readonly', False)]},)
    state = fields.Selection(
        [('draft', 'Draft'), ('presented', 'Presented'), ('cancel', 'Cancel')],
        'State', required=True, default='draft')
    note = fields.Html("Notes")
# Computed fields
    name = fields.Char(
        'Titile',
        compute='_get_name')
    invoice_ids = fields.Many2many(
        'account.invoice',
        string="Invoices",
        compute="_get_data")
    document_class_ids = fields.Many2many(
        'afip.document_class',
        string="Document Classes",
        compute="_get_data")
    tax_code_ids = fields.Many2many(
        'account.tax.code',
        string="Tax Codes",
        compute="_get_data")
    responsability_ids = fields.Many2many(
        'afip.responsability',
        string="Responsabilities",
        compute="_get_data")

    @api.one
    @api.depends('journal_ids', 'period_id')
    def _get_data(self):
        self.responsability_ids = self.env['afip.responsability'].search([])

        invoices_domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('journal_id', 'in', self.journal_ids.ids),
            ('period_id', '=', self.period_id.id)]
        # Get document classes
        self.document_class_ids = self.env['afip.document_class']
        group_invoices = self.env['account.invoice'].read_group(
            invoices_domain,
            ['id', 'afip_document_class_id'], ['afip_document_class_id'])
        document_class_ids = [
            x['afip_document_class_id'][0] for x in group_invoices]
        self.document_class_ids = document_class_ids

        # Get invoices
        self.invoice_ids = self.env['account.invoice']
        invoices = self.env['account.invoice'].search(invoices_domain)
        self.invoice_ids = invoices

        # Get tax codes
        taxes_domain = [
            ('invoice_id', 'in', invoices.ids),
            ('tax_code_id.parent_id.name', '=', 'IVA')]
        self.tax_code_ids = self.env['account.tax.code']
        group_taxes = self.env['account.invoice.tax'].read_group(
            taxes_domain, ['id', 'tax_code_id'], ['tax_code_id'])
        tax_code_ids = [
            x['tax_code_id'][0] for x in group_taxes]
        self.tax_code_ids = tax_code_ids

    @api.one
    @api.depends('type', 'period_id')
    def _get_name(self):
        if self.type == 'sale':
            ledger_type = _('Sales')
        elif self.type == 'purchase':
            ledger_type = _('Purchases')
        name = _("%s VAT Ledger %s") % (ledger_type, self.period_id.name)
        self.name = name

    @api.one
    @api.constrains('presented_ledger', 'last_page', 'state')
    def _check_state(self):
        if self.state == 'presented':
            if not self.presented_ledger:
                raise Warning(
                    _('To set "Presented" you must upload the "Presented Ledger" first'))
            elif not self.last_page:
                raise Warning(
                    _('To set "Presented" you must set the "Last Page" first'))

    @api.onchange('company_id')
    def change_company(self):
        now = time.strftime('%Y-%m-%d')
        company_id = self.company_id.id
        domain = [('company_id', '=', company_id),
                  ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1)
        self.fiscalyear_id = fiscalyears
        if self.type == 'sale':
            domain = [('type', 'in', ['sale', 'sale_refund'])]
        elif self.type == 'purchase':
            domain = [('type', 'in', ['purchase', 'purchase_refund'])]
        domain += [
            ('use_documents', '=', True),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', 'child_of', self.company_id.id)]
        journals = self.env['account.journal'].search(domain)
        self.journal_ids = journals

    @api.onchange('fiscalyear_id')
    def change_fiscalyear(self):
        vat_ledgers = self.search(
            [('company_id', '=', self.company_id.id),
             ('fiscalyear_id', '=', self.fiscalyear_id.id),
             ('type', '=', self.type)],
            order='period_id desc', limit=1)
        if vat_ledgers:
            next_period = self.env['account.period'].with_context(
                company_id=self.company_id.id).next(vat_ledgers.period_id, 1)
        else:
            next_period = self.env['account.period'].search(
                [('company_id', '=', self.company_id.id),
                 ('fiscalyear_id', '=', self.fiscalyear_id.id)], limit=1)
        self.period_id = next_period
        self.first_page = self.last_page

    @api.multi
    def action_present(self):
        self.state = 'presented'

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'

    @api.multi
    def action_to_draft(self):
        self.state = 'draft'

    @api.multi
    def action_print(self):
        assert len(
            self) == 1, 'This option should only be used for a single id at a time.'
        return self.env['report'].get_action(self, 'report_account_vat_ledger')

    # Range label (dates or periods)
    #     range_label = ''

    # Company
    #     if wizard.company_id:
    #         filters.append(('company_id', '=', wizard.company_id.id))
    # Fiscal year
    #     if wizard.fiscalyear_id:
    #         filters.append(
    #             ('period_id.fiscalyear_id', '=', wizard.fiscalyear_id.id))

    # Period From
    #     if wizard.period_from:
    #         filters.append(('period_id.id', '>=', wizard.period_from.id))
    #         range_label = 'Periodo ' + wizard.period_from.name

    # Period From
    #     if wizard.period_to:
    #         filters.append(('period_id.id', '<=', wizard.period_to.id))
    #         range_label += ' hasta ' + wizard.period_to.name

    # Journals
    #     if wizard.journal_ids:
    #         filters.append(
    #             ('journal_id', 'in', [x.id for x in wizard.journal_ids]))

    # Date From
    #     if wizard.date_from:
    #         filters.append(('date_invoice', '>=', wizard.date_from))
    #         range_label = 'Desde ' + \
    #             self.formatLang(cr, uid, wizard.date_from, context)

    # Date To
    #     if wizard.date_to:
    #         filters.append(('date_invoice', '<=', wizard.date_to))
    #         range_label += ' hasta ' + \
    #             self.formatLang(cr, uid, wizard.date_to, context)

    #     model_ids = obj_model.search(cr, uid, filters, context=context)

    # Report Description
    #     report_type = context.get('report_type', False)
    #     if report_type == 'sale':
    #         report_description = 'Diario IVA Ventas'
    #     elif report_type == 'purchase':
    #         report_description = 'Diario IVA Compras'

    #     no_data_description = ''
    #     if not model_ids:
    # We remove this as we want to print it the same way but with a new message
    # raise osv.except_osv(_('No Data!'),
    # _('There is no data for current filters.'))
    #         no_data_description = 'Sin Movimientos'

    #     company_vat = wizard.company_id.partner_id.printed_vat
    #     company_name = wizard.company_id.name

    #     data['ids'] = model_ids
    #     data['model'] = model
    #     data['variables'] = {'report_description': report_description,
    #                          'range_label': range_label,
    #                          'starting_page': wizard.starting_page,
    #                          'no_data_description': no_data_description,
    #                          'company_name': company_name,
    #                          'company_vat': company_vat,
    #                          'report_type': report_type, }
    #     data['output_type'] = wizard.output_type

    #     return self._print_report(cr, uid, ids, data, context=context)

    # def _print_report(self, cr, uid, ids, data, context=None):

    #     if context is None:
    #         context = {}

    #     return {
    #         'type': 'ir.actions.report.xml',
    #         'report_name': report_name,
    #         'datas': data,
    #     }


    # def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
    #     res = {'value': {}}
    #     if filter == 'filter_no':
    #         res['value'] = {
    #             'period_from': False, 'period_to': False, 'date_from': False, 'date_to': False}
    #     if filter == 'filter_date':
    # res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
    #         res['value'] = {'period_from': False, 'period_to': False, 'date_from': datetime.strftime(date.today(
    #         ) + relativedelta(months=-1), '%Y-%m-01'), 'date_to': datetime.strftime(date.today() + relativedelta(day=1, days=-1), '%Y-%m-%d')}

    #     if filter == 'filter_period' and fiscalyear_id:
    #         start_period = end_period = False
    #         cr.execute('''
    #             SELECT * FROM (SELECT p.id
    #                            FROM account_period p
    #                            LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
    #                            WHERE f.id = %s
    #                            AND p.special = false
    #                            ORDER BY p.date_start ASC, p.special ASC
    #                            LIMIT 1) AS period_start
    #             UNION ALL
    #             SELECT * FROM (SELECT p.id
    #                            FROM account_period p
    #                            LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
    #                            WHERE f.id = %s
    #                            AND p.date_start < NOW()
    #                            AND p.special = false
    #                            ORDER BY p.date_stop DESC
    #                            LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
    #         periods = [i[0] for i in cr.fetchall()]
    #         if periods and len(periods) > 1:
    #             start_period = periods[0]
    #             end_period = periods[1]
    #         res['value'] = {'period_from': start_period, 'period_to':
    #                         end_period, 'date_from': False, 'date_to': False}
    #     return res



    # This function was copied from server report_sxw.py
    # def formatLang(self, cr, uid, value, context=None):
    #     if not str(value):
    #         return ''

    #     pool_lang = self.pool.get('res.lang')
    #     lang = context.get('lang', 'en_US') or 'en_US'
    #     lang_ids = pool_lang.search(cr, uid, [('code', '=', lang)])[0]
    #     lang_obj = pool_lang.browse(cr, uid, lang_ids)
    #     date_format = lang_obj.date_format
    #     parse_format = DEFAULT_SERVER_DATE_FORMAT

    #     if isinstance(value, basestring):
    # FIXME: the trimming is probably unreliable if format includes day/month names
    # and those would need to be translated anyway.
    #         date = datetime.strptime(
    #             value[:get_date_length(parse_format)], parse_format)
    #     elif isinstance(value, time.struct_time):
    #         date = datetime(*value[:6])
    #     else:
    #         date = datetime(*value.timetuple()[:6])
    #     return date.strftime(date_format)
