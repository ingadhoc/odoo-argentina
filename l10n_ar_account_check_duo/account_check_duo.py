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

from openerp.osv import fields, osv
import logging
import time
_logger = logging.getLogger(__name__)
from openerp.tools.translate import _
from datetime import datetime

class account_issued_check(osv.osv):

    def _get_checkbook_id(self, cr, uid, context=None):
        res={}
        if context is None: 
            context = {}
        checkbook_pool = self.pool.get('account.checkbook')

        res = checkbook_pool.search(cr, uid, [('state', '=', 'active')],)
        
        if res:
            return res[0] 
        else:
            return False
            
        
    _name = 'account.issued.check'
    _description = 'Manage Checks Issued'
    _inherit = ['mail.thread']
    _order = "number"

    _columns = {
        'number': fields.char('Check Number', size=8, required=True,select=True,readonly=True,states={'draft': [('readonly', False)]}),
        'amount': fields.float('Amount Check', required=True,readonly=True,states={'draft': [('readonly', False)]}),
        'date': fields.date('Date Check', required=True,readonly=True,states={'draft': [('readonly', False)]}),
        'debit_date': fields.date('Date Debit', readonly=True), # clearing date + clearing
        'receiving_partner_id': fields.many2one('res.partner','Destiny Partner' ,readonly=True,states={'draft': [('readonly', False)]}),
        'clearing': fields.selection((
                ('24', '24 hs'),
                ('48', '48 hs'),
                ('72', '72 hs'),
            ), 'Clearing',readonly=True,states={'draft': [('readonly', False)]}),
        'account_bank_id': fields.many2one('res.partner.bank','Account Bank',required=True,readonly=True,states={'draft': [('readonly', False)]}),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'issued': fields.boolean('Issued'),
        'user_id' : fields.many2one('res.users','User'),  
        # Clearing date could be false because it could be to the date                   
        'clearing_date' : fields.date('Clearing Date', required=False,readonly=True,states={'draft':[('readonly',False)]}), 
        'state':fields.selection([('draft','Draft'),
                                    ('handed','Handed'),
                                    ('hrejected','Hand-Rejected'),
                                    ('cancel','Cancelled')],
                                   string='State',required=True, track_visibility='onchange'),
        'company_id': fields.many2one('res.company', 'Company', required=True,readonly=True,states={'draft':[('readonly',False)]}, select=1, help="Company related to this Check"),
        'reject_debit_note': fields.many2one('account.invoice','Reject Debit Note'), 
        'checkbook_id': fields.many2one('account.checkbook','Checkbook',readonly=True,required=True,states={'draft': [('readonly', False)]}),                         
    }

    _sql_constraints = [('number_check_uniq','unique(number,account_bank_id)','The number must be unique!')]
    _defaults = {
        'clearing': lambda *a: '48',
        'state': 'draft',
        'user_id': lambda s, cr, u, c: u,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'checkbook_id': _get_checkbook_id, 

    }
    
    
    def unlink(self, cr, uid, ids, context=None):
        for record in self.browse(cr,uid,ids,context=context):

            if  record.state not in ('draft'):
                raise osv.except_osv(_('Error !'), _('The Check must  be in draft state only for unlink !'))
                return False 
        return super(account_issued_check, self).unlink(cr, uid, ids, context=context)     

    def create(self, cr, uid, vals, context={}):        
        checkbook_obj = self.pool.get('account.checkbook')       
        num = vals['checkbook_id']
        book = checkbook_obj.browse(cr, uid, num, context=context)
        actual = int(vals['number'])
        hasta = int(book.range_hasta)
        if actual == hasta:
            checkbook_obj.write(cr, uid, num, {'state': 'used'})
        else:
            sum_actual_number = actual + 1
            checkbook_obj.write(cr, uid, num, {
                'actual_number': str(sum_actual_number)})

        vals['account_bank_id'] = book.account_bank_id.id
        res = super(account_issued_check, self).create(cr, uid, vals, context)
        return res


    def onchange_checkbook_id(self, cr, uid, ids, number, checkbook_id, context=None):
        result = {}
        checkbook_obj = self.pool.get('account.checkbook')
        if checkbook_id:

            res = checkbook_obj.browse(cr, uid, checkbook_id, context=context)
                                           
            #Busca la chequera activa de acuerdo a la cuenta                                    
            if not res.id:
                result = {'value':{'checkbook_id': None}}
                result = {'value':{'number': None}}
                result.update({'warning': {'title': _('Error !'), 'message': _('You must be create a checkbook or change state')}})
                return result
            
            if res.state != 'active':
                result = {'value':{'checkbook_id': 0}}
                result.update({'warning': {'title': _('Error !'), 'message': _('The Checkbook is not active')}})
            else:
                result = {'value':{'number': str(res.actual_number)}}
                                                             
        return result 
        
    def onchange_clearing_date(self, cr, uid, ids, date,clearing_date, context=None):
        res = {}
        if clearing_date < date:
            res = {'value':{'clearing_date': None}}
            res.update({'warning': {'title': _('Error !'), 'message': _('Clearing date must be greater than check date')}})
        else:
            res = {'value':{'clearing_date': clearing_date}}
        return res    
        
    
    def wkfw_draft(self,cr,user,ids,context=None):
        return self.write(cr,user,ids,{'state':'draft'},context=context) 

    def wkfw_handed(self, cr, user, ids, context=None):        
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'handed',
                'user_id':user
                 })
        return True


    def wkfw_hrejected(self, cr, user, ids, context=None):
        # TODO: Ejecutar el armado de nota de debito por cheque rechazado!
        # Ver si el cheque fue emitido por la empresa, si es asi deberia generar
        # una nota de credito al proveedor.
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'hrejected',
                'user_id':user
                 })
        return True

    def wkfw_cancel(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'cancel',
                'user_id':user
                 })
        return True
                
account_issued_check()


class account_third_check(osv.osv):
    

    _name = 'account.third.check'
    _description = 'Manage Checks Third'
    _order = "id desc"
    _inherit = ['mail.thread']
    

    _columns = {
            'number': fields.char('Check Number', size=8, required=True,readonly=True,states={'draft': [('readonly', False)]}),
            'sequence_number': fields.char('Id Number', size=40,readonly=True),
            'amount': fields.float('Check Amount', required=True,readonly=True,states={'draft':[('readonly',False)]}),
            'date_in': fields.date('Date In', required=True,readonly=True,states={'draft':[('readonly',False)]}),
            'date': fields.date('Check Date', required=True,readonly=True,states={'draft':[('readonly',False)]}),
            'source_partner_id': fields.many2one('res.partner', 'Source Partner',readonly=True,states={'draft':[('readonly',False)]}),
            'destiny_partner_id': fields.many2one('res.partner', 'Destiny Partner',readonly=False, required=False,states={'handed': [('required', True)]}),
            'state': fields.selection((
                    ('draft', 'Draft'),
                    ('holding', 'Holding'),
                    ('deposited', 'Deposited'),
                    ('drejected', 'Dep-Rejected'),
                    ('handed', 'Handed'),
                    ('hrejected', 'Hand-Rejected'),
                    ('sold', 'Sold'),
                ), 'State', required=True, track_visibility='onchange'),
            'bank_id': fields.many2one('res.bank', 'Bank', readonly=True,required=True,states={'draft': [('readonly', False)]}),
            'vat': fields.char('Vat', size=11,states={'draft': [('readonly', False)]}),
            'user_id' : fields.many2one('res.users','User'),  
            # Clearing date could be false because it could be to the date                              
            'clearing_date' : fields.date('Clearing Date', required=False,readonly=True,states={'draft':[('readonly',False)]}),
            'clearing': fields.selection((
                    ('24', '24 hs'),
                    ('48', '48 hs'),
                    ('72', '72 hs'),
                ), 'Clearing', readonly=True,states={'draft': [('readonly', False)]}),
        'account_bank_id': fields.many2one('res.partner.bank','Destiny Account'),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'company_id': fields.many2one('res.company', 'Company', required=True,readonly=True,states={'draft':[('readonly',False)]}, select=1, help="Company related to this Check"),
        'reject_debit_note': fields.many2one('account.invoice','Reject Debit Note'),
        'reject_debit_note_prov':fields.many2one('account.invoice','Reject Debit Note Prov'),
        'clearing_date_hasta':fields.date('Clearing Date Hasta', required=False),
        'ticket_deposit_id':fields.many2one('ticket.deposit',string='Ticket Deposit',required=False,readonly=True,states={'draft':[('readonly',False)]}),
    }

    _defaults = {
        'state': 'draft',
        'clearing': lambda *a: '48',
        'date_in': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda s, cr, u, c: u,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context is None:
            context = {}
        pos = 0
        desde = False
        hasta = False
        while pos < len(args):
            if args[pos][0] == 'clearing_date':
                desde= args[pos][2]
            if args[pos][0] == 'clearing_date_hasta':
                hasta= args[pos][2] 
            pos += 1  
              
            if  desde and hasta:
                 
                return super(account_third_check, self).search(cr, uid, [('clearing_date', '>', desde),
                                                                     ('clearing_date', '<', hasta),
                                                                    ])
                                            
        return super(account_third_check, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        
    def onchange_number(self, cr, uid, ids, number, context=None):
        res = {}
        number_str = str(number)
        if len(number_str) != 8:
            res = {'value':{'number': 0}}
            res.update({'warning': {'title': _('Error !'), 'message': _('Ckeck Number must be 8 numbers !')}})
        else:

            res = {'value':{'number': number}}
        return res
        
    def onchange_clearing_date(self, cr, uid, ids, date,clearing_date, context=None):
        res = {}
        if clearing_date < date:
            res = {'value':{'clearing_date': None}}
            res.update({'warning': {'title': _('Error !'), 'message': _('Clearing date must be greater than check date')}})
        else:
            res = {'value':{'clearing_date': clearing_date}}
        return res    
        
    def onchange_vat(self, cr, uid, ids, vat, context=None):
        res = {}
        if not vat:
            res.update({'warning': {'title': _('Error !'), 'message': _('Vat number must be not null !')}})
        else:
            if len(vat) != 11:
                res = {'value':{'vat': None}}
                res.update({'warning': {'title': _('Error !'), 'message': _('Vat number must be 11 numbers !')}})
            else:    
                res = {'value':{'vat': vat}}
        return res    
        
    def unlink(self, cr, uid, ids, context=None):
        for record in self.browse(cr,uid,ids,context=context):

            if  record.state not in ('draft'):
                raise osv.except_osv(_('Error !'), _('The Check must  be in draft state only for unlink !'))
                return False 
        return super(account_third_check, self).unlink(cr, uid, ids, context=context)     
    
    def create(self, cr, uid, vals, context=None):
        # TODO make that the button create is not available on the m2m widget used on supplier payments 
        if context.get('type', False) != 'receipt':
            raise osv.except_osv(_('Error !'), _('Third Checks must be created on Costumer Payment!'))
            return res

        seq_obj_name =  'check.third'
        name = self.pool.get('ir.sequence').get(cr, uid,seq_obj_name)
                       
        vals['sequence_number']= name
        
        res = super(account_third_check, self).create(cr, uid, vals, context)           
        return res            

    def wkf_draft(self, cr, user, ids, context=None): 
        return self.write(cr,uid,ids,{'state':'draft'},context=context)
        
        
    def wkf_holding(self, cr, user, ids, context=None):
        
        #Transicion efectuada al validar un pago de cliente que contenga cheque
        for check in self.browse(cr, user, ids):
            if check.voucher_id:
                source_partner_id = check.voucher_id.partner_id.id
        
            else:
                source_partner_id = None
    
        # Si creo el cheque para usar en pago al proveedor o lo uso de pago cliente
        check.write({
                'source_partner_id': source_partner_id,
                'state': 'holding',
                'user_id':user
                })
        return True

    def wkf_handed(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'handed',
                'user_id':user
                 })
        return True

    def wkf_hrejected(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'hrejected',
                'user_id':user
                 })
        return True

    def wkf_deposited(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'deposited',
                'user_id':user
                 })
        return True

    def wkf_drejected(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'drejected',
                'user_id':user
                 })
        return True

    def wkf_sold(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'sold',
                'user_id':user
                 })
        return True
   
    def wkf_cancel(self, cr, user, ids, context=None):
        for check in self.browse(cr, user, ids):
            check.write({
                'state': 'cancel',
                'user_id':user
                 })
        return True     

account_third_check()

