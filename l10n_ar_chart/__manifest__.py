{
    'name': 'Argentina - Planes Contables',
    'author': 'Moldeo Interactive,ADHOC SA,Odoo Community Association (OCA)',
    'category': 'Localization/Account Charts',
    'license': 'AGPL-3',
    'depends': [
        # for afip_code on fiscal position and other tax modifications
        'l10n_ar_account',
        'account_withholding',
        'account_check',
    ],
    'data': [
        'data/account.account.template.csv',
        'data/account_chart_template.xml',
        'data/account_tax_withholding_template.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'images': [
    ],
    'version': "13.0.1.0.0",
}
