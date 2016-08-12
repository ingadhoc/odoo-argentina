# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import time


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
        _('Titile'),
        compute='_get_name')
    reference = fields.Char(
        'Reference',)
    invoice_ids = fields.Many2many(
        'account.invoice',
        string=_("Invoices"),
        compute="_get_data")
    document_class_ids = fields.Many2many(
        'afip.document_class',
        string=_("Document Classes"),
        compute="_get_data")
    vat_tax_code_ids = fields.Many2many(
        'account.tax.code',
        string=_("VAT Tax Codes"),
        compute="_get_data")
    other_tax_code_ids = fields.Many2many(
        'account.tax.code',
        string=_("Other Tax Codes"),
        compute="_get_data")
    responsability_ids = fields.Many2many(
        'afip.responsability',
        string=_("Responsabilities"),
        compute="_get_data")

    @api.one
    # Sacamos el depends por un error con el cache en esqume multi cia al
    # cambiar periodo de una cia hija con usuario distinto a admin
    # @api.depends('journal_ids', 'period_id')
    def _get_data(self):
        self.responsability_ids = self.env['afip.responsability'].search([])

        invoices_domain = [
            # ('state', 'not in', ['draft', 'cancel']),
            # cancel invoices with internal number are invoices
            ('state', '!=', 'draft'),
            ('internal_number', '!=', False),
            ('journal_id', 'in', self.journal_ids.ids),
            ('period_id', '=', self.period_id.id)]

        # Get invoices
        invoices = self.env['account.invoice'].search(
            invoices_domain, order='date_invoice, afip_document_number')
        self.document_class_ids = invoices.mapped('afip_document_class_id')
        self.invoice_ids = invoices

        self.vat_tax_code_ids = invoices.mapped(
            'vat_tax_ids.tax_code_id')
        self.other_tax_code_ids = invoices.mapped(
            'not_vat_tax_ids.tax_code_id')

    @api.one
    @api.depends('type', 'period_id', 'reference')
    def _get_name(self):
        if self.type == 'sale':
            ledger_type = _('Sales')
        elif self.type == 'purchase':
            ledger_type = _('Purchases')
        name = _("%s VAT Ledger %s") % (ledger_type, self.period_id.name)
        if self.reference:
            name = "%s - %s" % (name, self.reference)
        self.name = name

    @api.one
    @api.constrains('presented_ledger', 'last_page', 'state')
    def _check_state(self):
        if self.state == 'presented':
            if not self.presented_ledger:
                raise Warning(_(
                    'To set "Presented" you must upload the '
                    '"Presented Ledger" first'))
            elif not self.last_page:
                raise Warning(_(
                    'To set "Presented" you must set the "Last Page" first'))

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
            # No tomamos los diarios de las cias hijas
            # '|',
            ('company_id', '=', self.company_id.id),
            # ('company_id', 'child_of', self.company_id.id)
            ]
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
            next_period = self.env['account.period'].search(
                [('company_id', '=', self.company_id.id),
                 ('fiscalyear_id', '=', self.fiscalyear_id.id),
                 ('date_start', '>', vat_ledgers.period_id.date_start),
                 ], limit=1)
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
        self.ensure_one
        return self.env['report'].get_action(self, 'report_account_vat_ledger')
