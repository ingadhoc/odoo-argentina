# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class account_move(osv.osv):
    _inherit = "account.move"

    def _get_document_data(self, cr, uid, ids, name, arg, context=None):
        """ TODO """
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            document_number = False
            if record.model and record.res_id:
                document_number = self.pool[record.model].browse(cr, uid, record.res_id, context=context).document_number
            res[record.id] = document_number
        return res

    _columns = {
        'document_class_id': fields.many2one('afip.document_class', 'Document Type', readonly=True),
    }

class account_journal_afip_document_class(osv.osv):
    _name = "account.journal.afip_document_class"
    _description = "Journal Afip Documents"

    def name_get(self, cr, uid, ids, context=None):
        result= []
        for record in self.browse(cr, uid, ids, context=context):
            result.append((record.id,record.afip_document_class_id.name))
        return result

    _order = 'journal_id desc, sequence, id'
    
    _columns = {
        'afip_document_class_id': fields.many2one('afip.document_class', 'Document Type', required=True),
        'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', required=False, help="This field contains the information related to the numbering of the documents entries of this document type."),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'sequence': fields.integer('Sequence',),
    }

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'journal_document_class_ids': fields.one2many('account.journal.afip_document_class','journal_id','Documents Class',),
        'point_of_sale': fields.integer('Point of sale'),
        'use_documents': fields.boolean('Use Documents?'),

    _defaults = {
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
