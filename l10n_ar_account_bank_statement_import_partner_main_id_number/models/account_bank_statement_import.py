# -*- coding: utf-8 -*-
# © 2018 Ivan Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        stmts_vals = super(AccountBankStatementImport, self)._complete_stmts_vals(stmts_vals, journal, account_number)
        for st_vals in stmts_vals:
            for line_vals in st_vals['transactions']:
                if not line_vals.get('partner_id'):
                    # Find the partner by using his main_id_number
                    identifying_string = line_vals.pop('partner_main_id_number')
                    if identifying_string:
                        partner = self.env['res.partner'].search([('main_id_number', '=', identifying_string)])
                        if len(partner) == 1:
                            line_vals['partner_id'] = partner.id
        return stmts_vals
