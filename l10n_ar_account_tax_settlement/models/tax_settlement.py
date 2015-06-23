# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning


class tax_settlement(models.Model):
    _name = 'account.tax.settlement'
    _description = 'Account Tax Settlement'
    _inherit = ['mail.thread']
    _order = 'period_id desc'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env[
            'res.company']._company_default_get('account.tax.settlement')
        )
    fiscalyear_id = fields.Many2one(
        'account.fiscalyear', 'Fiscal Year', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        )
    # type = fields.Selection(
    #     [('sale', 'Sale'), ('purchase', 'Purchase')],
    #     "Type", required=True)
    period_id = fields.Many2one(
        'account.period', 'Period', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help='Keep empty for all periods on fiscal year',
        )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        domain=[('type', '=', 'general'), ('tax_code_id', '!=', False)],
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    # journal_ids = fields.Many2many(
    #     'account.journal', 'account_vat_ledger_journal_rel',
    #     'vat_ledger_id', 'journal_id', string='Journals', required=True,
    #     readonly=True, states={'draft': [('readonly', False)]},
    #     )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('presented', 'Presented'),
        ('cancel', 'Cancel')],
        'State',
        required=True,
        default='draft'
        )
    note = fields.Html("Notes")
# Computed fields
    name = fields.Char(
        'Title',
        compute='_get_name')
    # move_line_ids = fields.Many2many(
    #     'account.move.line',
    #     string="Move Lines",
    #     compute="_get_data"
    #     )
    # invoice_ids = fields.Many2many(
    #     'account.invoice',
    #     string="Invoices",
    #     compute="_get_data")
    # document_class_ids = fields.Many2many(
    #     'afip.document_class',
    #     string="Document Classes",
    #     compute="_get_data")
    # vat_tax_code_ids = fields.Many2many(
    #     'account.tax.code',
    #     string="VAT Tax Codes",
    #     compute="_get_data")
    # other_tax_code_ids = fields.Many2many(
    #     'account.tax.code',
    #     string="Other Tax Codes",
    #     compute="_get_data")
    # responsability_ids = fields.Many2many(
    #     'afip.responsability',
    #     string="Responsabilities",
    #     compute="_get_data")
    # other_taxes_base = fields.Float(
    #     string="Other Taxes Base",
    #     help="Base Amount for taxes without tax code",
    #     compute="_get_data")
    # other_taxes_amount = fields.Float(
    #     string="Other Taxes Amount",
    #     help="Amount for taxes without tax code",
    #     compute="_get_data")
    moves_state = fields.Selection(
        [('draft', 'Unposted'), ('posted', 'Posted')],
        'Moves Status',
        required=True,
        readonly=True,
        default='posted',
        states={'draft': [('readonly', False)]},
        )
    tax_settlement_detail_ids = fields.One2many(
        'account.tax.settlement.detail',
        'tax_settlement_id',
        'Detail',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )

    @api.one
    @api.constrains('company_id', 'journal_id')
    def check_company(self):
        if self.company_id != self.journal_id.company_id:
            raise Warning(_('Tax settlement company and journal company must be the same'))

    @api.one
    @api.depends('period_id', 'fiscalyear_id')
    # @api.depends('type', 'period_id')
    def _get_name(self):
        name = _('Tax Settlment %s') % (
            self.period_id.name or self.fiscalyear_id.name)
        self.name = name

    # @api.one
    # # Sacamos el depends por un error con el cache en esqume multi cia al
    # # cambiar periodo de una cia hija con usuario distinto a admin
    # # @api.depends('journal_ids', 'period_id')
    # def _get_data(self):
    #     domain = [
    #         ('tax_code_id', 'child_of', self.journal_id.tax_code_id.id),
    #         ('move_id.state', '=', self.moves_state),
    #         ]
    #     if self.period_id:
    #         domain.append(('period_id', '=', self.period_id.id))
    #     else:
    #         domain.append(
    #             ('period_id.fiscalyear_id', '=', self.fiscalyear_id.id))
    #     move_lines = self.env['account.move.line'].search(domain)
    #     self.move_line_ids = move_lines

    @api.one
    # Sacamos el depends por un error con el cache en esqume multi cia al
    # cambiar periodo de una cia hija con usuario distinto a admin
    # @api.depends('journal_ids', 'period_id')
    def compute(self):
        actual_tax_code_ids = [
            x.tax_code_id.id for x in self.tax_settlement_detail_ids]
        for tax_code in self.env['tax.code'].search([
                ('id', 'child_of', self.journal_id.tax_code_id.id),
                ('id', '!=', actual_tax_code_ids),
                ]):
            self.tax_settlement_detail_ids.create({
                'tax_code_id': tax_code.id,
                'tax_settlement_id': self.id,
                })
        # domain = [
        #     ('tax_code_id', 'child_of', self.journal_id.tax_code_id.id),
        #     ('move_id.state', '=', self.moves_state),
        #     ]
        # if self.period_id:
        #     domain.append(('period_id', '=', self.period_id.id))
        # else:
        #     domain.append(
        #         ('period_id.fiscalyear_id', '=', self.fiscalyear_id.id))
        # move_lines = self.env['account.move.line'].search(domain)
        # self.move_line_ids = move_lines


class tax_settlement_detail(models.Model):
    _name = 'account.tax.settlement.detail'
    _description = 'Account Tax Settlement Detail'

    tax_settlement_id = fields.Many2one(
        'Tax Settlement',
        required=True,
        ondelete='cascade',
        )
    tax_code_id = fields.Many2many(
        'account.tax.code',
        required=True,
        'Tax Code',
        )
    move_line_ids = fields.One2many(
        'account.move.line',
        'tax_settlement_detail_id',
        string="Move Lines",
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
