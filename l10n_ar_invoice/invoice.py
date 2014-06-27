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
            letter_ids = []
            if invoice.use_documents:
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
                printed_amount_untaxed = sum(line.printed_price_subtotal for line in invoice.invoice_line)
                printed_tax_ids = [x.id for x in invoice.tax_line if not x.tax_code_id.vat_tax]
            res[invoice.id] = {
                'printed_amount_untaxed': printed_amount_untaxed,
                'printed_tax_ids': printed_tax_ids,
                'printed_amount_tax': invoice.amount_total - printed_amount_untaxed,
            }
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        types = {
                'out_invoice': _('Invoice'),
                'in_invoice': _('Supplier Invoice'),
                'out_refund': _('Refund'),
                'in_refund': _('Supplier Refund'),
                }
        return [(r['id'], '%s %s' % (r['reference'] or types[r['type']], r['number'] or '')) for r in self.read(cr, uid, ids, ['type', 'number', 'reference'], context, load='_classic_write')]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('reference','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('reference',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    _columns = {
        'printed_amount_tax': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Tax', multi='printed',),
        'printed_amount_untaxed': fields.function(_printed_prices, type='float', digits_compute=dp.get_precision('Account'), string='Subtotal', multi='printed',),
        'printed_tax_ids': fields.function(_printed_prices, type='one2many', relation='account.invoice.tax', string='Tax', multi='printed'),
        'available_document_letter_ids': fields.function(_get_available_document_letters, relation='afip.document_letter', type='many2many', string='Available Document Letters'),
        'journal_document_class_id': fields.many2one('account.journal.afip_document_class', 'Documents Type', readonly=True, states={'draft':[('readonly',False)]}),
        'afip_document_class_id': fields.related('journal_document_class_id', 'afip_document_class_id',relation='afip.document_class', type='many2one', string='Document Type', readonly=True, store=True),
        'next_invoice_number': fields.related('journal_document_class_id','sequence_id', 'number_next_actual', type='integer', string='Next Document Number', readonly=True),
        'use_documents': fields.related('journal_id','use_documents', type='boolean', string='Use Documents?', readonly=True),
    }

    def _check_reference(self, cr, uid, ids, context=None):
    # def _check_document_number(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.type in ['out_invoice','out_refund'] and invoice.reference and invoice.state == 'open':
            # if invoice.type in ['out_invoice','out_refund'] and invoice.document_number:
                domain = [('type','in',('out_invoice','out_refund')),
                    ('reference','=',invoice.reference),
                    # ('document_number','=',invoice.document_number),
                    ('journal_document_class_id.afip_document_class_id','=',invoice.journal_document_class_id.afip_document_class_id.id),
                    ('company_id','=',invoice.company_id.id),
                    ('id','!=',invoice.id)]
                invoice_ids = self.search(cr, uid, domain, context=context)
                if invoice_ids:
                    # return True
                    return False
        return True

    _sql_constraints = [
        ('number_supplier_invoice_number', 'unique(supplier_invoice_number, partner_id, company_id)', 'Supplier Invoice Number must be unique per Supplier and Company!'),
    ]

    # _constraints = [(_check_reference, 'Invoice Reference Number must be unique per Document Class and Company!', ['referece','afip_document_class_id','company_id'])]

    def create(self, cr, uid, vals, context=None):
        '''We modify create for 2 popuses:
        - Modify create function so it can try to set a right document for the invoice
        - If reference in values, we clean it for argentinian companies as it will be used for invoice number
        ''' 
        # First purpose
        if not context:
            context = {}
        partner_id = vals.get('partner_id', False)
        journal_id = vals.get('journal_id', False)
        if journal_id and partner_id:
            journal = self.pool['account.journal'].browse(cr, uid, int(journal_id), context=context)
            if journal.use_documents:
                journal_type = journal.type
                letter_ids = self.get_valid_document_letters(cr, uid, int(partner_id), journal_type, company_id=journal.company_id.id)
                domain = ['|',('afip_document_class_id.document_letter_id','=',False),('afip_document_class_id.document_letter_id','in',letter_ids),('journal_id','=',journal_id)]
                journal_document_class_ids = self.pool['account.journal.afip_document_class'].search(cr, uid, domain)
                if journal_document_class_ids:
                    vals['journal_document_class_id'] = journal_document_class_ids[0]

                # second purpose
                if 'reference' in vals:
                    vals['reference'] = False

        return super(account_invoice, self).create(cr, uid, vals, context=context)

    def action_move_create(self, cr, uid, ids, context=None):
        obj_sequence = self.pool.get('ir.sequence')
        
        # We write reference field with next invoice number by document type
        for obj_inv in self.browse(cr, uid, ids, context=context):
            invtype = obj_inv.type
            # if we have a journal_document_class_id is beacuse we are in a company that use this function
            # also if it has a reference number we use it (for example when cancelling for modification)
            if obj_inv.journal_document_class_id and not obj_inv.reference:
                if invtype in ('out_invoice', 'out_refund'):
                    if not obj_inv.journal_document_class_id.sequence_id:
                        raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related documents to this invoice.'))
                    reference = obj_sequence.next_by_id(cr, uid, obj_inv.journal_document_class_id.sequence_id.id, context)
                elif invtype in ('in_invoice', 'in_refund'):
                    reference = obj_inv.supplier_invoice_number
                obj_inv.write({'reference':reference})
        res = super(account_invoice, self).action_move_create(cr, uid, ids, context=context)
        
        # on created moves we write the document type
        for obj_inv in self.browse(cr, uid, ids, context=context):
            invtype = obj_inv.type
            # if we have a journal_document_class_id is beacuse we are in a company that use this function
            if obj_inv.journal_document_class_id:
                obj_inv.move_id.write({'document_class_id':obj_inv.journal_document_class_id.afip_document_class_id.id})
        return res

    # def action_number(self, cr, uid, ids, context=None):
    #     obj_sequence = self.pool.get('ir.sequence')
    #     for obj_inv in self.browse(cr, uid, ids, context=context):
    #         invtype = obj_inv.type
    #         # if we have a journal_document_class_id is beacuse we are in a company that use this function
    #         if obj_inv.journal_document_class_id:
    #             if invtype in ('out_invoice', 'out_refund'):
    #                 if not obj_inv.journal_document_class_id.sequence_id:
    #                     raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related documents to this invoice.'))
    #                 document_number = obj_sequence.next_by_id(cr, uid, obj_inv.journal_document_class_id.sequence_id.id, context)
    #             elif invtype in ('in_invoice', 'in_refund'):
    #                 document_number = obj_inv.supplier_invoice_number
    #             obj_inv.write({'document_number':document_number})
    #     return super(account_invoice, self).action_number(cr, uid, ids, context)

    # TODO si deja de ser related hay que blanquearlo
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'supplier_invoice_number':False,
            })
        return super(account_invoice, self).copy(cr, uid, id, default, context)

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

    def on_change_journal_document_class_id(self, cr, uid, ids, journal_document_class_id):     
        result = {}
        next_invoice_number = False
        if journal_document_class_id:
            journal_document_class = self.pool['account.journal.afip_document_class'].browse(cr, uid, journal_document_class_id)
            if journal_document_class.sequence_id:
                next_invoice_number = journal_document_class.sequence_id.number_next
        
        result['value'] = {'next_invoice_number':next_invoice_number}
        return result

    # def onchange_partner_id(self, cr, uid, ids, type, partner_id,
    #                         date_invoice=False, payment_term=False,
    #                         partner_bank_id=False, company_id=False, journal_id=False):
    #     result = super(account_invoice,self).onchange_partner_id(cr, uid, ids,
    #                    type, partner_id, date_invoice, payment_term,
    #                    partner_bank_id, company_id,)
    #     if 'value' not in result: result['value'] = {}                
    #     journal_document_class_id = False
    #     if journal_id and partner_id:
    #         journal_type = self.get_journal_type(cr, uid, type)
    #         letter_ids = self.get_valid_document_letters(cr, uid, partner_id, journal_type, company_id=company_id)
    #         domain = ['|',('afip_document_class_id.document_letter_id','=',False),('afip_document_class_id.document_letter_id','in',letter_ids),('journal_id','=',journal_id)]
    #         journal_document_class_ids = self.pool['account.journal.afip_document_class'].search(cr, uid, domain)
    #         if journal_document_class_ids:
    #             journal_document_class_id = journal_document_class_ids[0]
    #         if 'domain' not in result: result['domain'] = {}          
    #         result['domain']['journal_document_class_id'] = [('id', 'in', journal_document_class_ids)]
    #     if 'value' not in result: result['value'] = {}          
    #     result['value']['journal_document_class_id'] = journal_document_class_id
    #     return result

    def onchange_journal_id(self, cr, uid, ids, journal_id=False, partner_id=False, context=None):
        result = super(account_invoice, self).onchange_journal_id(cr, uid, ids, journal_id, context)
        journal_document_class_id = False        
        if journal_id:
            journal = self.pool['account.journal'].browse(cr, uid, journal_id)
            result['value']['use_documents'] = journal.use_documents
            if partner_id:
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