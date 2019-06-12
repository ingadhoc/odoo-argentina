##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
# import time


class AccountVatLedger(models.Model):

    _name = "account.vat.ledger"
    _description = "Account VAT Ledger"
    _inherit = ['mail.thread']
    _order = 'date_from desc'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env[
            'res.company']._company_default_get('account.vat.ledger')
    )
    # fiscalyear_id = fields.Many2one(
    #     'account.fiscalyear', 'Fiscal Year', required=True,
    #     readonly=True, states={'draft': [('readonly', False)]},
    #     help='Keep empty for all open fiscal year')
    type = fields.Selection(
        [('sale', 'Sale'), ('purchase', 'Purchase')],
        "Type",
        required=True
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    journal_ids = fields.Many2many(
        'account.journal', 'account_vat_ledger_journal_rel',
        'vat_ledger_id', 'journal_id',
        string='Journals',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    first_page = fields.Integer(
        "First Page",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    last_page = fields.Integer(
        "Last Page",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    presented_ledger = fields.Binary(
        "Presented Ledger",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    presented_ledger_name = fields.Char(
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('presented', 'Presented'), ('cancel', 'Cancel')],
        'State',
        required=True,
        default='draft'
    )
    note = fields.Html(
        "Notes"
    )
# Computed fields
    name = fields.Char(
        'Titile',
        compute='_compute_name'
    )
    reference = fields.Char(
        'Reference',
    )
    invoice_ids = fields.Many2many(
        'account.invoice',
        string="Invoices",
        compute="_compute_data"
    )
    document_type_ids = fields.Many2many(
        'account.document.type',
        string="Document Classes",
        compute="_compute_data"
    )
    vat_tax_ids = fields.Many2many(
        'account.tax',
        string="VAT Taxes",
        compute="_compute_data"
    )
    other_tax_ids = fields.Many2many(
        'account.tax',
        string="Other Taxes",
        compute="_compute_data"
    )
    afip_responsability_type_ids = fields.Many2many(
        'afip.responsability.type',
        string="AFIP Responsabilities",
        compute="_compute_data"
    )

    @api.model
    def get_tax_groups_columns(self):
        ref = self.env.ref
        # tg_0 = ref('l10n_ar_account.tax_group_iva_0', False)
        tg_21 = ref('l10n_ar_account.tax_group_iva_21', False)
        tg_10 = ref('l10n_ar_account.tax_group_iva_10', False)
        tg_27 = ref('l10n_ar_account.tax_group_iva_27', False)
        tg_25 = ref('l10n_ar_account.tax_group_iva_25', False)
        tg_5 = ref('l10n_ar_account.tax_group_iva_5', False)
        # tg_per_iva = ref('l10n_ar_account.tax_group_percepcion_iva', False)
        return [
            ('IVA 2,5%', tg_25),
            ('IVA 5%', tg_5),
            ('IVA 10.5%', tg_10),
            ('IVA 21%', tg_21),
            ('IVA 27%', tg_27),
            # ('Perc. IVA', tg_per_iva),
        ]

    @api.multi
    @api.depends('journal_ids', 'date_from', 'date_to')
    def _compute_data(self):
        for rec in self:
            rec.afip_responsability_type_ids = rec.env[
                'afip.responsability.type'].search([])

            invoices_domain = [
                # cancel invoices with internal number are invoices
                ('state', '!=', 'draft'),
                ('number', '!=', False),
                # ('internal_number', '!=', False),
                ('journal_id', 'in', rec.journal_ids.ids),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ]

            # Get invoices
            invoices = rec.env['account.invoice'].search(
                # TODO, tal vez directamente podemos invertir el orden, como?
                invoices_domain,
                order='date_invoice asc, document_number asc, number asc, '
                'id asc')
            rec.document_type_ids = invoices.mapped('document_type_id')
            rec.invoice_ids = invoices

            rec.vat_tax_ids = invoices.mapped(
                'vat_tax_ids.tax_id')
            rec.other_tax_ids = invoices.mapped(
                'not_vat_tax_ids.tax_id')

    @api.multi
    @api.depends(
        'type',
        'reference',
    )
    def _compute_name(self):
        date_format = self.env['res.lang']._lang_get(
            self._context.get('lang', 'en_US')).date_format
        for rec in self:
            if rec.type == 'sale':
                ledger_type = _('Sales')
            elif rec.type == 'purchase':
                ledger_type = _('Purchases')
            name = _("%s VAT Ledger %s - %s") % (
                ledger_type,
                rec.date_from and fields.Date.from_string(
                    rec.date_from).strftime(date_format) or '',
                rec.date_to and fields.Date.from_string(
                    rec.date_to).strftime(date_format) or '',
            )
            if rec.reference:
                name = "%s - %s" % (name, rec.reference)
            rec.name = name

    @api.multi
    @api.constrains('presented_ledger', 'last_page', 'state')
    def _check_state(self):
        require_file_and_page = safe_eval(self.env[
            'ir.config_parameter'].sudo().get_param(
            'l10n_ar_vat_ledger.require_file_and_page', 'False'))
        if require_file_and_page:
            for rec in self.filtered(lambda x: x.state == 'presented'):
                if not rec.presented_ledger:
                    raise UserError(_(
                        'To set "Presented" you must upload the '
                        '"Presented Ledger" first'))
                elif not rec.last_page:
                    raise UserError(_(
                        'To set "Presented" you must set'
                        ' the "Last Page" first'))

    @api.onchange('company_id')
    def change_company(self):
        if self.type == 'sale':
            domain = [('type', '=', 'sale')]
        elif self.type == 'purchase':
            domain = [('type', '=', 'purchase')]
        domain += [
            ('use_documents', '=', True),
            ('company_id', '=', self.company_id.id),
        ]
        journals = self.env['account.journal'].search(domain)
        self.journal_ids = journals

    # @api.onchange('fiscalyear_id')
    # def change_fiscalyear(self):
    #     vat_ledgers = self.search(
    #         [('company_id', '=', self.company_id.id),
    #          ('fiscalyear_id', '=', self.fiscalyear_id.id),
    #          ('type', '=', self.type)],
    #         order='period_id desc', limit=1)
    #     if vat_ledgers:
    #         next_period = self.env['account.period'].search(
    #             [('company_id', '=', self.company_id.id),
    #              ('fiscalyear_id', '=', self.fiscalyear_id.id),
    #              ('date_start', '>', vat_ledgers.period_id.date_start),
    #              ], limit=1)
    #     else:
    #         next_period = self.env['account.period'].search(
    #             [('company_id', '=', self.company_id.id),
    #              ('fiscalyear_id', '=', self.fiscalyear_id.id)], limit=1)
    #     self.period_id = next_period
    #     self.first_page = self.last_page

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
        self.ensure_one()
        return self.env['ir.actions.report'].search(
            [('report_name', '=', 'report_account_vat_ledger')],
            limit=1).report_action(self)
