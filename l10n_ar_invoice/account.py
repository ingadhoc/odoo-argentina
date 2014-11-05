# -*- coding: utf-8 -*-
from openerp.osv import fields
from openerp import fields as new_fields
from openerp import api, models, _
from openerp.exceptions import Warning


class afip_tax_code(models.Model):
    _inherit = 'account.tax.code'

    def _get_parent_afip_code(self, cr, uid, ids, field_name, args, context=None):
        r = {}

        for tc in self.read(cr, uid, ids, ['afip_code', 'parent_id'], context=context):
            _id = tc['id']
            if tc['afip_code']:
                r[_id] = tc['afip_code']
            elif tc['parent_id']:
                p_id = tc['parent_id'][0]
                r[_id] = self._get_parent_afip_code(
                    cr, uid, [p_id], None, None)[p_id]
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


class account_move(models.Model):
    _inherit = "account.move"

    def _get_document_data(self, cr, uid, ids, name, arg, context=None):
        """ TODO """
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            document_number = False
            if record.model and record.res_id:
                document_number = self.pool[record.model].browse(
                    cr, uid, record.res_id, context=context).document_number
            res[record.id] = document_number
        return res

    document_class_id = new_fields.Many2one(
        'afip.document_class',
        'Document Type',
        copy=False,
        # readonly=True
    )
    afip_document_number = new_fields.Char(
        string='Document Number',
        copy=False,)

    @api.one
    @api.depends(
        'afip_document_number',
        'name',
        'document_class_id',
        'document_class_id.doc_code_prefix',
        )
    def _get_document_number(self):
        if self.afip_document_number and self.document_class_id:
            document_number = (self.document_class_id.doc_code_prefix or '') + \
                self.afip_document_number
        else:
            document_number = self.name
        self.document_number = document_number

    document_number = new_fields.Char(
        compute='_get_document_number',
        string='Document Number',
        readonly=True,
        store=True
        )


class account_move_line(models.Model):
    _inherit = "account.move.line"

    document_class_id = new_fields.Many2one(
        'afip.document_class',
        'Document Type',
        related='move_id.document_class_id',
        store=True,
        readonly=True,
    )
    document_number = new_fields.Char(
        string='Document Number',
        related='move_id.document_number',
        store=True,
        readonly=True,
        )


class account_journal_afip_document_class(models.Model):
    _name = "account.journal.afip_document_class"
    _description = "Journal Afip Documents"

    def name_get(self, cr, uid, ids, context=None):
        result = []
        for record in self.browse(cr, uid, ids, context=context):
            result.append((record.id, record.afip_document_class_id.name))
        return result

    _order = 'journal_id desc, sequence, id'

    _columns = {
        'afip_document_class_id': fields.many2one('afip.document_class', 'Document Type', required=True),
        'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', required=False, help="This field contains the information related to the numbering of the documents entries of this document type."),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'sequence': fields.integer('Sequence',),
    }


class account_journal(models.Model):
    _inherit = "account.journal"
    _columns = {
        'journal_document_class_ids': fields.one2many('account.journal.afip_document_class', 'journal_id', 'Documents Class',),
        'point_of_sale_id': fields.many2one('afip.point_of_sale', 'Point of sale'),
        'point_of_sale': fields.related(
            'point_of_sale_id', 'number', type='integer', string='Point of sale', readonly=True),  # for compatibility
        'use_documents': fields.boolean('Use Documents?'),
    }

    @api.one
    @api.constrains('point_of_sale_id', 'company_id')
    def _check_company_id(self):
        if self.point_of_sale_id and self.point_of_sale_id.company_id != self.company_id:
            raise Warning(_('The company of the point of sale and of the \
                journal must be the same!'))


class res_currency(models.Model):
    _inherit = "res.currency"
    _columns = {
        'afip_code': fields.char('AFIP Code', size=4),
    }
