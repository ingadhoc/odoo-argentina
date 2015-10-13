# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, api, models, _
from openerp.exceptions import Warning


class account_journal_create_wizard(models.TransientModel):
    _name = 'account.journal.create.wizard'

    @api.model
    def get_company(self):
        return self.env['res.company'].browse(self._context.get('active_id'))

    company_id = fields.Many2one(
        'res.company',
        required=True,
        readonly=True,
        default=get_company,
        ondelete='cascade',
        )
    group_invoice_lines = fields.Boolean(
        'Group Invoice Lines',
        default=True,
        help="If this box is checked, the system will try to group the "
        "accounting lines when generating them from invoices.",
        )
    update_posted = fields.Boolean(
        'Allow Cancelling',
        default=True,
        help="Check this box if you want to allow the cancellation the "
        "entries related to this journals or of the invoice related to this "
        "journals"
        )
    allow_date = fields.Boolean(
        'Date in Period',
        default=True,
        help="If checked, the entry won\'t be created if the entry date is "
        "not included into the selected period"
        )
    invoice_subtype = fields.Selection([
        ('only_invoice', 'Only Invoice'),
        ('only_refund', 'Only Refund'),
        ('invoice_and_refund', 'Invoice and Refund'),
        ],
        'Subtype',
        default='invoice_and_refund',
        )
    name_sufix = fields.Char(
        'Name Sufix',
        )
    use_documents = fields.Boolean(
        'Use Documents?'
        )
    point_of_sale_id = fields.Many2one(
        'afip.point_of_sale',
        'Point Of Sale',
        )
    type = fields.Selection([
        ('sale', 'Sale'),
        # ('sale_refund','Sale Refund'),
        ('purchase', 'Purchase'),
        # ('purchase_refund','Purchase Refund'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        # we move this to l10n_ar_account_check
        # ('issue_check', 'Issue Check'),
        # ('third_check', 'Third Check'),
        # ('general', 'General'),
        # ('situation', 'Opening/Closing Situation')
        ],
        'Type',
        required=True,
        )
    currency_id = fields.Many2one(
        'res.currency',
        'Currency'
        )
    account_user_type_id = fields.Many2one(
        'account.account.type',
        'Account Type',
        help=(
            'It will be used for the new account created. If you choose a '
            'parent account, then you must also select an account type')
        )
    parent_account_id = fields.Many2one(
        'account.account',
        string="Parent Account",
        domain="[('type', '=', 'view'), ('company_id', '=', company_id)]",
        help=(
            "If you dont choose parent account, then we will search for one of"
            " type liquidity and use this for type and the parent for parent.")
        )
    default_credit_account_id = fields.Many2one(
        'account.account',
        string="Default Credit Account",
        help="If not configured for bank/cash journals it will be created"
        )
    default_debit_account_id = fields.Many2one(
        'account.account',
        string="Default Debit Account",
        help="If not configured for bank/cash journals it will be created"
        )

    @api.multi
    def action_confirm(self):
        """
        """
        self.ensure_one()
        self._create_journals()
        return True

    @api.onchange('company_id', 'type')
    def change_company(self):
        if self.type not in ('sale', 'purchase'):
            self.use_documents = False
        else:
            self.use_documents = self.company_id.use_argentinian_localization

    @api.onchange('point_of_sale_id', 'type')
    def change_point_of_sale(self):
        if self.type == 'sale':
            self.name_sufix = self.point_of_sale_id.name
        else:
            self.name_sufix = False

    @api.multi
    def _get_vals(self, invoice_subtype=False):
        vals = {}
        domain = [
            ('company_id', '=', self.company_id.id),
            ]

        journal_type = False
        name = ''
        code = ''
        if self.type == 'bank':
            code = _('BAN')
            name = _('Banco')
            journal_type = 'bank'
        elif self.type == 'cash':
            code = _('CAJ')
            name = _('Caja')
            journal_type = 'cash'
        elif self.type == 'purchase':
            if invoice_subtype == 'refund':
                journal_type = 'purchase_refund'
                code = _('RCO')
                name = _('Reembolso Compras')
            else:
                journal_type = 'purchase'
                code = _('COM')
                name = _('Compras')
        elif self.type == 'sale':
            if invoice_subtype == 'refund':
                vals['point_of_sale_id'] = self.point_of_sale_id.id
                journal_type = 'sale_refund'
                code = _('RVE')
                name = _('Reembolso Ventas')
            else:
                vals['point_of_sale_id'] = self.point_of_sale_id.id
                journal_type = 'sale'
                code = _('VEN')
                name = _('Ventas')

        domain.append(('type', '=', journal_type))

        if self.type in ('sale', 'purchase'):
            vals['use_documents'] = self.use_documents
            vals['group_invoice_lines'] = self.group_invoice_lines

        journals = self.env['account.journal'].search(domain)
        if self.point_of_sale_id and self.type == 'sale':
            next_number = self.point_of_sale_id.number
        else:
            next_number = len(journals) + 1

        if self.currency_id:
            name = '%s %s' % (name, self.currency_id.name)

        account_name = name
        if self.name_sufix:
            name = '%s (%s)' % (name, self.name_sufix)
            account_name = '%s %s' % (account_name, self.name_sufix)

        if journal_type in ('bank', 'cash'):
            # if none, we create one and use for debit credit
            if (
                    not self.default_debit_account_id and
                    not self.default_credit_account_id
                    ):
                account = self.env['account.account'].create(
                    self._get_account_vals(account_name))
                self.default_debit_account_id = account.id
                self.default_credit_account_id = account.id
            # if not debit, we use credit
            elif not self.default_credit_account_id:
                self.default_credit_account_id = self.default_debit_account_id
            # if not credit, we use debit
            elif not self.default_debit_account_id:
                self.default_debit_account_id = self.default_credit_account_id

        vals.update({
            'type': journal_type,
            'name': name,
            'code': '%s%02d' % (code, next_number),
            'company_id': self.company_id.id,
            'allow_date': self.allow_date,
            'update_posted': self.update_posted,
            'currency': self.currency_id.id,
            # TODO ver si queremos implementar analytic journal
            # 'analytic_journal_id': _get_analytic_journal(journal_type),
            'default_credit_account_id': self.default_credit_account_id.id,
            'default_debit_account_id': self.default_debit_account_id.id,
        })

        # check if journal sequence is installed
        if 'sequence' in journals.fields_get():
            last_journal = self.env['account.journal'].search(
                domain, order='sequence desc', limit=1)
            sequence = last_journal and last_journal.sequence + 10 or 10
            vals['sequence'] = sequence
        return vals

    @api.multi
    def _create_journals(self):
        self.ensure_one()
        if self.type in ('sale', 'purchase'):
            if self.invoice_subtype == 'invoice_and_refund':
                invoice_subtypes = ['invoice', 'refund']
            elif self.invoice_subtype == 'only_refund':
                invoice_subtypes = ['refund']
            else:
                invoice_subtypes = ['invoice']
            for invoice_subtype in invoice_subtypes:
                self.env['account.journal'].create(
                    self._get_vals(invoice_subtype))
        else:
            self.env['account.journal'].create(self._get_vals())
        return True

    @api.multi
    def _get_account_vals(self, account_name):
        self.ensure_one()

        parent_account = self.parent_account_id
        account_user_type = self.account_user_type_id
        if parent_account and not account_user_type:
            raise Warning(_(
                'If you set a parent acount you must also set a user type'))
        if not parent_account:
            account = self.env['account.account'].search([
                ('type', '=', 'liquidity'),
                ('company_id', '=', self.company_id.id),
                ('parent_id', '!=', False)], limit=1)
            parent_account = account.parent_id
            if not account_user_type:
                account_user_type = account.user_type

        # No liquidity account exists, no template available
        if not parent_account:
            raise Warning(_('No Parent Account Found for Bank/Cash Accounts!'))

        current_num = 10

        while True:
            new_code = "%s%03d" % (parent_account.code[:-3], current_num)
            account = self.env['account.account'].search([
                ('code', '=', new_code),
                ('company_id', '=', self.company_id.id)])
            if not account:
                break
            current_num += 10
        vals = {
            'name': account_name,
            'code': new_code,
            'type': 'liquidity',
            'user_type': account_user_type.id,
            'reconcile': False,
            'parent_id': parent_account.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
        }
        return vals
