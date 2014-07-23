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
import logging
import time
_logger = logging.getLogger(__name__)
from tools.translate import _
from datetime import datetime

class account_checkbook(osv.osv):
    
    _name = 'account.checkbook'
    _description = 'Manage Checkbook'
    _inherit = ['mail.thread']

    _columns = {
        'name':fields.char('CheckBook Name', size=30, readonly=True,select=True,required=True,states={'draft': [('readonly', False)]}),
        'range_desde': fields.integer('Check Number Desde', size=8, readonly=True,required=True,states={'draft': [('readonly', False)]}),
        'range_hasta': fields.integer('Check Number Hasta', size=8,readonly=True, required=True,states={'draft': [('readonly', False)]}),
        'actual_number':fields.char('Next Check Number', size=8,readonly=True, required=True,states={'draft': [('readonly', False)]}),
        'account_bank_id': fields.many2one('res.partner.bank','Account Bank',readonly=True,required=True,states={'draft': [('readonly', False)]}),
        'user_id' : fields.many2one('res.users','User'),  
        'state':fields.selection([('draft','Draft'),('active','In Use'),('used','Used')],string='State',readonly=True),                            
    }
    
    _order = "name"
    _defaults = {
        'state': 'draft',
    }

    def _check_numbers(self, cr, uid, ids, context=None):
        record = self.browse(cr, uid, ids, context=context)
        print record
        for data in record:
            if (data.range_hasta <= data.range_desde):
                return False
        return True

    _constraints = [
        (_check_numbers, 'Range to must be greater than range from', ['level']),
        ]
    
    def unlink(self, cr, uid, ids, context=None):
        for record in self.browse(cr,uid,ids,context=context):

            if  record.state not in ('draft'):
                raise osv.except_osv(_('Error !'), _('You can drop the checkbook(s) only in  draft state !'))
                return False 
        return super(account_checkbook, self).unlink(cr, uid, ids, context=context) 
   
    def wkf_active(self, cr, uid, ids,context=None):
        if context is None:
            context = {}
        res= {}  
        check_obj= self.pool.get('account.checkbook')
        for order in self.browse(cr,uid,ids,context=context):
            
            if not order.account_bank_id.account_id.id:
                raise osv.except_osv(' %s selected error' % (order.account_bank_id.bank.name),
                    'The bank account must have an account selected.' )
            
            res = check_obj.search(cr, uid, [('account_bank_id', '=', order.account_bank_id.id),
                                              ('state', '=', 'active')],)
                                                                                
            if res:
                raise osv.except_osv(_('Error !'), _('You cant change the checkbook´s state, there is one active !'))
                return False 

            else:
                self.write(cr, uid, ids, { 'state' : 'active' })
                return True
                
        
    def wkf_used(self, cr, uid, ids,context=None):
        self.write(cr, uid, ids, { 'state' : 'used' })
        return True
   
        
account_checkbook()
