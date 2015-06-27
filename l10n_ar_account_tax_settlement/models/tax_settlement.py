# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
import time


class account_tax_settlement_detail(models.Model):
    _name = 'account.tax.settlement.detail'
    _description = 'Account Tax Settlement Detail'

    tax_settlement_id = fields.Many2one(
        'account.tax.settlement',
        'Tax Settlement',
        required=True,
        ondelete='cascade',
        )
    tax_code_id = fields.Many2one(
        'account.tax.code',
        'Tax Code',
        required=True,
        )
    move_line_ids = fields.One2many(
        'account.move.line',
        'tax_settlement_detail_id',
        string="Move Lines",
        )
    tax_amount = fields.Float(
        'Amount',
        compute='get_amounts',
        )

    @api.one
    def get_move_lines(self):
        settlement = self.tax_settlement_id
        domain = [
            ('tax_code_id', '=', self.tax_code_id.id),
            ('tax_settlement_detail_id', '=', False),
            ]
        self.move_line_ids = False

        if settlement.moves_state == 'posted':
            domain.append(('move_id.state', '=', settlement.moves_state))

        if settlement.filter == 'filter_period':
            # TODO revisar como hacer este filtro
            domain += [
                ('period_id', 'in', settlement.period_ids.ids)]
        elif settlement.filter == 'filter_date':
            domain += [
                ('move_id.date', '>=', settlement.date_from),
                # ('date', '=>', fields.Date.from_string(settlement.date_from)),
                ('move_id.date', '<', settlement.date_to)]
                # ('date', '<', fields.Date.from_string(settlement.date_to))]
        else:
            domain.append(
                ('period_id.fiscalyear_id', '=', settlement.fiscalyear_id.id))
        move_lines = self.env['account.move.line'].search(domain)
        self.move_line_ids = move_lines

    @api.one
    @api.depends('move_line_ids.tax_amount', 'tax_code_id.sign')
    def get_amounts(self):
        self.tax_amount = self.tax_code_id.sign * sum(
            self.move_line_ids.mapped('tax_amount'))


class account_tax_settlement(models.Model):
    _name = 'account.tax.settlement'
    _description = 'Account Tax Settlement'
    _inherit = ['mail.thread']
    # _order = 'period_id desc'

    filter = fields.Selection([
        ('filter_no', 'No Filters'),
        ('filter_date', 'Date'),
        ('filter_period', 'Periods')],
        "Filter by",
        default='filter_no',
        required=True
        )
    period_ids = fields.Many2many(
        'account.period',
        'account_tax_settlement_period_rel',
        'settlement_id', 'period_id',
        'Periods',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    # period_from_id = fields.Many2one(
    #     'account.period',
    #     'Start Period',
    #     readonly=True,
    #     states={'draft': [('readonly', False)]},
    #     )
    # period_to_id = fields.Many2one(
    #     'account.period',
    #     'End Period',
    #     readonly=True,
    #     states={'draft': [('readonly', False)]},
    #     )
    date_from = fields.Date(
        "Start Date"
        )
    date_to = fields.Date(
        "End Date"
        )
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
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        domain=[('type', '=', 'general'), ('tax_code_id', '!=', False)],
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('presented', 'Presented'),
        ('cancel', 'Cancel')],
        'State',
        required=True,
        default='draft'
        )
    note = fields.Html("Notes")
    name = fields.Char(
        'Title',
        compute='_get_name')
    moves_state = fields.Selection(
        [('posted', 'Posted Entries'), ('all', 'All Entries')],
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
    def _get_name(self):
        if self.filter == 'filter_period' and self.period_ids:
            filter_name = ', '.join(self.period_ids.mapped('name'))
        elif self.filter == 'filter_date' and self.date_from and self.date_to:
            filter_name = "%s - %s" % (self.date_from, self.date_to)
        else:
            filter_name = self.fiscalyear_id.name
        name = _('Tax Settlment %s') % (filter_name)
        self.name = name

    @api.one
    def compute(self):
        actual_tax_code_ids = [
            x.tax_code_id.id for x in self.tax_settlement_detail_ids]
        for tax_code in self.env['account.tax.code'].search([
                ('id', 'child_of', self.journal_id.tax_code_id.id),
                ('id', 'not in', actual_tax_code_ids),
                ('type', '!=', 'view'),
                ]):
            self.tax_settlement_detail_ids.create({
                'tax_code_id': tax_code.id,
                'tax_settlement_id': self.id,
                })
        self.tax_settlement_detail_ids.get_move_lines()

    @api.onchange('company_id')
    def change_company(self):
        now = time.strftime('%Y-%m-%d')
        company_id = self.company_id.id
        domain = [('company_id', '=', company_id),
                  ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1)
        self.fiscalyear_id = fiscalyears

    # @api.onchange('fiscalyear_id')
    # def change_fiscalyear(self):
    #     # TODO arreglar este onchange
    #     tax_settlement = self.search(
    #         [('company_id', '=', self.company_id.id),
    #          ('fiscalyear_id', '=', self.fiscalyear_id.id)],
    #         order='period_id desc', limit=1)
    #     if tax_settlement:
    #         next_period = self.env['account.period'].search(
    #             [('company_id', '=', self.company_id.id),
    #              ('fiscalyear_id', '=', self.fiscalyear_id.id),
    #              ('date_start', '>', tax_settlement.period_id.date_start),
    #              ], limit=1)
    #     else:
    #         next_period = self.env['account.period'].search(
    #             [('company_id', '=', self.company_id.id),
    #              ('fiscalyear_id', '=', self.fiscalyear_id.id)], limit=1)
    #     self.period_id = next_period
