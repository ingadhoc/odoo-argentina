# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'map_supplier_invoice_journals': fields.boolean(string="Map Supplier Invoices Journals", help='Suggest and Check journal on supplier invoices based in their responsability. Suggested to be used on Argentinian Companies'),
        'map_customer_invoice_journals': fields.boolean(string="Map Customer Invoices Journals", help='Suggest and Check journal on customer invoices based in their responsability. Suggested to be used on Argentinian Companies'),
        'responsability_id': fields.related('partner_id', 'responsability_id', relation='afip.responsability', type='many2one', string="Responsability",),
        'iibb': fields.related('partner_id', 'iibb', type='char', string='Gross Income', size=64,),
        'start_date': fields.related('partner_id', 'start_date', type='date', string='Start-up Date', size=64,),
    }

    _defaults = {
        'map_supplier_invoice_journals': True,
        'map_customer_invoice_journals': True,
    }