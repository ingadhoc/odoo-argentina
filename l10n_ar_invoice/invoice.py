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
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

class account_invoice_line(osv.osv):
    """
    En argentina como no se diferencian los impuestos en las facturas, excepto el IVA,
    agrego campos que ignoran el iva solamenta a la hora de imprimir los valores.
    """

    _inherit = "account.invoice.line"

    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}
        tax_obj = self.pool['account.tax']
        cur_obj = self.pool.get('res.currency')

        for line in self.browse(cr, uid, ids, context=context):
            _round = (lambda x: cur_obj.round(cr, uid, line.invoice_id.currency_id, x)) if line.invoice_id else (lambda x: x)
            quantity = line.quantity
            discount = line.discount
            printed_price_unit = line.price_unit
            printed_price_net = line.price_unit * (1-(discount or 0.0)/100.0)
            printed_price_subtotal = printed_price_net * quantity

            afip_document_class_id = line.invoice_id.journal_document_class_id.afip_document_class_id
            if afip_document_class_id and not afip_document_class_id.vat_discriminated:
                vat_taxes = [x for x in line.invoice_line_tax_id if x.tax_code_id.vat_tax]
                print 'vat_taxes', vat_taxes
                taxes = tax_obj.compute_all(cr, uid,
                                            vat_taxes, printed_price_net, 1,
                                            product=line.product_id,
                                            partner=line.invoice_id.partner_id)
                printed_price_unit = _round(taxes['total_included'] * (1+(discount or 0.0)/100.0))
                printed_price_net = _round(taxes['total_included'])
                printed_price_subtotal = _round(taxes['total_included'] * quantity)
            
            res[line.id] = {
                'printed_price_unit': printed_price_unit,
                'printed_price_net': printed_price_net,
                'printed_price_subtotal': printed_price_subtotal, 
            }
        return res

    _columns = {
        'printed_price_unit': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Unit Price', multi='printed',),
        'printed_price_net': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Net Price', multi='printed'),
        'printed_price_subtotal': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Subtotal', multi='printed'),
    }    

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    # def _get_available_journal_ids(self, cr, uid, ids, field_name, arg, context=None):
    #     if context is None:
    #         context = {}
    #     result = {}
    #     for invoice in self.browse(cr, uid, ids, context=context):
    #         journal_type = self.get_journal_type(cr, uid, invoice.type, context=context)
    #         journal_ids = self.get_valid_journals(cr, uid, invoice.partner_id.id, journal_type, company_id=invoice.company_id.id)            
    #         result[invoice.id] = journal_ids
    #     return result

    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}

        for invoice in self.browse(cr, uid, ids, context=context):
            printed_amount_untaxed = invoice.amount_untaxed
            printed_tax_ids = [x.id for x in invoice.tax_line]

            afip_document_class_id = invoice.journal_document_class_id.afip_document_class_id
            if afip_document_class_id and not afip_document_class_id.vat_discriminated:
                printed_amount_untaxed = sum(line.printed_price_net for line in invoice.invoice_line)
                printed_tax_ids = [x.id for x in invoice.tax_line if not x.tax_code_id.vat_tax]
            
            res[invoice.id] = {
                'printed_amount_untaxed': printed_amount_untaxed,
                'printed_tax_ids': printed_tax_ids,
            }
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        # types = {
        #         'out_invoice': _('Invoice'),
        #         'in_invoice': _('Supplier Invoice'),
        #         'out_refund': _('Refund'),
        #         'in_refund': _('Supplier Refund'),
        #         }
        # return [(r['id'], '%s %s' % (r['number'] or types[r['type']], r['name'] or '')) for r in self.read(cr, uid, ids, ['type', 'number', 'name'], context, load='_classic_write')]
        return [(r['id'], r['document_number'] or r['number'] or '') for r in self.read(cr, uid, ids, ['type', 'number', 'document_number'], context, load='_classic_write')]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('document_number','=',name)] + args, limit=limit, context=context)
            # ids = self.search(cr, user, [('number','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('document_number',operator,name)] + args, limit=limit, context=context)
            # ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    _columns = {
        'printed_amount_untaxed': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Subtotal', multi='printed',),
        'printed_tax_ids': fields.function(_printed_prices, type='one2many', relation='account.invoice.tax', string='Tax', multi='printed'),
        # 'available_journal_ids': fields.function(_get_available_journal_ids, relation='account.journal', type='many2many', string='Available Journals'),
        # TODO este campo no deberia estar duplicado aca y en el account.move
        'journal_document_class_id': fields.many2one('account.journal.afip_document_class', 'Documents Class'),
        # 'afip_document_class_id': fields.many2one('afip.document_class', 'Afip Document Class'),
        'document_number': fields.related('move_id','document_number', type='char', readonly=True, size=64, relation='account.move', store=True, string='Document Number'),
    }

    def action_number(self, cr, uid, ids, context=None):
        obj_sequence = self.pool.get('ir.sequence')
        for obj_inv in self.browse(cr, uid, ids, context=context):
            invtype = obj_inv.type
            if invtype in ('out_invoice', 'out_refund'):
                print 'obj_inv.journal_document_class_id.sequence_id', obj_inv.journal_document_class_id.sequence_id
                if not obj_inv.journal_document_class_id.sequence_id:
                    raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related documents to this invoice.'))
                document_number = obj_sequence.next_by_id(cr, uid, obj_inv.journal_document_class_id.sequence_id.id, context)
            elif invtype in ('in_invoice', 'in_refund'):
                print 'obj_inv.supplier_invoice_number', obj_inv.supplier_invoice_number
                document_number = obj_inv.supplier_invoice_number
            print 'document_number', document_number
            obj_inv.write({'document_number':document_number})
        return super(account_invoice, self).action_number(cr, uid, ids, context)

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            # TODO si deja de ser related hay que blanquearlo
            # 'document_number':False,
            })
        return super(account_invoice, self).copy(cr, uid, id, default, context)

# TODO ver si la necesito para el resto
    # def get_journal_type(self, cr, uid, invoice_type, context=None):
    #     if invoice_type == 'in_invoice':
    #         journal_type = 'purchase'
    #     elif invoice_type == 'in_refund':
    #         journal_type = 'purchase_refund'
    #     elif invoice_type == 'out_invoice':
    #         journal_type = 'sale'
    #     elif invoice_type == 'out_refund':
    #         journal_type = 'sale_refund'
    #     else:
    #         journal_type = False
    #     return journal_type

# TODO ver si queremos agregar esta validacion en algun lugar
    # def afip_validation(self, cr, uid, ids, context=None):
    #     for invoice in self.browse(cr, uid, ids):
    #         journal_type = self.get_journal_type(cr, uid, invoice.type, context=context)
    #         journal_ids = self.get_valid_journals(cr, uid, invoice.partner_id.id, journal_type, company_id=invoice.company_id.id)
    #         if invoice.journal_id.id not in journal_ids:
    #             raise osv.except_osv(_('Invalid Journal'),
    #                 _('Invalid journal selection for actual partner and company.'))

# TODO change this function to choose correct letter    
    # def onchange_partner_id(self, cr, uid, ids, type, partner_id,
    #                         date_invoice=False, payment_term=False,
    #                         partner_bank_id=False, company_id=False, context=None):
    #     result = super(account_invoice,self).onchange_partner_id(cr, uid, ids,
    #                    type, partner_id, date_invoice, payment_term,
    #                    partner_bank_id, company_id,)
        
    #     journal_type = self.get_journal_type(cr, uid, type, context=context)        

    #     journal_id = False
    #     journal_ids = False
        
    #     if company_id and partner_id:
    #         journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)
    #     if journal_ids:            
    #         journal_id = journal_ids[0]
        
    #     if 'value' not in result: result['value'] = {}
    #     result['value'].update({
    #        'journal_id': journal_id,
    #     })      

    #     if 'domain' not in result: result['domain'] = {}          
    #     result['domain'].update({
    #        'journal_id': [('id', 'in', journal_ids)],
    #     })  
    #     return result

# TODO change this function to choose correct letter
    # def _get_journal(self, cr, uid, context=None):
    #     '''We change the default _get_journal_ function. If there is a partner on the context
    #     we will try to choose the right journal'''

    #     res = super(account_invoice,self)._get_journal(cr, uid, context=context)
    #     partner_id = context.get('partner_id', False)
    #     journal_type = context.get('journal_type', False)
    #     if not partner_id:
    #         partner_id = context.get('default_partner_id', False)            
    #     if partner_id and journal_type:
    #         user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
    #         company_id = context.get('company_id', user.company_id.id)
    #         journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)
    #         if journal_ids: 
    #             res = journal_ids[0]
    #     return res

# TODO change this function to choose correct letter
    # def create(self, cr, uid, vals, context=None):
    #     ''' Modify create function so it can try to set a right journal for the invoice'''
    #     if not context:
    #         context = {}
    #     partner_id = vals.get('partner_id', False)
    #     journal_type = vals.get('journal_type', False)
    #     if not journal_type:
    #         invoice_type = vals.get('type', False)
    #         journal_type = self.get_journal_type(cr, uid, invoice_type, context=context)      
    #     if partner_id and journal_type:
    #         user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
    #         company_id = vals.get('company_id', context.get('company_id',user.company_id.id))
    #         journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)
    #         if journal_ids:
    #             vals['journal_id'] = journal_ids[0]
    #     return super(account_invoice, self).create(cr, uid, vals, context)

# Ver si la necesito para el resto
    # def get_valid_journals(self, cr, uid, partner_id, journal_type, company_id=False, context=None):
    #     # journal_type could be purchase or sale
    #     if context is None:
    #         context = {}
            
    #     journal_obj = self.pool.get('account.journal')
    #     document_letter_obj = self.pool.get('afip.document_letter')
    #     user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
    #     partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)

    #     partner = partner.commercial_partner_id
    #     # journal_subtype = context.get('journal_subtype', False)
    #     journal_subtype = context.get('journal_subtype', 'invoice')

    #     if company_id == False:
    #         company_id = context.get('company_id', user.company_id.id) 
    #     company = self.pool.get('res.company').browse(cr, uid, company_id, context)

    #     journal_ids = []
    #     journal_filter = []
    #     journal_filter.append(('company_id','=',company_id))
    #     map_invoice = False
    #     if journal_type in ['sale','sale_refund']:
    #         issuer_responsability_id = company.partner_id.responsability_id.id
    #         receptor_responsability_id = partner.responsability_id.id 
    #         if company.map_customer_invoice_journals:
    #             map_invoice = True
    #     elif journal_type in ['purchase','purchase_refund']:
    #         issuer_responsability_id = partner.responsability_id.id    
    #         receptor_responsability_id = company.partner_id.responsability_id.id
    #         if company.map_supplier_invoice_journals:
    #             map_invoice = True            
    #     else:
    #         raise orm.except_orm(_('Journal Type Error'),
    #                 _('Journal Type Not defined)'))

    #     journal_filter.append(('type','=',journal_type))
    #     if journal_type in ['sale', 'purchase']:
    #         journal_filter.append(('journal_subtype','=',journal_subtype))
            
    #     # Now we check if the company has mapping journals enable
    #     if map_invoice:
    #         if not company.partner_id.responsability_id.id:
    #             raise orm.except_orm(_('Your company has not setted any responsability'),
    #                     _('Please, set your company responsability in the company partner before continue.'))            
    #             _logger.warning('Your company "%s" has not setted any responsability.' % company.name)

    #         document_letter_ids = document_letter_obj.search(cr, uid, [('issuer_ids', 'in', issuer_responsability_id),('receptor_ids', 'in', receptor_responsability_id)], context=context)
    #         journal_filter.extend(['|','|',('afip_document_class_id.document_letter_id','in',document_letter_ids),('afip_document_class_id.document_letter_id','=',False),('afip_document_class_id','=',False)])
    #     journal_ids = journal_obj.search(cr, uid, journal_filter, context=context)
    #     print 'journal_filter', journal_filter
    #     print 'journal_ids', journal_ids
    #     return journal_ids  

# TODO change this function to choose correct letter
    # def onchange_company_id(self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id, context=None): 
    #     result = super(account_invoice,self).onchange_company_id(cr, uid, ids,
    #                    company_id, part_id, type, invoice_line, currency_id)
    #     partner_id = part_id

    #     journal_type = self.get_journal_type(cr, uid, type, context=context)   

    #     journal_id = False
    #     journal_ids = False
    #     normal_journal_ids = False
        
    #     if company_id and partner_id:
    #         normal_journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)
    #         journal_ids = self.get_valid_journals(cr, uid, partner_id, journal_type, company_id=company_id, context=context)

    #     if normal_journal_ids:            
    #         journal_id = normal_journal_ids[0]
        
    #     if 'value' not in result: result['value'] = {}
    #     result['value'].update({
    #        'journal_id': journal_id,
    #     })      

    #     if 'domain' not in result: result['domain'] = {}          
    #     result['domain'].update({
    #        'journal_id': [('id', 'in', journal_ids)],
    #     })    

    #     return result      

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

