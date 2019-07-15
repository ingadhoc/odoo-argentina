{
    "name": "Argentinian VAT Ledger Management",
    'version': '12.0.1.0.0',
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
        'data/l10n_ar_account_vat_ledger_data.xml',
        'report/account_vat_ledger_report.xml',
        'views/account_vat_report_views.xml',
        'wizards/res_config_settings_views.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'images': [
    ],
    'installable': False,
    'auto_install': True,
    'application': False,
}
