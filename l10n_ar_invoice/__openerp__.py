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
{   'active': False,
    'author': 'OpenERP - Team de Localizaci\xc3\xb3n Argentina',
    'category': 'Localization/Argentina',
    'demo_xml': [
       'data/partner_demo.xml',
      ],
    'depends': [   
                    'account',
                    'l10n_ar_base',
                   'l10n_ar_base_vat', # Es usado en los onchange de documentos y demas
                   ],
    'description': '''
\n\nM\xc3\xb3dulo de Facturaci\xc3\xb3n de la localizaci\xc3\xb3n Argentina\n\n\n\nIncluye:\n\n\n\n  - Configuraci\xc3\xb3n de libros, diarios y otros detalles para facturaci\xc3\xb3n argentina.\n\n  - Wizard para configurar los talonarios necesarios para facturar.\n\n\n\nFalta:\n\n  - Terminar de completar la lista de codigos del AFIP de monedas (http://www.afip.gob.ar/fe/documentos/TABLA%20MONEDAS%20V.0%20%2025082010.xls)\n\n
''',
    'init_xml': [],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Generador de Talonarios',
    'test': [   'test/products.yml',
                'test/partners.yml',
                'test/com_ri1.yml',
                'test/com_ri2.yml',
                'test/com_rm1.yml',
                'test/inv_ri2ri.yml',
                'test/inv_rm2ri.yml',
                'test/inv_ri2rm.yml',
                'test/bug_1042944.yml'],
    'data': [   
                      'security/l10n_ar_invoice_security.xml',
                      'wizard/journal_config_wizard_view.xml',
                      'data/responsability.xml',
                      'data/afip.document_letter.csv',
                      'data/afip.document_class.csv',
                      'data/document_type.xml', 
                      'data/partner.xml',
                      'data/invoice_workflow.xml',
                      'data/country.xml',
                      'data/res.currency.csv',
                      'data/afip.concept_type.csv',
                      'view/partner_view.xml',
                      'view/company_view.xml',
                      'view/country_view.xml',
                      'view/afip_menuitem.xml',
                      'view/afip_document_letter_view.xml',
                      'view/afip_concept_type_view.xml',
                      'view/afip_optional_type_view.xml',
                      'view/afip_document_type_view.xml',
                      'view/afip_responsability_view.xml',
                      'view/afip_document_class_view.xml',
                      'view/journal_view.xml',
                      'view/invoice_view.xml',
                      'view/res_config_view.xml',
                      'security/ir.model.access.csv'
                      ],
    'version': '2.7.243',
    'website': 'https://launchpad.net/~openerp-l10n-ar-localization'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
