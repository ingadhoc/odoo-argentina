# -*- coding: utf-8 -*-
from openerp.osv import osv, fields


class account_voucher_receiptbook (osv.osv):

    _inherit = "account.voucher.receiptbook"

    _columns = {
        'afip_document_class_id': fields.many2one(
            'afip.document_class', 'Afip Document Class'),
    }


class account_voucher_receipt (osv.osv):

    _inherit = "account.voucher.receipt"

    _columns = {
        # TODO podemos hacer como en invoice el tema de los recipts, es decir que se pueda tener una lista y luego sean mapeados segun las responsabilidades
        # 'receipt_document_class_ids': fields.one2many('account.voucher.receipt.afip_document_class','receipt_id','Documents Class',),
        # 'point_of_sale': fields.integer('Point of sale'),
    }

    def post_receipt(self, cr, uid, ids, context=None):
        res = super(account_voucher_receipt, self).post_receipt(
            cr, uid, ids, context)
        for receipt in self.browse(cr, uid, ids, context=context):
            for voucher in receipt.voucher_ids:
                voucher.move_id.write({
                    'afip_document_number': receipt.name,
                    'document_class_id': receipt.receiptbook_id.afip_document_class_id and receipt.receiptbook_id.afip_document_class_id.id or False,
                })
        return res

# class account_journal_afip_document_class(osv.osv):
#     _name = "account.voucher.receipt.afip_document_class"
#     _description = "Voucher Receipt Afip Documents"

#     def name_get(self, cr, uid, ids, context=None):
#         result= []
#         for record in self.browse(cr, uid, ids, context=context):
#             result.append((record.id,record.afip_document_class_id.name))
#         return result

#     _order = 'journal_id desc, sequence, id'

#     _columns = {
#         'afip_document_class_id': fields.many2one('afip.document_class', 'Afip Document Class', required=True),
#         'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', required=False, help="This field contains the information related to the numbering of the documents entries of this document class."),
#         'receipt_id': fields.many2one('account.voucher.receipt', 'Receipt', required=True),
#         'sequence': fields.integer('Sequence',),
#     }
