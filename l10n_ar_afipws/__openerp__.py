# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Base para los Web Services del AFIP',
    'version': '9.0.0.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA, Moldeo Interactive',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        # this dependency is becaouse of CUIT request and some config menus
        'l10n_ar_partner',
        ],
    'external_dependencies': {
        'python': ['suds', 'M2Crypto', 'OpenSSL']
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
