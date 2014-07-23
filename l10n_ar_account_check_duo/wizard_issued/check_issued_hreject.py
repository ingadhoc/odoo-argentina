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

class account_issuedcheck_hreject(osv.osv_memory):
    
    _name = 'account.issuedcheck.hreject'
    _description = 'account issued check hreject'
    _columns = {
        'reject_date': fields.date('Reject Date', required=True),
        'expense_account': fields.many2one('account.account','Expense Account'),
        'expense_amount': fields.float('Expense Amount'),
        # 'invoice_expense': fields.boolean('Invoice Expense?'),
        # 'make_expense': fields.boolean('Make Expenses ?'),
        'expense': fields.selection([('without_expense','Without Expenses'),
                                ('supplier_expenses','Supplier Expenses')], string='Expenses', required=True),        
    }

    _defaults = { 
                }
                
                
    def _get_address_invoice(self, cr, uid, partner):
        partner_obj = self.pool.get('res.partner')
        return partner_obj.address_get(cr, uid, [partner],['contact', 'invoice'])
    

    def action_hreject_issued(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])
        third_issued = self.pool.get('account.issued.check')
        check_objs = third_issued.browse(cr, uid, record_ids, context=context)

        third_check = self.pool.get('account.issued.check')
        wf_service = netsvc.LocalService('workflow')
        invoice_obj = self.pool.get('account.invoice')
        move_line = self.pool.get('account.move.line')
        invoice_line_obj = self.pool.get('account.invoice.line')
        wizard = self.browse(cr, uid, ids[0], context=context)

        period_id = self.pool.get('account.period').find(cr, uid,wizard.reject_date)[0]

        for check in check_objs:
            if check.state != 'handed':
                raise osv.except_osv('Check %s selected error' % (check.number),
                    'The selected checks must to be in handed.'
                     )
                     
            if not (check.voucher_id.journal_id.default_credit_account_id.id or check.voucher_id.journal_id.default_debit_account_id.id):
                raise osv.except_osv('Journal %s selected error' % (check.voucher_id.journal_id.id),
                    'The journal must to be created defaults account for debit and credit.' )  
                           
            partner_address = self._get_address_invoice(cr, uid,check.voucher_id.partner_id.id)
            contact_address = partner_address['contact']
            invoice_address = partner_address['invoice']
            invoice_vals = {
                            'name': check.number,
                            'origin': 'Check Rejected Hand Nr. ' + (check.number or '') + ',' + (check.voucher_id.number),
                            'type': 'in_invoice',
                            'account_id': check.voucher_id.partner_id.property_account_payable.id,
                            'partner_id': check.voucher_id.partner_id.id,
                            'address_invoice_id': invoice_address,
                            'address_contact_id': contact_address,
                            'date_invoice': wizard.reject_date,
                        }

            invoice_id = invoice_obj.create(cr, uid, invoice_vals)
 
            invoice_line_vals = {
                'name': 'Check Rejected Hand Nr. ' + check.number,
                'origin': 'Check Rejected Hand Nr. ' + check.number,
                'invoice_id': invoice_id,
                'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                'price_unit': check.amount,
                'quantity': 1,
            }
            invoice_line_obj.create(cr, uid, invoice_line_vals)
            check.write({'reject_debit_note': invoice_id})

            # if wizard.make_expense:
            if wizard.expense == 'supplier_expenses':
                if  wizard.expense_amount != 0.00 and wizard.expense_account:
                    invoice_line_obj.create(cr, uid, {
                        'name': 'Check Rejected Hand Expenses Nr. ' + check.number,
                        'origin':'Check Rejected Hand Nr. ' + check.number,
                        'invoice_id': invoice_id,
                        'account_id': wizard.expense_account.id,
                        'price_unit': wizard.expense_amount,
                        'quantity': 1,
                    })
                else:
                    raise osv.except_osv(_('Error'),_('You must assign expense account and amount !'))

                # else:
                #     if  wizard.expense_amount != 0.00 \
                #     and wizard.expense_account:
                #         name = self.pool.get('ir.sequence').get_id(cr, uid,check.voucher_id.journal_id.sequence_id.id)
                #         move_id = self.pool.get('account.move').create(cr, uid, {
                #             'name': name,
                #             'journal_id': check.voucher_id.journal_id.id,
                #             'state': 'draft',
                #             'period_id': period_id,
                #             'date': wizard.reject_date,
                #             'ref': 'Check Rejected Hand Nr. ' + check.number,
                #         })

                #         move_line.create(cr, uid, {
                #             'name': name,
                #             'centralisation': 'normal',
                #             'account_id': wizard.expense_account.id,
                #             'move_id': move_id,
                #             'journal_id': check.voucher_id.journal_id.id,
                #             'period_id': period_id,
                #             'debit': wizard.expense_amount,
                #             'credit': 0.0,
                #             'ref': 'Check Rejected Hand Nr. ' + check.number,
                #             'state': 'valid',
                #         })

                #         move_line.create(cr, uid, {
                #             'name': name,
                #             'centralisation': 'normal',
                #             'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                #             'move_id': move_id,
                #             'journal_id': check.voucher_id.journal_id.id,
                #             'period_id': period_id,
                #             'debit': 0.0,
                #             'credit': wizard.expense_amount,
                #             'ref': 'Check Rejected Hand Nr. ' + check.number,
                #             'state': 'valid',
                #         })
                #         self.pool.get('account.move').write(cr, uid, [move_id], {
                #             'state': 'posted',
                #         })

            wf_service.trg_validate(uid, 'account.issued.check', check.id,
                    'handed_hrejected', cr)

        return {}

account_issuedcheck_hreject()
