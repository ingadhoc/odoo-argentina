# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import netsvc
import time


class account_check_sold(osv.osv_memory):
    _name = 'account.check.sold'

    _columns = {
        'sold_date': fields.date('Sold Date', required=True),
        'expense_account': fields.many2one('account.account','Expense Account', domain=[('type','<>','view'), ('type', '<>', 'closed')],),
        'expense_amount': fields.float('Expense Amount'),
        'destiny_account_id': fields.many2one('account.account','Destiny Account', required=True, domain=[('type','<>','view'), ('type', '<>', 'closed')],),
        'expense': fields.selection([('without_expense','Without Expenses'),
                                ('record_expenses','Record Expenses')], string='Expenses', required=True),

        # 'bank_account_id': fields.many2one('res.partner.bank', 'Bank Account',required=True),
    }

    def action_sold(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])
        
        third_check = self.pool.get('account.third.check')
        check_objs = third_check.browse(cr, uid, record_ids, context=context)

        wf_service = netsvc.LocalService('workflow')
        #invoice_obj = self.pool.get('account.invoice')
        move_line = self.pool.get('account.move.line')
        #invoice_line_obj = self.pool.get('account.invoice.line')
        wizard = self.browse(cr, uid, ids[0], context=context)

        period_id = self.pool.get('account.period').find(cr, uid,wizard.sold_date)[0]

        for check in check_objs:
            if not (check.voucher_id.journal_id.default_credit_account_id.id or check.voucher_id.journal_id.default_debit_account_id.id):
                raise osv.except_osv('Journal %s selected error' % (check.voucher_id.journal_id.id),
                    'The journal must to be created defaults account for debit and credit.' )
                                        
            if not check.amount > wizard.expense_amount:
                 raise osv.except_osv('Check %s selected error' % (check.number),
                    'The expense amount must to be minor than check amount.'
                     )
                
            if check.state != 'holding':
                raise osv.except_osv('Check %s selected error' % (check.number),
                    'The selected checks must to be in holding.'
                     )

            # if  wizard.expense_amount != 0.00  and wizard.expense_account:
            name = self.pool.get('ir.sequence').next_by_id(cr, uid, check.voucher_id.journal_id.sequence_id.id, context=context)
            move_id = self.pool.get('account.move').create(cr, uid, {
                                                    'name': name,
                                                    'journal_id': check.voucher_id.journal_id.id,
                                                    'state': 'draft',
                                                    'period_id': period_id,
                                                    'date': wizard.sold_date,
                                                    'ref': 'Check Sold Nr. ' + check.number,
                    })
            #debit 
            # If expense and expense ammount defined we create de expense 
            if  wizard.expense == 'record_expenses' and wizard.expense_amount != 0.00:
                move_line.create(cr, uid, {
                            'name': name,
                            'centralisation': 'normal',
                            'account_id': wizard.expense_account.id,
                            'move_id': move_id,
                            'journal_id': check.voucher_id.journal_id.id,
                            'period_id': period_id,
                            'date': wizard.sold_date,
                            'debit': wizard.expense_amount,
                            'credit': 0.0,
                            'ref': 'Check Sold Nr. ' + check.number,
                            'state': 'valid',
                        })              
            #debit         
            move_line.create(cr, uid, {
                        'name': name,
                        'centralisation': 'normal',
                        'account_id': wizard.destiny_account_id.id,
                        # 'account_id': wizard.bank_account_id.account_id.id,
                        'move_id': move_id,
                        'journal_id': check.voucher_id.journal_id.id,
                        'period_id': period_id,
                        'debit': check.amount - wizard.expense_amount,
                        'credit': 0.0,
                        'ref': 'Check Sold Nr. ' + check.number,
                        'state': 'valid',
                    })
            #credit 
            move_line.create(cr, uid, {
                        'name': name,
                        'centralisation': 'normal',
                        'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                        'move_id': move_id,
                        'journal_id': check.voucher_id.journal_id.id,
                        'period_id': period_id,
                        'debit': 0.0,
                        'credit':check.amount,
                        'ref': 'Check Sold Nr. ' + check.number,
                        'state': 'valid',
                    })
            self.pool.get('account.move').write(cr, uid, [move_id], {
                        'state': 'posted',
                    })

            wf_service.trg_validate(uid, 'account.third.check', check.id,
                'holding_sold', cr)

        return {}

account_check_sold()
