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


class receipt_receipt (osv.osv):
       
    _name = "receipt.receipt" 
    _description = 'Receipt'
    _columns = {
            'name':fields.char(string='Receipt number',size=128, required=True, readonly=True, ondelete='set null'),
            'receiptbook_id': fields.many2one('receipt.receiptbook','ReceiptBook',readonly=True,required=True),   
            'date': fields.date('Receipt Date',readonly=True),
            'total_ammount':fields.float('Total Ammount',readonly=True),
            'partner_id':fields.many2one('res.partner',string='Partner',readonly=True),
            'voucher_ids':fields.one2many('account.voucher','receipt_id',string='Vouchers Lines'),
            'receipt_type': fields.selection([('receipt','receipt'),
                                             ('payment','payment')],'Receipt Type', required=1),

                }
                
    _sql_constraints = [('name_uniq','unique(name)','The name must be unique!')]
    _order = "date"

   
   # def unlink(self, cr, uid, ids, context=None):

        #raise osv.except_osv(_('Invalid action !'), _('Cannot delete Receipt(s) !'))
        #return {'type': 'ir.actions.act_window_close'} 
         
    
receipt_receipt()      

class receipt_receipt_line (osv.osv):
    
    _name = "receipt.receipt.line" 
    _description = 'Receipt Line'
    _columns = {
            'receipt_id':fields.many2one('receipt.receipt', 'Receipt', ondelete='set null'),
            'name':fields.char('Description', size=256),
            'voucher_id': fields.many2one('account.voucher', 'Voucher'),

                }
    _order = "receipt_id"  
    
receipt_receipt_line()  

