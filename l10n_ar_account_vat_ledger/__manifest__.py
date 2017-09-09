# -*- coding: utf-8 -*-
{
    "name": "Argentinian VAT Ledger Management",
    'version': '9.0.1.4.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA,Moldeo Interactive,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': '',
    "depends": [
        # TODO we should try to get this report with another tool, not aeroo
        "report_aeroo",
        "l10n_ar_account",
        "report_custom_filename",
        "date_range",
        # "account_fiscal_year",
    ],
    'external_dependencies': {
    },
    "data": [
        'account_vat_report_view.xml',
        'report/account_vat_ledger_report.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'test': [
    ],
    'images': [
    ],
    'installable': False,
    'auto_install': True,
    'application': False,
}
