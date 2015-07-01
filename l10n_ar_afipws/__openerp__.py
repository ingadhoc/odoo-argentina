# -*- coding: utf-8 -*-
{'active': False,
    'author': 'OpenERP - Team de Localización Argentina',
    'category': 'Localization/Argentina',
    'demo': [
        'demo/certificate_demo.xml',
    ],
    'depends': [
        'base',
        'l10n_ar_invoice',  # this dependency is becaouse of CUIT request and some config menus
        ],
    'description': """
Configuración y API para acceder a las Web Services de la AFIP
==============================================================

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
    'external_dependencies': {'python': ['suds', 'M2Crypto']},
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Base para los Web Services del AFIP',
    'test': [
    ],
    'data': [
        'data/afipws_sequence.xml',
        'wizard/upload_certificate_view.xml',
        'views/afipws_menuitem.xml',
        'views/afipws_certificate_view.xml',
        'views/afipws_certificate_alias_view.xml',
        'views/afipws_connection_view.xml',
        'views/res_company_view.xml',
        'wizard/config_view.xml',
        'security/ir.model.access.csv',
    ],
    'version': '2.7.244', }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
