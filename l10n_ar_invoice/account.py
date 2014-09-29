# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class afip_tax_code(osv.osv):
    _inherit = 'account.tax.code'

    def _get_parent_afip_code(self, cr, uid, ids, field_name, args, context=None):
        r = {}

        for tc in self.read(cr, uid, ids, ['afip_code', 'parent_id'], context=context):
            _id = tc['id']
            if tc['afip_code']:
                r[_id] = tc['afip_code']
            elif tc['parent_id']:
                p_id = tc['parent_id'][0]
                r[_id] = self._get_parent_afip_code(cr, uid, [p_id], None, None)[p_id]
            else:
                r[_id] = 0

        return r

    _columns = {
        'afip_code': fields.integer('AFIP Code'),
        'parent_afip_code': fields.function(_get_parent_afip_code, type='integer', method=True, string='Parent AFIP Code', readonly=1),
    }

    def get_afip_name(self, cr, uid, ids, context=None):
        r = {}

        for tc in self.browse(cr, uid, ids, context=context):
            if tc.afip_code:
                r[tc.id] = tc.name
            elif tc.parent_id:
                r[tc.id] = tc.parent_id.get_afip_name()[tc.parent_id.id]
            else:
                r[tc.id] = False

        return r

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
        'point_of_sale_id': fields.many2one('afip.point_of_sale', 'Point of sale'),
        'point_of_sale': fields.related(
            'point_of_sale_id', 'number', type='integer', string='Point of sale', readonly=True), #for compatibility
        'use_documents': fields.boolean('Use Documents?'),
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
