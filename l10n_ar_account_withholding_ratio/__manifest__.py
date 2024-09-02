{
    'name': 'Argentinean Withholding Ratio',
    'version': "16.0.1.0.0",
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar_account_withholding',
        'account_withholding_automatic',
    ],
    'data': [
        'views/account_tax_view.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
