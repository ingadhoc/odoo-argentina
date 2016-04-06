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
    'name': 'Argentina - Base para los Web Services del AFIP',
    'version': '8.0.1.1.2',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Configuración y API para acceder a las Web Services de la AFIP
==============================================================

Homologation / production:
--------------------------
First it search for a paramter "afip.ws.env.type" if exists and:
* is production --> production
* is homologation --> homologation
Else
Search for 'server_mode' parameter on conf file. If that parameter:
* has a value then we use "homologation",
* if no parameter, then "production"

Incluye:
--------
* Wizard para instalar los claves para acceder a las Web Services.
* API para realizar consultas en la Web Services desde OpenERP.

El módulo l10n_ar_afipws permite a OpenERP acceder a los servicios del AFIP a
travésde Web Services. Este módulo es un servicio para administradores y
programadores, donde podrían configurar el servidor, la autentificación
y además tendrán acceso a una API genérica en Python para utilizar los
servicios AFIP.

Para poder ejecutar los tests es necesario cargar la clave privada y el
certificado al archivo test_key.yml.

Tenga en cuenta que estas claves son personales y pueden traer conflicto
publicarlas en los repositorios públicos.
""",
    'depends': [
        # 'base',
        # this dependency is becaouse of CUIT request and some config menus
        'l10n_ar_invoice',
        ],
    'external_dependencies': {
        'python': ['suds', 'M2Crypto', 'pyafipws']
    },
    'data': [
        'data/afipws_sequence.xml',
        'wizard/upload_certificate_view.xml',
        'views/afipws_menuitem.xml',
        'views/afipws_certificate_view.xml',
        'views/afipws_certificate_alias_view.xml',
        'views/afipws_connection_view.xml',
        'views/res_company_view.xml',
        # 'wizard/config_view.xml',
        'security/ir.model.access.csv',
        ],
    'demo': [
        'demo/certificate_demo.xml',
        'demo/parameter_demo.xml',
        ],
    'test': [
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
