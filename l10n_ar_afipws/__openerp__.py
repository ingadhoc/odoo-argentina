# -*- coding: utf-8 -*-
{
    'name': 'Modulo Base para los Web Services de AFIP',
    'version': '9.0.1.2.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA, Moldeo Interactive,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        # this dependency is becaouse of CUIT request and some config menus
        'l10n_ar_partner',
    ],
    'external_dependencies': {
        'python': ['suds', 'M2Crypto', 'pyafipws']
    },
    'data': [
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
    'images': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
