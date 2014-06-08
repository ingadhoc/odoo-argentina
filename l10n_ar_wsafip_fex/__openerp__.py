# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2013 Elepe Servicios (http://www.elepeservicios.com.ar)
# All Rights Reserved
#
# Author : Dario Kevin De Giacomo (Elepe Servicios)
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
    'author': 'Dar\xc3\xado Kevin De Giacomo (Elepe Servicios >> www.elepeservicios.com.ar)',
    'category': 'Localization/Argentina',
    'demo_xml': [],
    'depends': ['l10n_ar_wsafip_fe',
                'l10n_ar_states'
                ],
    'description': '\n\nAPI e GUI para acceder a las Web Services de Factura Electr\xc3\xb3nica de Exportaci\xc3\xb3n de la AFIP\n\n',
    'init_xml': [
                      'data/res_country_afip_code.xml',
                      'data/res_currency_afip_code.xml',
                      'data/product_uom_afip_code.xml',
                      ],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Web Services de F.E. de Exportaci\xc3\xb3n del AFIP',
    'update_xml': [  
                      'data/wsafip_server.xml', 
                      'data/invoice_view.xml',
                      'data/invoice_workflow.xml',
                      'data/journal_view.xml',
                      'data/reports.xml',
                      'data/wsafip_fex_config.xml',
                      'data/res_config_view.xml',
                      'security/ir.model.access.csv',
                      ],
    'version': '2.7.243',
    'website': 'https://launchpad.net/~openerp-l10n-ar-localization'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
