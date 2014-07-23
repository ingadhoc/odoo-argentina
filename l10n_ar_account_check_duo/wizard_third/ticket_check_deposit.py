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

from osv import osv, fields
from tools.translate import _
import netsvc
import logging
_logger = logging.getLogger(__name__)


class wizard_ticket_deposit(osv.osv_memory):
    _name = 'wizard.ticket.deposit'

    _columns = {
        'name':fields.char('Ticket deposited number', size=30),
        'bank_account_id': fields.many2one('res.partner.bank', 'Bank Account',required=True),
        'date': fields.date('Deposit Date',required=True),
        'total_amount':fields.float("Total Amount",readonly=True),
        'ticket_deposit':fields.many2one('ticket.deposit',string='Ticket Deposit'),
    }

    def default_get(self, cr, uid, fields, context=None):
        
        amount_total=0.00
        one_time= True
        partnerid= {}
        values = super(wizard_ticket_deposit, self).default_get(cr, uid, fields, context=context)
        third_check = self.pool.get('account.third.check')
        
        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])
        
        check_objs = third_check.browse(cr, uid, record_ids, context=context)

        for check in check_objs:
            if check.state == 'holding':
                amount_total += check.amount
            else:    
                raise osv.except_osv('Check %s selected error' % (check.number),
                    'The selected checks must to be in the holding.' )
        
        
        
        values.update({'total_amount': amount_total})
        return values


    def action_ticket_deposit(self, cr, uid, ids, context=None):
        third_check_obj = self.pool.get('account.third.check')
        
        wf_service = netsvc.LocalService('workflow')
        ticket_obj = self.pool.get('ticket.deposit')
        ticket_line_obj = self.pool.get('ticket.deposit.line')

        move_line = self.pool.get('account.move.line')

        wizard = self.browse(cr, uid, ids[0], context=context)
        wizard_ids = [wizard.id] 

        period_id = self.pool.get('account.period').find(cr, uid, wizard.date)[0]

        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])

        check_ids = third_check_obj.browse(cr, uid, record_ids, context=context)
        
        for wizid in wizard_ids:
            pay = self.browse(cr, uid, wizid, context=context)
            
            #creo el ticket
            ticket_obj.create(cr, uid, {
                            'name': pay.name,
                            'bank_account_id': wizard.bank_account_id.id,
                            'date': pay.date,
                            'total_ammount': pay.total_amount,

                    })
                    
              
            #busco el id del receipt
            id_ticket_dep= ticket_obj.search(cr, uid, [('name','=',pay.name)],context=context)

            for third_check in third_check_obj.browse(cr, uid, record_ids, context=context): 
                
                third_check_obj.write(cr, uid, third_check.id, {
                            'ticket_deposit_id': id_ticket_dep[0],
                    })
                   
                ticket_line_obj.create(cr, uid, {
                            'ticket_deposit_id': id_ticket_dep[0],
                            'account_third_check_id': third_check.id,
                            'name': 'Activo',

                    })    
                    
            id_receipt= ticket_obj.search(cr, uid, [('name','=',pay.name)],context=context)     
            
            self.write(cr, uid, wizid, {
                            'ticket_deposit': id_receipt[0],
                    })           

        for check in check_ids:
            if not (check.voucher_id.journal_id.default_credit_account_id.id or check.voucher_id.journal_id.default_debit_account_id.id):
                raise osv.except_osv('Journal %s selected error' % (check.voucher_id.journal_id.id),
                    'The journal must to be created defaults account for debit and credit.' )
                    
            if not wizard.bank_account_id.account_id.id:
                raise osv.except_osv(' %s selected error' % (wizard.bank_account_id.bank.name),
                    'The account must to be created in The Company Bank / Accounting Information.' )
            
                     
                     
            if check.state != 'holding':
                raise osv.except_osv('Check %s selected error' % (check.number),
                    'The selected checks must to be in the holding.' )
    
            else:
                name = self.pool.get('ir.sequence').next_by_id(cr, uid, check.voucher_id.journal_id.sequence_id.id, context=context)
                
                move_id = self.pool.get('account.move').create(cr, uid, {
                        'name': name,
                        'journal_id': check.voucher_id.journal_id.id,
                        'state': 'draft',
                        'period_id': period_id,
                        'date': wizard.date,
                        'ref': 'Check Deposit Nr. ' + check.number,
                })
                
                move_line.create(cr, uid, {
                        'name': name,
                        'centralisation': 'normal',
                        'account_id': wizard.bank_account_id.account_id.id,
                        'move_id': move_id,
                        'journal_id': check.voucher_id.journal_id.id,
                        'period_id': period_id,
                        'debit': check.amount,
                        'credit': 0.0,
                        'ref': 'Check Deposit Nr. ' + check.number,
                        'state': 'valid',
                })
                move_line.create(cr, uid, {
                        'name': name,
                        'centralisation': 'normal',
                        'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                        'move_id': move_id,
                        'journal_id': check.voucher_id.journal_id.id,
                        'period_id': period_id,
                        'debit': 0.0,
                        'credit': check.amount,
                        'ref': 'Check Deposit Nr. ' + check.number,
                        'state': 'valid',
                })
                
                check.write({'account_bank_id': wizard.bank_account_id.id})
                wf_service.trg_validate(uid, 'account.third.check', check.id,'holding_deposited', cr)
            self.pool.get('account.move').write(cr, uid, [move_id], {'state': 'posted',})

        return {}

wizard_ticket_deposit()
