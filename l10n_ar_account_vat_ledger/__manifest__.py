{
    "name": "Argentinian VAT Ledger Management",
    'version': '9.0.1.7.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA,Moldeo Interactive,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': '',
    "depends": [
        # TODO we should try to get this report with another tool, not aeroo
        "report_aeroo",
        "l10n_ar_account",
    ],
    'external_dependencies': {
    },
    "data": [
        'views/account_vat_report_views.xml',
        'report/account_vat_ledger_report.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
