{
    'name': 'Modulo Base para los Web Services de AFIP',
    'version': '11.0.1.0.0',
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
        'python': ['pyafipws', 'OpenSSL', 'pysimplesoap']
    },
    'data': [
        'wizard/upload_certificate_view.xml',
        'views/afipws_menuitem.xml',
        'views/afipws_certificate_view.xml',
        'views/afipws_certificate_alias_view.xml',
        'views/afipws_connection_view.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'demo': [
        'demo/certificate_demo.xml',
        'demo/parameter_demo.xml',
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
