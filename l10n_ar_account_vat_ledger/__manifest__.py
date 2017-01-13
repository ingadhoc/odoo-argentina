# -*- coding: utf-8 -*-
{
    "name": "Argentinian VAT Ledger Management",
    'version': '10.0.1.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA,Moldeo Interactive',
    'license': 'AGPL-3',
    'summary': '',
    "depends": [
        # TODO we should try to get this report with another tool, not aeroo
        # "report_aeroo",
        "l10n_ar_account"
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
    "installable": True,
    'auto_install': False,
    'application': False,
}
