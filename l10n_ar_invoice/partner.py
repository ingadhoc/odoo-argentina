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
from openerp.tools.translate import _
import re

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'responsability_id': fields.many2one('afip.responsability', 'Resposability'),
        'document_type_id': fields.many2one('afip.document_type', 'Document type',
                                            on_change="onchange_document(vat,document_type_id,document_number)"),
        'document_number': fields.char('Document number', size=64, select=1,
                                       on_change="onchange_document(vat,document_type_id,document_number)"),
        'iibb': fields.char('Ingresos Brutos', size=64),
        'start_date': fields.date('Inicio de actividades'),
    }

    def onchange_document(self, cr, uid, ids, vat, document_type, document_number, context={}):
        v = {}
        m = None
        mod_obj = self.pool.get('ir.model.data')
        if document_number and (u'afip.document_type', document_type) == mod_obj.get_object_reference(cr, uid, 'l10n_ar_invoice', 'dt_CUIT'):
            document_number = re.sub('[^1234567890]','',str(document_number))
            if not self.check_vat_ar(document_number):
                m = {'title': _('Warning!'),
                     'message': _('VAT Number is wrong.\n Please verify the number before continue.'), }
            if vat == False:
                v['vat'] = 'AR%s' % document_number
            v['document_number'] = document_number
        return { 'value': v,
                 'warning': m }

    def onchange_vat(self, cr, uid, ids, vat, document_type, document_number, context={}):
        """
        Not used because is complex to integrate.
        Could be associated to country?
        """
        doc_type_obj = self.pool.get('afip.document_type')
        country_obj = self.pool.get('res.country')

        cuit_document_type_id = doc_type_obj.search(cr, uid, [('code','=','CUIT')])

        v = {}
        if vat[:2].lower()=='ar' and document_type==False and document_number==False:
            v['document_type'] = cuit_document_type_id
            v['document_number'] = vat[2:]
        elif document_type==False and document_number==False:
            country_ids = countr_obj.search(cr, uid, [('code','=',vat[:2].upper())])
            iva_data = countr_obj.read(cr, uid, country_ids, ['cuit_juridica','cuit_fisica'])
            v['document_type'] = cuit_document_type_id
            v['document_number'] = iva_data['cuit_juridica' if is_company else 'cuit_fisica']

        return { 'value': v }


    def afip_validation(sefl, cr, uid, ids, context={}):
        """ Hay que validar si el partner no es de tipo 'consumidor final' tenga un CUIT asociado.
            - Si el cuit es extrangero, hay que asignar a document_number y document_type los correspondientes
            a la interpretación argentina del CUIT.
            - Si es responsable monotributo hay que asegurarse que tenga vat asignado. El documento y
            número de documento deberían ser DNI.
            - Si es responsable inscripto y persona juridica indicar el cuit copia del VAT.
            El objetivo es que en la generación de factura utilice la información de document_type y document_number.
            
            Otra opción es asignar a la argentina los prefijos: 'cuit' 'dni' 'ci', etc...
            
            Del prefijo se toma el número de documento. Que opinanará la comunidad?"""
        
        for part in self.read(cr, uid, ids, ['document_number', 'document_type_id', 'vat', 'is_vat_subject']):
            pass

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
