# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Argentina - Web Services de Factura Electrónica del AFIP",
    'version': '8.0.1.6.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
API y GUI para acceder a las Web Services de Factura Electrónica de la AFIP
===========================================================================
TODO analizar que hacemos con la clase afip error, a ver si la aprovechamos en
algun lugar
""",
    'depends': [
        'l10n_ar_afipws',
    ],
    'external_dependencies': {
    },
    'data': [
        'wizard/afip_ws_consult_wizard_view.xml',
        'wizard/afip_ws_currency_rate_wizard_view.xml',
        'views/invoice_view.xml',
        'views/journal_afip_document_class_view.xml',
        'views/wsfe_error_view.xml',
        'views/afip_point_of_sale_view.xml',
        'views/product_uom_view.xml',
        'views/res_currency_view.xml',
        'views/res_company_view.xml',
        'data/afip.wsfe_error.csv',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/account_demo.xml',
        'demo/ri_sale_invoice_demo.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
