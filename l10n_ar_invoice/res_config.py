# -*- coding: utf-8 -*-
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