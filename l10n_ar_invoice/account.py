# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class account_move(osv.osv):
    _inherit = "account.move"
    _columns = {
        'afip_document_class_id': fields.many2one('afip.document_class', 'Afip Document Class'),
        'document_number': fields.char('Document Number', size=64, required=True),
        # 'documen_model_id': fields.function(_get_document_data, string='Document Model',
        #     type='many2one', relation='account.invoice', fnct_search=_invoice_search),
        # 'model': fields.char('Related Document Model', size=128, select=1),
        # 'res_id': fields.integer('Related Document ID', select=1),
        # 'document_id': fields.reference('Source Document', required=True, selection=_get_document_types, size=128),        
    }

class account_journal_afip_document_class(osv.osv):
    _name = "account.journal.afip_document_class"
    _description = "Journal Afip Documents"

    def name_get(self, cr, uid, ids, context=None):
        # res = {}
        result= []
        # if not all(ids):
        #     return result        
        for record in self.browse(cr, uid, ids, context=context):
            result.append((record.id,record.afip_document_class_id.name))
            # res[record.id] = record.afip_document_class_id.name
        return result
# TODO hacer esta funcion search
    # def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
    #     if not args:
    #         args = []
    #     if context is None:
    #         context = {}
    #     ids = []
    #     if name:
    #         ids = self.search(cr, user, [('document_number','=',name)] + args, limit=limit, context=context)
    #         # ids = self.search(cr, user, [('number','=',name)] + args, limit=limit, context=context)
    #     if not ids:
    #         ids = self.search(cr, user, [('document_number',operator,name)] + args, limit=limit, context=context)
    #         # ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
    #     return self.name_get(cr, user, ids, context)        

    _order = 'journal_id desc, sequence, id'
    
    _columns = {
        'afip_document_class_id': fields.many2one('afip.document_class', 'Afip Document Class', required=True),
        'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', required=False, help="This field contains the information related to the numbering of the documents entries of this document class."),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of sales order lines."),
    }

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
# No lo queremos sobre escribir por ahora
        # 'code': fields.char('Code', size=10, required=True,
        #                     help="The code will be used to generate the numbers of the journal entries of this journal."),
        'journal_document_class_ids': fields.one2many('account.journal.afip_document_class','journal_id','Documents Class',),
        'point_of_sale': fields.integer('Point of sale'),
        'journal_subtype': fields.selection([('invoice','Invoices'),('debit_note','Debit Notes'),('other_document','Other Documents')], string='Journal Subtype', help='It defines some behaviours on automatic journal selection and in menus where it is shown.'),        
        # 'journal_subtype': fields.selection([('invoice','Invoices'),('credit_note','Credit Notes'),('debit_note','Debit Notes'),('other_document','Other Documents')], string='Journal Subtype', help='It defines some behaviours on automatic journal selection and in menus where it is shown.'),        
# Lo agregamos si lo necesitamos mas adelante
        # 'product_types': fields.char('Product types',
        #                              help='Only use products with this product types in this journals. '
        #                              'Types must be a subset of adjust, consu and service separated by commas.'),
    }

    # def _check_product_types(self, cr, uid, ids, context=None):
    #     for jc in self.browse(cr, uid, ids, context=context):
    #         if jc.product_types:
    #             types = set(jc.product_types.split(','))
    #             res = types.issubset(['adjust','consu','service'])
    #         else:
    #             res = True
    #     return res

    # _constraints = [(_check_product_types, 'You provided an invalid list of product types. Must been separated by commas.', ['product_types'])]

    _defaults = {
        'journal_subtype': 'invoice',
    }

class res_currency(osv.osv):
    _inherit = "res.currency"
    _columns = {
        'afip_code': fields.char('AFIP Code', size=4),
    }

class account_tax_code(osv.osv):
    _inherit = "account.tax.code"
    _columns = {
        'vat_tax': fields.boolean('VAT Tax?', help="If VAT tax then it will or not be printed on invoices acording partners responsabilities, also, it will or not be use on vat declaration"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
