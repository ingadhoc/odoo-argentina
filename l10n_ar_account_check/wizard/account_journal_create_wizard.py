# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, api, models, _


class account_journal_create_wizard(models.TransientModel):
    _inherit = 'account.journal.create.wizard'

    type = fields.Selection(
        selection_add=[
            ('issue_check', _('Issue Check')),
            ('third_check', _('Third Check')),
            ],
        )

    @api.multi
    def _get_vals(self, invoice_subtype=False):
        # TODO mejorar para que no haya ue sobreescribir tantas cosas
        vals = super(account_journal_create_wizard, self)._get_vals(
            invoice_subtype)
        if self.type in ('issue_check', 'third_check'):
            if self.type == 'issue_check':
                domain = [('payment_subtype', '=', 'issue_check')]
                payment_subtype = 'issue_check'
                code = _('CHP')
                name = _('Cheques Propios')
                journal_type = 'bank'
            elif self.type == 'third_check':
                payment_subtype = 'third_check'
                domain = [('payment_subtype', '=', 'third_check')]
                code = _('CHT')
                name = _('Cheques Terceros')
                journal_type = 'bank'
            domain += [
                ('type', '=', journal_type),
                ('company_id', '=', self.company_id.id)]
            journals = self.env['account.journal'].search(domain)
            next_number = len(journals) + 1

            if self.currency_id:
                name = '%s %s' % (name, self.currency_id.name)

            account_name = name
            if self.name_sufix:
                name = '%s (%s)' % (name, self.name_sufix)
                account_name = '%s %s' % (account_name, self.name_sufix)

            # if none, we create one and use for debit credit
            if not self.default_debit_account_id and not (
                    self.default_credit_account_id):
                account = self.env['account.account'].create(
                    self._get_account_vals(account_name))
                self.default_credit_account_id = account.id
                self.default_debit_account_id = account.id
            # if not debit, we use credit
            elif not self.default_credit_account_id:
                self.default_credit_account_id = self.default_debit_account_id
            # if not credit, we use debit
            elif not self.default_debit_account_id:
                self.default_debit_account_id = self.default_credit_account_id

            vals.update({
                'type': journal_type,
                'name': name,
                'validate_only_checks': True,
                'payment_subtype': payment_subtype,
                'code': '%s%02d' % (code, next_number),
                'default_credit_account_id': self.default_credit_account_id.id,
                'default_debit_account_id': self.default_debit_account_id.id,
            })
        return vals
