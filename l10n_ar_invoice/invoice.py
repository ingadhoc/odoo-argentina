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
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

_all_taxes = lambda x: True
_all_except_vat = lambda x: x.tax_code_id.parent_id.name != 'IVA'

class account_invoice_line(osv.osv):
    """
    En argentina como no se diferencian los impuestos en las facturas, excepto el IVA,
    agrego funciones que ignoran el iva solamenta a la hora de imprimir los valores.

    En esta nueva versión se cambia las tres variables a una única función 'price_calc'
    que se reemplaza de la siguiente manera:

        'price_unit_vat_included'         -> price_calc(use_vat=True, quantity=1, discount=True)[id]
        'price_subtotal_vat_included'     -> price_calc(use_vat=True, discount=True)[id]
        'price_unit_not_vat_included'     -> price_calc(use_vat=False, quantity=1, discount=True)[id]
        'price_subtotal_not_vat_included' -> price_calc(use_vat=False, discount=True)[id]

    Y ahora puede imprimir sin descuento:

        price_calc(use_vat=True, quantity=1, discount=False)
    """

    _inherit = "account.invoice.line"

    def price_calc(self, cr, uid, ids, use_vat=True, tax_filter=None, quantity=None, discount=None, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        _tax_filter = tax_filter or ( use_vat and _all_taxes ) or _all_except_vat
        for line in self.browse(cr, uid, ids):
            _quantity = quantity if quantity is not None else line.quantity
            _discount = discount if discount is not None else line.discount
            _price = line.price_unit * (1-(_discount or 0.0)/100.0)
            _tax_ids = filter(_tax_filter, line.invoice_line_tax_id)
            taxes = tax_obj.compute_all(cr, uid,
                                        _tax_ids, _price, _quantity,
                                        product=line.product_id,
                                        partner=line.invoice_id.partner_id)
            res[line.id] = taxes['total_included']
            if line.invoice_id:
                cur = line.invoice_id.currency_id
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    def compute_all(self, cr, uid, ids, tax_filter=None, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        _tax_filter = tax_filter
        for line in self.browse(cr, uid, ids):
            _quantity = line.quantity
            _discount = line.discount
            _price = line.price_unit * (1-(_discount or 0.0)/100.0)
            _tax_ids = filter(_tax_filter, line.invoice_line_tax_id)
            taxes = tax_obj.compute_all(cr, uid,
                                        _tax_ids, _price, _quantity,
                                        product=line.product_id,
                                        partner=line.invoice_id.partner_id)

            _round = (lambda x: cur_obj.round(cr, uid, line.invoice_id.currency_id, x)) if line.invoice_id else (lambda x: x)
            res[line.id] = {
                'amount_untaxed': _round(taxes['total']),
                'amount_tax': _round(taxes['total_included'])-_round(taxes['total']),
                'amount_total': _round(taxes['total_included']), 
                'taxes': taxes['taxes'],
            }
        return res.get(len(ids)==1 and ids[0], res)

account_invoice_line()

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_available_journal_ids(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            journal_type = self.get_journal_type(cr, uid, invoice.type, context=context)
            journal_ids = self.get_valid_journals(cr, uid, invoice.partner_id.id, journal_type, company_id=invoice.company_id.id)            
            result[invoice.id] = journal_ids
        return result

    _columns = {
        'available_journal_ids': fields.function(_get_available_journal_ids, relation='account.journal', type='many2many', string='Available Journals'),
    }

    def afip_validation(self, cr, uid, ids, context={}):

        for invoice in self.browse(cr, uid, ids):
            if invoice.type == 'in_invoice':
                journal_type = 'purchase'
            elif invoice.type == 'in_refund':
                journal_type = 'purchase_refund'
            elif invoice.type == 'out_invoice':
                journal_type = 'sale'
            elif invoice.type == 'out_refund':
                journal_type = 'sale_refund'

            journal_ids = self.get_valid_journals(cr, uid, invoice.partner_id.id, journal_type, company_id=invoice.company_id.id)

            if invoice.journal_id.id not in journal_ids:
                raise osv.except_osv(_('Invalid Journal'),
                    _('Invalid journal selection for actual partner and company.'))

    def compute_all(self, cr, uid, ids, line_filter=lambda line: True, tax_filter=lambda tax: True, context=None):
        res = {}
        for inv in self.browse(cr, uid, ids, context=context):
            amounts = []
            for line in inv.invoice_line:
                if line_filter(line):
                    amounts.append(line.compute_all(tax_filter=tax_filter, context=context))

            s = {
                 'amount_total': 0,
                 'amount_tax': 0,
                 'amount_untaxed': 0,
                 'taxes': [],
                }
            for amount in amounts:
                for key, value in amount.items():
                    s[key] = s.get(key, 0) + value

            res[inv.id] = s

        return res.get(len(ids)==1 and ids[0], res)

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,
                            date_invoice=False, payment_term=False,
                            partner_bank_id=False, company_id=False, context=None):
        result = super(account_invoice,self).onchange_partner_id(cr, uid, ids,
                       type, partner_id, date_invoice, payment_term,
                       partner_bank_id, company_id,)
        
        
        if type == 'in_invoice':
            journal_type = 'purchase'
        elif type == 'in_refund':
            journal_type = 'purchase_refund'
        elif type == 'out_invoice':
            journal_type = 'sale'
        elif type == 'out_refund':
            journal_type = 'sale_refund'

        journal_id = False
        journal_ids = False
        normal_journal_ids = False
        
        if company_id and partner_id:
            normal_journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, is_debit_note=False, company_id=company_id)
            journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id)

        if normal_journal_ids:            
            journal_id = normal_journal_ids[0]
        
        if 'value' not in result: result['value'] = {}
        result['value'].update({
           'journal_id': journal_id,
        })      

        if 'domain' not in result: result['domain'] = {}          
        result['domain'].update({
           'journal_id': [('id', 'in', journal_ids)],
        })  
        return result

    def get_valid_journals(self, cr, uid, partner_id, journal_type, is_debit_note=None, company_id=False, context=None):
        # Type could be purchase or sale
        journal_obj = self.pool.get('account.journal')
        resp_relation_obj = self.pool.get('afip.responsability_relation')
        responsability_obj = self.pool.get('afip.responsability')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)

        if partner.parent_id:
            partner = partner.parent_id

        if context is None:
            context = {}
        if company_id == False:
            company_id = context.get('company_id', user.company_id.id) 
        company = self.pool.get('res.company').browse(cr, uid, company_id, context)

        journal_ids = []
        journal_filter = []
        journal_filter.append(('company_id','=',company_id))
        map_invoice = False
        if journal_type in ['sale','sale_refund']:
            issuer_responsability_id = company.partner_id.responsability_id.id
            receptor_responsability_id = partner.responsability_id.id 
            if company.map_customer_invoice_journals:
                map_invoice = True
        elif journal_type in ['purchase','purchase_refund']:
            issuer_responsability_id = partner.responsability_id.id    
            receptor_responsability_id = company.partner_id.responsability_id.id
            if company.map_supplier_invoice_journals:
                map_invoice = True            
        else:
            raise orm.except_orm(_('Journal Type Error'),
                    _('Journal Type Not defined)'))
        if journal_type:
            journal_filter.append(('type','=',journal_type))
            
        # Now we check if the company has mapping journals enable
        if map_invoice:
            if not company.partner_id.responsability_id.id:
                raise orm.except_orm(_('Your company has not setted any responsability'),
                        _('Please, set your company responsability in the company partner before continue.'))            
                _logger.warning('Your company "%s" has not setted any responsability.' % company.name)

            document_class_ids = []

            resp_relation_ids = resp_relation_obj.search(cr, uid, [('issuer_id', '=', issuer_responsability_id),('receptor_id', '=', receptor_responsability_id)], context=context)

            for resp_relation in resp_relation_obj.browse(cr, uid, resp_relation_ids, context):
                if resp_relation.document_class_id not in document_class_ids:
                    document_class_ids.append(resp_relation.document_class_id.id)
            journal_filter.append(('journal_class_id.document_class_id','in',document_class_ids))
        
        if is_debit_note != None:
            journal_filter.append(('is_debit_note','=',is_debit_note))
            journal_ids = journal_obj.search(cr, uid, journal_filter, context)
        else:
            debit_journal_filter = journal_filter[:]
            debit_journal_filter.append(('is_debit_note','=',True))
            journal_filter.append(('is_debit_note','=',False))
            
            # We look for jorunals not debit notes
            journal_ids = journal_obj.search(cr, uid, journal_filter, context=context)
            # We append debit notes
            journal_ids.extend(journal_obj.search(cr, uid, debit_journal_filter, context=context))

        return journal_ids  


    def onchange_company_id(self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id):
        result = super(account_invoice,self).onchange_partner_id(cr, uid, ids,
                       company_id, part_id, type, invoice_line, currency_id)        
        partner_id = part_id

        if type == 'in_invoice':
            journal_type = 'purchase'
        elif type == 'in_refund':
            journal_type = 'purchase_refund'
        elif type == 'out_invoice':
            journal_type = 'sale'
        elif type == 'out_refund':
            journal_type = 'sale_refund'

        journal_id = False
        journal_ids = False
        normal_journal_ids = False
        
        if company_id and partner_id:
            normal_journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, is_debit_note=False, company_id=company_id)
            journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id)

        if normal_journal_ids:            
            journal_id = normal_journal_ids[0]
        
        if 'value' not in result: result['value'] = {}
        result['value'].update({
           'journal_id': journal_id,
        })      

        if 'domain' not in result: result['domain'] = {}          
        result['domain'].update({
           'journal_id': [('id', 'in', journal_ids)],
        })    

        return result    

    def get_journal_type(self, cr, uid, invoice_type, context=None):
        if invoice_type == 'in_invoice':
            journal_type = 'purchase'
        elif invoice_type == 'in_refund':
            journal_type = 'purchase_refund'
        elif invoice_type == 'out_invoice':
            journal_type = 'sale'
        elif invoice_type == 'out_refund':
            journal_type = 'sale_refund'
        else:
            journal_type = False
        return journal_type          

    def _get_journal(self, cr, uid, context=None):
        '''We change the default _get_journal_ function. If there is a partner on the context
        we will try to choose the right journal'''

        res = super(account_invoice,self)._get_journal(cr, uid, context=context)
        partner_id = context.get('partner_id', False)
        journal_type = context.get('journal_type', False)
        if not partner_id:
            partner_id = context.get('default_partner_id', False)            
        print 'get_journal'
        if partner_id and journal_type:
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            company_id = context.get('company_id', user.company_id.id)
            journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)
            print 'journal_ids', journal_ids
            if journal_ids: 
                res = journal_ids[0]
        return res

    def create(self, cr, uid, vals, context=None):
        ''' Modify create function so it can try to set a right journal for the invoice'''
        if not context:
            context = {}
        partner_id = vals.get('partner_id', False)
        journal_type = vals.get('journal_type', False)
        # Intentamos hacer esto de qeu si viene un joruanl no lo cambie pero la verdad es que en diversas ocasiones viene un jorunal equivocado, por ejemplo en modulo sale
        # journal_id = vals.get('journal_id', False)
        # if not journal_id:
        if not journal_type:
            invoice_type = vals.get('type', False)
            journal_type = self.get_journal_type(cr, uid, invoice_type, context=context)      
        if partner_id and journal_type:
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            company_id = vals.get('company_id', context.get('company_id',user.company_id.id))
            journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)
            if journal_ids:
                vals['journal_id'] = journal_ids[0]
        return super(account_invoice, self).create(cr, uid, vals, context)