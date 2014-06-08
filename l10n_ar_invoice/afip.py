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
from openerp.osv import fields, osv

class afip_document_class(osv.osv):
    _name = 'afip.document_class'
    _description = 'Afip Document Class'
    _columns = {
        'name': fields.char('Name', size=120),
        'code_template': fields.char('Code Template for Journal'),
        'afip_code': fields.integer('AFIP Code',required=True),
        'document_letter_id': fields.many2one('afip.document_letter', 'Document Letter'),
        'journal_subtype': fields.selection([('invoice','Invoices'),('credit_note','Credit Notes'),('debit_note','Debit Notes'),('other_document','Other Documents')], string='Journal Subtype', help='It defines some behaviours on automatic journal selection and in menus where it is shown.'),        
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }    

    def create_journals(cr, uid, ids, context=None):
        account_obj = self.pool['account.journal']
        sequence_obj = self.pool['ir.sequence']
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        
        point_of_sale = context.get('point_of_sale', 1)
        sequence_id = context.get('sequence_id', False)        
        company_id = context.get('company_id', user.company_id.id) 
        
        for record in self.browse(cr, uid, ids, context=context):
            name = u"%s (%04i-%s)" % (record.name, point_of_sale, record.code_template)

            if not sequence_id:
                # TODO make prefix, suffix, padding and implementation configurable
                seq_vals = {
                    'name': name,
                    'prefix': u"%s%04i" % (record.code_template, point_of_sale),
                    # 'suffix': , 
                    'padding': 8,
                    'implementation': 'no_gap',
                }
                sequence_id = sequence_obj.create(cr, uid, seq_vals, context=context)
            vals = {
                'name': name,
                'code': u"%s%04i" % (record.code_template, point_of_sale),
                'afip_document_class_id': record.id,
                'company_id': company_id,
                'point_of_sale': point_of_sale,
                'sequence_id': sequence_id,
                # 'sequence_name': rel[item['row']],
                'type': item['type'],
            }
            account_obj.create(cr, uid, vals, context=context)

class afip_document_letter(osv.osv):
    _name='afip.document_letter'
    _description='Document letter'
    _columns={
        'name': fields.char('Name', size=64, required=True),
        'afip_document_class_ids': fields.one2many('afip.document_class', 'document_letter_id', 'Afip Document Classes'),
        'issuer_ids': fields.many2many('afip.responsability', 'afip_doc_letter_issuer_rel', 'letter_id', 'responsability_id', 'Issuers',),
        'receptor_ids': fields.many2many('afip.responsability', 'afip_doc_letter_receptor_rel', 'letter_id', 'responsability_id', 'Receptors',),
        'active': fields.boolean('Active'),
    }
    _sql_constraints = [('name','unique(name)', 'Not repeat name!'),]

    _defaults = {
        'active': True,
    }    

class afip_responsability(osv.osv):
    _name='afip.responsability'
    _description='VAT Responsability'
    _columns={
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=8, required=True),
        'active': fields.boolean('Active'),
        'issued_letter_ids': fields.many2many('afip.document_letter', 'afip_doc_letter_issuer_rel', 'responsability_id', 'letter_id', 'Issued Document Letters'),
        'received_letter_ids': fields.many2many('afip.document_letter', 'afip_doc_letter_receptor_rel', 'responsability_id', 'letter_id', 'Received Document Letters'),
    }
    _sql_constraints = [('name','unique(name)', 'Not repeat name!'),
                        ('code','unique(code)', 'Not repeat code!')]

    _defaults = {
        'active': True,
    }

class afip_document_type(osv.osv):
    _name = 'afip.document_type'
    _description='AFIP document types'
    _columns = {
        'name': fields.char('Name', size=120,required=True),
        'code': fields.char('Code', size=16,required=True),
        'afip_code': fields.integer('AFIP Code',required=True),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }

class afip_concept_type(osv.osv):
    _name = 'afip.concept_type'
    _description='AFIP concept types'
    _columns = {
        'name': fields.char('Name', size=120,required=True),
        'afip_code': fields.integer('AFIP Code',required=True),
        'active': fields.boolean('Active'),
        'product_types': fields.char('Product types',
                                     help='Translate this product types to this AFIP concept. '
                                     'Types must be a subset of adjust, consu and service separated by commas.',required=True),
    }

    _defaults = {
        'active': True,
    }    

    def _check_product_types(self, cr, uid, ids, context=None):
        for ct in self.browse(cr, uid, ids, context=context):
            if ct.product_types:
                types = set(ct.product_types.split(','))
                res = types.issubset(['adjust','consu','service'])
            else:
                res = True
        return res

    _constraints = [(_check_product_types, 'You provided an invalid list of product types. Must been separated by commas',['product_types'])]

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

class afip_optional_type(osv.osv):
    _name = 'afip.optional_type'
    _description='AFIP optional types'
    _columns = {
        'name': fields.char('Name', size=120,required=True),
        'afip_code': fields.integer('AFIP Code',required=True),
        'apply_rule': fields.char('Apply rule'),
        'value_computation': fields.char('Value computation'),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
