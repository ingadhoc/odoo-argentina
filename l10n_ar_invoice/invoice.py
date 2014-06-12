# -*- coding: utf-8 -*-
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

    def _get_available_document_letters(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            journal_type = self.get_journal_type(cr, uid, invoice.type, context=context)
            letter_ids = self.get_valid_document_letters(cr, uid, invoice.partner_id.id, journal_type, company_id=invoice.company_id.id)            
            result[invoice.id] = letter_ids
        return result

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
        # TODO mejorar esto para mantenerlo parecido a odoo
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
        if not ids:
            ids = self.search(cr, user, [('document_number',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    _columns = {
        'printed_amount_untaxed': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Subtotal', multi='printed',),
        'printed_tax_ids': fields.function(_printed_prices, type='one2many', relation='account.invoice.tax', string='Tax', multi='printed'),
        'available_document_letter_ids': fields.function(_get_available_document_letters, relation='afip.document_letter', type='many2many', string='Available Document Letters'),
        # TODO este campo no deberia estar duplicado aca y en el account.move
        'journal_document_class_id': fields.many2one('account.journal.afip_document_class', 'Documents Class'),
        'document_number': fields.related('move_id','document_number', type='char', readonly=True, size=64, relation='account.move', store=True, string='Document Number'),
    }

    def action_number(self, cr, uid, ids, context=None):
        obj_sequence = self.pool.get('ir.sequence')
        for obj_inv in self.browse(cr, uid, ids, context=context):
            invtype = obj_inv.type
            # if we have a journal_document_class_id is beacuse we are in a company that use this function
            if obj_inv.journal_document_class_id:
                if invtype in ('out_invoice', 'out_refund'):
                    if not obj_inv.journal_document_class_id.sequence_id:
                        raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related documents to this invoice.'))
                    document_number = obj_sequence.next_by_id(cr, uid, obj_inv.journal_document_class_id.sequence_id.id, context)
                elif invtype in ('in_invoice', 'in_refund'):
                    document_number = obj_inv.supplier_invoice_number
                obj_inv.write({'document_number':document_number})
        return super(account_invoice, self).action_number(cr, uid, ids, context)

    # TODO si deja de ser related hay que blanquearlo
    # def copy(self, cr, uid, id, default=None, context=None):
    #     default = default or {}
    #     default.update({
    #         # 'document_number':False,
    #         })
    #     return super(account_invoice, self).copy(cr, uid, id, default, context)

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

    def get_valid_document_letters(self, cr, uid, partner_id, journal_type, company_id=False, context=None):
        if context is None:
            context = {}

        document_letter_obj = self.pool.get('afip.document_letter')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)

        if not partner_id or not company_id or not journal_type:
            return []
            
        partner = partner.commercial_partner_id

        if company_id == False:
            company_id = context.get('company_id', user.company_id.id) 
        company = self.pool.get('res.company').browse(cr, uid, company_id, context)

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

        if map_invoice:
            if not company.partner_id.responsability_id.id:
                raise orm.except_orm(_('Your company has not setted any responsability'),
                        _('Please, set your company responsability in the company partner before continue.'))            
                _logger.warning('Your company "%s" has not setted any responsability.' % company.name)

            document_letter_ids = document_letter_obj.search(cr, uid, [('issuer_ids', 'in', issuer_responsability_id),('receptor_ids', 'in', receptor_responsability_id)], context=context)
        return document_letter_ids          

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,
                            date_invoice=False, payment_term=False,
                            partner_bank_id=False, company_id=False, journal_id=False):
        result = super(account_invoice,self).onchange_partner_id(cr, uid, ids,
                       type, partner_id, date_invoice, payment_term,
                       partner_bank_id, company_id,)
        if 'value' not in result: result['value'] = {}                
        journal_document_class_id = False
        if journal_id and partner_id:
            journal_type = self.get_journal_type(cr, uid, type)
            letter_ids = self.get_valid_document_letters(cr, uid, partner_id, journal_type, company_id=company_id)
            domain = ['|',('afip_document_class_id.document_letter_id','=',False),('afip_document_class_id.document_letter_id','in',letter_ids),('journal_id','=',journal_id)]
            journal_document_class_ids = self.pool['account.journal.afip_document_class'].search(cr, uid, domain)
            if journal_document_class_ids:
                journal_document_class_id = journal_document_class_ids[0]
            if 'domain' not in result: result['domain'] = {}          
            result['domain']['journal_document_class_id'] = [('id', 'in', journal_document_class_ids)]
        result['value']['journal_document_class_id'] = journal_document_class_id
        return result

    def onchange_journal_id(self, cr, uid, ids, journal_id=False, partner_id=False, context=None):
        result = super(account_invoice, self).onchange_journal_id(cr, uid, ids, journal_id, context)
        journal_document_class_id = False        
        if journal_id and partner_id:
            journal = self.pool['account.journal'].browse(cr, uid, journal_id)
            journal_type = journal.type
            letter_ids = self.get_valid_document_letters(cr, uid, partner_id, journal_type, company_id=journal.company_id.id)
            domain = ['|',('afip_document_class_id.document_letter_id','=',False),('afip_document_class_id.document_letter_id','in',letter_ids),('journal_id','=',journal_id)]
            journal_document_class_ids = self.pool['account.journal.afip_document_class'].search(cr, uid, domain)
            if journal_document_class_ids:
                journal_document_class_id = journal_document_class_ids[0]
            if 'domain' not in result: result['domain'] = {}        
            result['domain']['journal_document_class_id'] = [('id', 'in', journal_document_class_ids)]  
        result['value']['journal_document_class_id'] = journal_document_class_id
        return result

    def create(self, cr, uid, vals, context=None):
        ''' Modify create function so it can try to set a right document for the invoice'''
        if not context:
            context = {}
        partner_id = vals.get('partner_id', False)
        journal_id = vals.get('journal_id', False)
        if journal_id and partner_id:
            journal = self.pool['account.journal'].browse(cr, uid, journal_id)
            journal_type = journal.type
            letter_ids = self.get_valid_document_letters(cr, uid, partner_id, journal_type, company_id=journal.company_id.id)
            domain = ['|',('afip_document_class_id.document_letter_id','=',False),('afip_document_class_id.document_letter_id','in',letter_ids),('journal_id','=',journal_id)]
            journal_document_class_ids = self.pool['account.journal.afip_document_class'].search(cr, uid, domain)
            if journal_document_class_ids:
                vals['journal_document_class_id'] = journal_document_class_ids[0]
        return super(account_invoice, self).create(cr, uid, vals, context)