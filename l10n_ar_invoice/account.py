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

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'code': fields.char('Code', size=10, required=True,
                            help="The code will be used to generate the numbers of the journal entries of this journal."),
        'point_of_sale': fields.integer('Point of sale ID'),
        'journal_subtype': fields.selection([('invoice','Invoices'),('debit_note','Debit Notes'),('other_document','Other Documents')], string='Journal Subtype', help='It defines some behaviours on automatic journal selection and in menus where it is shown.'),        
        # 'journal_subtype': fields.selection([('invoice','Invoices'),('credit_note','Credit Notes'),('debit_note','Debit Notes'),('other_document','Other Documents')], string='Journal Subtype', help='It defines some behaviours on automatic journal selection and in menus where it is shown.'),
        'afip_document_class_id': fields.many2one('afip.document_class', 'Afip Document Class'),
        'product_types': fields.char('Product types',
                                     help='Only use products with this product types in this journals. '
                                     'Types must be a subset of adjust, consu and service separated by commas.'),
    }

    def on_change_afip_document_class(self, cr, uid, ids, afip_document_class_id, code, context=None):
        # TODO hacer esta funcion y agregar funcionalidad de puntos de venta
        if afip_document_class_id and not code:
            print 'return codigo del diario'
            return {}
        return {}

    def _check_product_types(self, cr, uid, ids, context=None):
        for jc in self.browse(cr, uid, ids, context=context):
            if jc.product_types:
                types = set(jc.product_types.split(','))
                res = types.issubset(['adjust','consu','service'])
            else:
                res = True
        return res

    _constraints = [(_check_product_types, 'You provided an invalid list of product types. Must been separated by commas.', ['product_types'])]

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
