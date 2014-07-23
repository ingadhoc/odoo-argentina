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


class ticket_deposit(osv.osv):
       
    _name = "ticket.deposit" 
    _description = 'Ticket Deposit'
    _columns = {
            'name':fields.char(string='Ticket Deposit number',size=128, required=True, select=True, readonly=True, ondelete='set null'),  
            'date': fields.date('Ticket Deposit Date',readonly=True),
            'bank_account_id': fields.many2one('res.partner.bank', 'Bank Account',required=True),
            'total_ammount':fields.float('Total Ammount',readonly=True),
            'checks_ids':fields.one2many('account.third.check','ticket_deposit_id',string='Check Lines'),

                }
                
    _sql_constraints = [('name_uniq','unique(name)','The name must be unique!')]
    _order = "date"

         
    
ticket_deposit()      

class ticket_deposit_line (osv.osv):
    
    _name = "ticket.deposit.line" 
    _description = 'Ticket Deposit Line'
    _columns = {
            'ticket_deposit_id':fields.many2one('ticket.deposit', 'Ticket Deposit', ondelete='set null'),
            'name':fields.char('Description', size=256),
            'account_third_check_id': fields.many2one('account.third.check', 'Thirds Checks'),

                }
    _order = "ticket_deposit_id"  

ticket_deposit_line()  

