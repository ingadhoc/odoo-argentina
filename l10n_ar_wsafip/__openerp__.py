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
    'demo_xml': [],
    'depends': ['crypto'],
    'description': '\n\nConfiguraci\xc3\xb3n y API para acceder a las Web Services de la AFIP\n\n\n\nIncluye:\n\n - Wizard para instalar los claves para acceder a las Web Services.\n\n - API para realizar consultas en la Web Services desde OpenERP.\n\n\n\nEl m\xc3\xb3dulo l10n_ar_wsafip permite a OpenERP acceder a los servicios del AFIP a trav\xc3\xa9s de Web Services. Este m\xc3\xb3dulo es un servicio para administradores y programadores, donde podr\xc3\xa1n configurar el servidor, la autentificaci\xc3\xb3n y adem\xc3\xa1s tendr\xc3\xa1n acceso a una API gen\xc3\xa9rica en Python para utilizar los servicios AFIP.\n\n\n\nPara poder ejecutar los tests es necesario cargar la clave privada y el certificado al archivo test_key.yml. Tenga en cuenta que estas claves son personales y pueden traer conflicto publicarlas en los repositorios p\xc3\xbablicos.\n\n',
    'external_dependencies': {   'python': ['suds']},
    'init_xml': [],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Base para los Web Services del AFIP',
    'test': [   'test/test_key.yml',
                'test/test_mime_signer.yml',
                'test/test_wsafip_service.yml'],
    'update_xml': [   'data/wsafip_sequence.xml',
                      'data/wsafip_server.xml',
                      'data/wsafip_menuitem.xml',
                      'data/wsafip_connection_view.xml',
                      'data/wsafip_server_view.xml',
                      'data/wsafip_config.xml',
                      'security/wsafip_security.xml',
                      'security/ir.model.access.csv'],
    'version': '2.7.244',
    'website': 'https://launchpad.net/~openerp-l10n-ar-localization'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
