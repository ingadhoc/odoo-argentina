{
    "name": "Argentinian CITI Reports",
    'version': '9.0.1.3.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA,Moldeo Interactive,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': '',
    "depends": [
        "l10n_ar_account_vat_ledger",
    ],
    'external_dependencies': {
    },
    "data": [
        'views/account_vat_report_view.xml',
        'views/account_document_type_view.xml',
        'data/account.document.type.csv',
    ],
    'demo': [
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
