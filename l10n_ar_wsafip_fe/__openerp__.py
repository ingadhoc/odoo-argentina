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
                #'test/invoice.yml',
                #'test/inv_2prod.yml',
                #'test/inv_2iva.yml',
                #'test/query_invoices.yml'
{   'active': False,
    'author': 'OpenERP - Team de Localizaci\xc3\xb3n Argentina',
    'category': 'Localization/Argentina',
    'demo_xml': [],
    'depends': ['l10n_ar_wsafip', 'l10n_ar_invoice'],
    'description': '\n\nAPI e GUI para acceder a las Web Services de Factura Electr\xc3\xb3nica de la AFIP\n\n',
    'init_xml': ['data/afip.wsfe_error.csv'],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Web Services de Factura Electr\xc3\xb3nica del AFIP',
    'test': [   'test/test_key.yml',
                'test/partners.yml',
                'test/products.yml',
                'test/com_ri1.yml',
                'test/com_ri2.yml',
                'test/com_rm1.yml',
                'test/journal.yml'],
    'update_xml': [   'data/wsafip_server.xml',
                      'data/invoice_view.xml',
                      'data/invoice_workflow.xml',
                      'data/journal_view.xml',
                      'data/wsfe_error_view.xml',
                      'data/reports.xml',
                      'data/wsafip_fe_config.xml',
                      'data/res_config_view.xml',
                      'security/wsafip_fe_security.xml',
                      'security/ir.model.access.csv',
                      'wizard/query_invoices_view.xml',
                      'wizard/validate_invoices_view.xml'],
    'version': '2.7.244',
    'website': 'https://launchpad.net/~openerp-l10n-ar-localization'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
