# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, api, models, _
from openerp.exceptions import Warning


class account_journal_create_wizard(models.TransientModel):
    _inherit = 'account.journal.create.wizard'

    type = fields.Selection(
        selection_add=[
            ('issue_check', 'Issue Check'),
            ('third_check', 'Third Check'),
            ],
        )

    @api.multi
    def _get_vals(self, invoice_subtype=False):
        # TODO mejorar para que no haya ue sobreescribir tantas cosas
        vals = super(account_journal_create_wizard, self)._get_vals(
            invoice_subtype)
        if self.type in ('issue_check', 'third_check'):
            if self.type == 'issue_check':
                domain = [('check_type', '=', 'issue')]
                check_type = 'issue'
                code = _('CHP')
                name = _('Cheques Propios')
                journal_type = 'bank'
            elif self.type == 'third_check':
                check_type = 'third'
                domain = [('check_type', '=', 'third')]
                code = _('CHT')
                name = _('Cheques Terceros')
                journal_type = 'bank'
            domain += [
                ('type', '=', journal_type),
                ('company_id', '=', self.company_id.id)]
            journals = self.env['account.journal'].search(domain)
            next_number = len(journals) + 1
            if self.name_sufix:
                name = '%s (%s)' % (name, self.name_sufix)

            vals.update({
                'type': journal_type,
                'name': name,
                'validate_only_checks': True,
                'check_type': check_type,
                'code': '%s%02d' % (code, next_number),
            })
        return vals
