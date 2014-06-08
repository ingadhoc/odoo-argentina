# -*- coding: utf-8 -*-
##############################################################################
#
#    Sistemas ADHOC - ADHOC SA
#    https://launchpad.net/~sistemas-adhoc
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

class argentinian_base_configuration(osv.osv_memory):
    _inherit = 'argentinian.base.config.settings'

    _columns = {
        'group_customer_other_documents': fields.boolean('Show Customer Other Documents Menu',
            implied_group='l10n_ar_invoice.customer_other_documents',
            help="To allow your salesman to register customer other documents like ???'."),
        'group_supplier_other_documents': fields.boolean('Show Supplier Other Documents Menu',
            implied_group='l10n_ar_invoice.supplier_other_documents',
            help="To allow your salesman to register supplier other documents like imports'."),
        'group_customer_debit_notes': fields.boolean('Show Customer Debit Notes Menu',
            implied_group='l10n_ar_invoice.customer_debit_notes',
            help="To allow your salesman to register customer debit notes'."),
        'group_supplier_debit_notes': fields.boolean('Show Supplier Debit Notes Menu',
            implied_group='l10n_ar_invoice.supplier_debit_notes',
            help="To allow your salesman to register supplier debit notes'."),
    }        
    
    _defaults = {
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
