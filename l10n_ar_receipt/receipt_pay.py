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
from osv import fields, osv 
from tools.translate import _
import logging
import time
import netsvc
_logger = logging.getLogger(__name__)
        
class receipt_pay(osv.osv_memory):
    
    
    def _get_receiptbook_id(self, cr, uid, context=None):
        res={}
        if context is None: 
            context = {}
        receiptbook_pool = self.pool.get('receipt.receiptbook')
        order_obj= self.pool.get('account.voucher')
        
        for order in order_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            _logger.info("pasa order.type: %s",order.type)
            if order.type == 'receipt':
                ids = receiptbook_pool.search(cr, uid, [('state', '=', 'active'),('type_custsupl','=','cust')],)
                
                #result[res.id] = [res.name]
            else:
                ids = receiptbook_pool.search(cr, uid, [('state', '=', 'active'),('type_custsupl','=','supl')],)
           
            _logger.info("pasa ids: %s",ids) 
            res= receiptbook_pool.read(cr, uid, ids, ['id','name'], context=context) 
            res = [(r['id'], r['name']) for r in res]
            _logger.info("pasa res: %s",res) 
            return res
            

        
    _name = "receipt.pay"
    _description = 'Receipt Pay wizard'

    _columns = {
            'fix_name_man':fields.char('Receipt Fix Number', size=4),
            'name_man':fields.char('Number', size=8),
            'name':fields.char('Receipt number', size=13),
            'date':fields.date('Receipt Date'),
            'partner':fields.char('Customer', size=40,readonly=True),
            'partner_id':fields.many2one('res.partner',string='Customer',readonly=True),
            'total_amount':fields.float("Total Amount",readonly=True),
            'receipt':fields.many2one('receipt.receipt',string='Receipt'),
            #'receiptbook_id':fields.many2one('receipt.receiptbook',string='Receipt Book',required=True),
            'receiptbook_id':fields.many2one('receipt.receiptbook',string='Receipt Book',required=True, selection= _get_receiptbook_id),
            'receiptbook_auto':fields.boolean('Receipt set type', help='This boolean helps you to use receipt manual or automatic sequence'),
            
            
        }
        
    _defaults = {
                'date':lambda *a: time.strftime('%Y-%m-%d'),
                #'receiptbook_id': _get_receiptbook_id,  
                }
        

    def default_get(self, cr, uid, fields, context=None):
        
        amount_total=0.00
        one_time= True
        partnerid= {}
        values = super(receipt_pay, self).default_get(cr, uid, fields, context=context)
        order_obj= self.pool.get('account.voucher')
        receiptbook_pool = self.pool.get('receipt.receiptbook')
        
        _logger.info("pasa fields: %s",values)
        for order in order_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if one_time:
                one_time=False
                partnerid = order.partner_id.id
                partner= order.partner_id.name
                values.update({'partner': order.partner_id.name})
                
            if order.partner_id:
                amount_total += order.amount
                
           # _logger.info("default get: %s",fields)    
           # if order.type == 'receipt':
           #     ids = receiptbook_pool.search(cr, uid, [('state', '=', 'active'),('type_custsupl','=','cust')],)
           #         
           #         #result[res.id] = [res.name]
           # else:
           #     ids = receiptbook_pool.search(cr, uid, [('state', '=', 'active'),('type_custsupl','=','supl')],)
           #     
           # _logger.info("pasa ids: %s",ids)    
               # if res:
               #     return result 
               # else:
               #     return False
            #if not ids:
            #    values.update({'receiptbook_id': ' '})
            #res = []
            #for record in receiptbook_pool.read(cr, uid, ids, ['name'], context=context):
            #    name =  record['name']
            #    res.append((record['id'],name ))
            #_logger.info("pasa res: %s",res)     
            #values.update({'receiptbook_id': res})

        
        values.update({'total_amount': amount_total})
        _logger.info("pasa fields get: %s",values)
        return values
                
                
    def onchange_receiptbook_id(self, cr, uid, ids, receiptbook_id,fix_name_man,name_man,name, context=None):
        
        result = {}
        receiptbook_obj = self.pool.get('receipt.receiptbook')
        fix_name_man = False

        if receiptbook_id:
            _logger.info("pasa receiptbook_id: %s",receiptbook_id)
            res = receiptbook_obj.browse(cr, uid, receiptbook_id, context=context)
            #re_ids = receiptbook_obj.search(cr, uid, [('name', '=', receiptbook_id),('state','=','active')],)
            _logger.info("pasa res: %s",res)
                                        
            #Busca la chequera activa de acuerdo a la cuenta                                    
            if not res:
                _logger.info("pasa res.id: %s",res)
                result = {'value':{'receiptbook_id': None}}
                result = {'value':{'name': None}}
                result.update({'warning': {'title': _('Error !'), 'message': _('You must be create a receiptkbook or change state')}})
                return result
            
            if res.state != 'active':
                _logger.info("pasa res.state : %s",res.state )
                result = {'value':{'receiptbook_id': None}}
                raise osv.except_osv(_('Error !'), _('You must be  change state !'))
                #result.update({'warning': {'title': _('Error !'), 'message': _('You must be  change state')}})
                _logger.info("pasa  if res.state %s",result)

            
            if res.receipt_type == 'manual': 
                _logger.info("pasa res.receipt_type: %s",res.receipt_type)
                #result = {'value':{'name': False }}   
                #result = {'value':{'fix_name_man': str(res.range_fix)  }}
                _logger.info("pasa fix_name_man manual: %s",fix_name_man) 
                result = {'value':{'name': False,'fix_name_man': str(res.range_fix) }}                           
                _logger.info("pasa  if res.receipt_type %s",result)    
            else:
                _logger.info("pasa else 1 fix_name_man: %s",fix_name_man) 
                #result = {'value':{'fix_name_man': None}}
                actual=0
                hasta=0
                actual= int(res.actual_number)
                hasta= int(res.range_hasta)
                #if actual == hasta:
                #    receiptbook_obj.write(cr, uid, receiptbook_id, {'state': 'used',})  
                #else:
                #    if str(res.actual_number) < str(res.range_hasta):
                #        sum_actual_number = int(res.actual_number) + 1
                        #receiptbook_obj.write(cr, uid, receiptbook_id, {'actual_number': str(sum_actual_number),
                    #
                   #                                         }) 
                #result = {'value':{'name': res.range_fix + "-" + str(actual), }}
                #return result
                result = {'value':{'name': res.range_fix + "-" + str(actual),'fix_name_man':False }}  
                _logger.info("pasa  if ultimo %s",result)  
                              
        return result
                                                             

    def create(self, cr, uid, vals, context={}):
       
        amount_total=0.00
        one_time= True
        partnerid= {}

        order_obj= self.pool.get('account.voucher')
        receiptbook_obj = self.pool.get('receipt.receiptbook')
        receipt_obj = self.pool.get('receipt.receipt')

        for order in order_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            
            if one_time:
                one_time=False
                partnerid = order.partner_id.id
                partner= order.partner_id.name
                voucher_type = order.type
                    
                vals['partner']= order.partner_id.name
                vals['partner_id']= order.partner_id.id

            amount_total += order.amount

            if order.partner_id.id != partnerid:
                raise osv.except_osv(_('Different Customers!'), _('The receipts must be from the same Customer.'))
                return False
                    
            if  order.state in ('draft'):
                raise osv.except_osv(_('Voucher in draft state!'), _('The Voucher must not be in draft state.'))
                return False
                    
            if order.receipt_id:
                raise osv.except_osv(_('Receipt already asigned!'), _('The Voucher already have a receipt number.'))
                return False  
                    
                
        vals['total_amount']= amount_total 
        
        # Sequence receiptbook (atomatic or manual ) (customer or suppliers)
        checkbook_name = vals['receiptbook_id'] 
        book = receiptbook_obj.browse(cr, uid, checkbook_name, context=context)
        

        if voucher_type== 'payment':
            if not book.type_custsupl == 'supl':
                raise osv.except_osv(_('Error type of receipt'), _('Receiptbook type is not for Suppliers.'))
                return False
        else:
            if not book.type_custsupl == 'cust':
                raise osv.except_osv(_('Error type of receipt'), _('Receiptbook type is not for Customers.'))
                return False
                
                
        if book.receipt_type == 'automatic':
            actual=0
            hasta=0
            actual= int(book.actual_number)
            hasta= int(book.range_hasta)
            if actual == hasta:
                receiptbook_obj.write(cr, uid, checkbook_name, {'state': 'used',})  
            else:
                if str(book.actual_number) < str(book.range_hasta):
                    sum_actual_number = int(book.actual_number) + 1
                    receiptbook_obj.write(cr, uid, checkbook_name, {'actual_number': str(sum_actual_number),
            
                                                    }) 
            vals['name']= book.range_fix + "-" + str(actual)
                                                       
        else:
            desde=0
            hasta=0
            if vals['name_man']:
                numr = vals['name_man']

            else: 
                numr=0
            
            if book.actual_number:
               actual= book.actual_number

            else:
               actual=0     
            
            desde= int(book.range_desde)
            hasta= int(book.range_hasta)
            
            if int(numr) < desde or int(numr) > hasta:
                raise osv.except_osv(_('Error number'), _('Receipt number is out of range.'))
                return False
            
            res = receipt_obj.search(cr, uid, [('name', '=', book.range_fix + "-" + numr),('receiptbook_id','=',checkbook_name)],)    
                
            if res:
                raise osv.except_osv(_('Duplicated number'), _('Receipt number already asigned.'))
                return False
            else:
                vals['name']= book.range_fix + "-" + str(numr)
        
    
        res = super(receipt_pay, self).create(cr, uid, vals, context)
        return res


    def action_receipt(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        wizard = self.browse(cr, uid, ids[0], context=context) 
        wizard_ids = [wizard.id] 
        
        rec_ids = context.get('active_ids',[])  
        
        receipt_obj = self.pool.get('receipt.receipt')
        voucher_objs = self.pool.get('account.voucher')
        receipt_line_obj = self.pool.get('receipt.receipt.line')
        
        for acc_voucher in voucher_objs.browse(cr, uid, rec_ids, context=context):
            is_type = acc_voucher.type
          
        for wizid in wizard_ids:
            pay = self.browse(cr, uid, wizid, context=context)
            _logger.info("pasa pay: %s",pay)
            #creo el recibo
            receipt_obj.create(cr, uid, {
                            'name': pay.name,
                            'receiptbook_id': pay.receiptbook_id.id,
                            'date': pay.date,
                            'total_ammount': pay.total_amount,
                            'partner_id': pay.partner_id.id,
                            'receipt_type': is_type,
                    })
            
            #busco el id del receipt
            id_receipt= receipt_obj.search(cr, uid, [('name','=',pay.name)],context=context)

            for acc_voucher in voucher_objs.browse(cr, uid, rec_ids, context=context): 
                
                voucher_objs.write(cr, uid, acc_voucher.id, {
                            'receipt_id': id_receipt[0],
                    })
                   
                receipt_line_obj.create(cr, uid, {
                            'receipt_id': id_receipt[0],
                            'voucher_id': acc_voucher.id,
                            'name': 'Activo',

                    })    
                    
            id_receipt= receipt_obj.search(cr, uid, [('name','=',pay.name)],context=context)     
            
            self.write(cr, uid, wizid, {
                            'receipt': id_receipt[0],
                    })  
    
        return {'type': 'ir.actions.act_window_close'}
        
      
    
receipt_pay()
