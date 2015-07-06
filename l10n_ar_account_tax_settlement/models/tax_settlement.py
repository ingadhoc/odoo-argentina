# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
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
        # TODO hacerlo m2m y verificar que a la hora de generar el asiento no se haya usado ya
        'account.move.line',
        'tax_settlement_detail_id',
        string="Move Lines",
        )
    tax_amount = fields.Float(
        'Tax Amount',
        compute='get_amounts',
        digits_compute=dp.get_precision('Account'),
        )
    debit_amount = fields.Float(
        'Debit Amount',
        compute='get_amounts',
        digits_compute=dp.get_precision('Account'),
        )
    credit_amount = fields.Float(
        'Credit Amount',
        compute='get_amounts',
        digits_compute=dp.get_precision('Account'),
        )

    @api.one
    def get_move_lines(self):
        settlement = self.tax_settlement_id
        domain = [
            ('tax_code_id', '=', self.tax_code_id.id),
            # unreconciled entries
            ('reconcile_id', '=', False),
            # only accounts that can reconcile
            ('account_id.reconcile', '=', True),
            ]
        self.move_line_ids = False

        if settlement.moves_state != 'all':
            domain.append(('move_id.state', '=', settlement.moves_state))

        if settlement.filter == 'filter_period':
            domain += [
                ('period_id', 'in', settlement.period_ids.ids)]
        elif settlement.filter == 'filter_date':
            domain += [
                ('move_id.date', '>=', settlement.date_from),
                ('move_id.date', '<', settlement.date_to)]
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
        self.credit_amount = sum(
            self.move_line_ids.mapped('credit'))
        self.debit_amount = sum(
            self.move_line_ids.mapped('debit'))

    @api.multi
    def prepare_line_values(self):
        self.ensure_one()
        res = []
        grouped_lines = self.move_line_ids.read_group(
            domain=[('id', 'in', self.move_line_ids.ids)],
            fields=['id', 'debit', 'credit', 'tax_amount', 'account_id'],
            groupby=['account_id'],
            )

        for line in grouped_lines:
            if not line['tax_amount'] and line['debit'] == line['credit']:
                continue

            debit = 0.0
            credit = 0.0
            if line['credit'] > line['debit']:
                debit = line['credit'] - line['debit']
            else:
                credit = line['debit'] - line['credit']

            vals = {
                'name': self.tax_settlement_id.name,
                'debit': debit,
                'credit': credit,
                'account_id': line['account_id'][0],
                'tax_code_id': self.tax_code_id.id,
                'tax_amount': -1.0 * line['tax_amount'],
            }
            res.append(vals)
        return res


class account_tax_settlement(models.Model):
    _name = 'account.tax.settlement'
    _description = 'Account Tax Settlement'
    _inherit = ['mail.thread']
    # _order = 'period_id desc'

    tax_codes_count = fields.Float(
        '# Tax Codes',
        compute='_get_tax_codes_count',
        )
    balance_amount = fields.Float(
        'Balance Amount',
        compute='_get_balance',
        digits_compute=dp.get_precision('Account'),
        )
    balance_tax_amount = fields.Float(
        'Balance Tax Amount',
        compute='_get_balance',
        digits_compute=dp.get_precision('Account'),
        )
    balance_account_id = fields.Many2one(
        'account.account',
        'Balance Account',
        compute='_get_balance',
        digits_compute=dp.get_precision('Account'),
        )
    balance_tax_code_id = fields.Many2one(
        'account.tax.code',
        'Balance Tax Code',
        compute='_get_balance',
        digits_compute=dp.get_precision('Account'),
        )
    move_line_ids = fields.One2many(
        related='move_id.line_id',
        readonly=True,
        )
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        ondelete='restrict',
        copy=False,
        help="Link to the automatically generated Journal Items."
        )
    filter = fields.Selection([
        ('filter_no', 'No Filters'),
        ('filter_date', 'Date'),
        ('filter_period', 'Periods')],
        "Filter by",
        default='filter_no',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    date = fields.Date(
        'Date',
        help='Date to be used on created move',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    period_id = fields.Many2one(
        'account.period',
        help='Period to be used on created move',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    period_ids = fields.Many2many(
        'account.period',
        'account_tax_settlement_period_rel',
        'settlement_id', 'period_id',
        'Periods',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    date_from = fields.Date(
        "Start Date",
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    date_to = fields.Date(
        "End Date",
        readonly=True,
        states={'draft': [('readonly', False)]},
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
    note = fields.Html(
        'Notes'
        )
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
    @api.depends('tax_settlement_detail_ids')
    def _get_tax_codes_count(self):
        self.tax_codes_count = len(self.tax_settlement_detail_ids)

    @api.one
    @api.depends('tax_settlement_detail_ids')
    def _get_balance(self):
        credit_amount = sum(
            self.tax_settlement_detail_ids.mapped('credit_amount'))
        debit_amount = sum(
            self.tax_settlement_detail_ids.mapped('debit_amount'))
        balance_tax_amount = sum(
            self.tax_settlement_detail_ids.mapped('tax_amount'))
        balance_amount = credit_amount - debit_amount
        if balance_amount <= 0:
            balance_account = self.journal_id.default_credit_account_id
            balance_tax_code = self.journal_id.default_credit_tax_code_id
        else:
            balance_account = self.journal_id.default_debit_account_id
            balance_tax_code = self.journal_id.default_debit_tax_code_id
        self.balance_amount = balance_amount
        self.balance_account_id = balance_account.id
        self.balance_tax_code_id = balance_tax_code.id
        self.balance_tax_amount = balance_tax_amount

    @api.multi
    def action_present(self):
        self.create_move()

    @api.one
    def action_cancel(self):
        move = self.move_id

        # unreconcile
        self.refresh()
        reconcile_reads = self.env['account.move.line'].read_group(
            domain=[
                ('id', 'in', self.move_line_ids.ids),
                ('reconcile_id', '!=', False)],
            fields=['id', 'reconcile_id'],
            groupby=['reconcile_id'])
        for line in reconcile_reads:
            self.env['account.move.reconcile'].browse(
                line['reconcile_id'][0]).unlink()

        self.move_id = False
        move.unlink()
        self.state = 'cancel'

    @api.multi
    def action_to_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def get_final_line_vals(self):
        res = {}
        if not self.journal_id.partner_id:
            raise Warning(_(
                'No Partner configured on journal'))
        if not self.balance_account_id:
            raise Warning(_(
                'No Balance account configured on journal'))
        for line in self:
            debit = 0.0
            credit = 0.0
            balance_amount = self.balance_amount
            if balance_amount < 0:
                debit = balance_amount
            else:
                credit = balance_amount
            vals = {
                'partner_id': self.journal_id.partner_id.id,
                'name': self.name,
                'debit': debit,
                'credit': credit,
                'account_id': self.balance_account_id.id,
                'tax_code_id': self.balance_tax_code_id.id,
                'tax_amount': self.balance_tax_amount,
            }
            res[self.id] = vals
        return res

    @api.one
    def create_move(self):
        if not self.period_id or not self.date:
            raise Warning('not implemented! you must configure date and period')

        if not self.journal_id.sequence_id:
            raise Warning(_('Please define a sequence on the journal.'))
        name = self.journal_id.sequence_id._next()
        move_line_env = self.env['account.move.line']
        move_vals = {
            'ref': self.name,
            'name': name,
            'period_id': self.period_id.id,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            }
        move = self.move_id.create(move_vals)
        created_move_line_ids = []
        debit = 0.0
        credit = 0.0
        for tax in self:
            for tax in self.tax_settlement_detail_ids:
                for line_vals in tax.prepare_line_values():
                    credit += line_vals['credit']
                    debit += line_vals['debit']
                    line_vals['move_id'] = move.id
                    created_move_line_ids.append(
                        move_line_env.create(line_vals).id)

        final_line_vals = self.get_final_line_vals()[self.id]
        final_line_vals['move_id'] = move.id
        move_line_env.create(final_line_vals)
        to_reconcile_move_lines = move_line_env.browse(
            created_move_line_ids) + self.mapped(
            'tax_settlement_detail_ids.move_line_ids')
        grouped_lines = to_reconcile_move_lines.read_group(
            domain=[('id', 'in', to_reconcile_move_lines.ids)],
            fields=['id', 'account_id'],
            groupby=['account_id'],
            )

        for line in grouped_lines:
            account_id = line['account_id'][0]
            to_reconcile_move_lines.filtered(
                lambda r: r.account_id.id == account_id).reconcile_partial()

        self.write({
            'move_id': move.id,
            'state': 'presented',
            })

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
