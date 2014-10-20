{
    "name": "Argentinian VAT Ledger Management",
    "description": """
Argentinian VAT Ledger Management
=================================
Creates Sale and Purchase VAT report menus in
"accounting/period processing/VAT Ledger"
    """,
    "version": "0.1",
    'author': 'ADHOC SA',
    'website': 'www.ingadhoc.com',
    "depends": [
        "report_aeroo",
        "l10n_ar_invoice"
    ],
    "category": "Reporting subsystems",
    "data": [
        'account_vat_report_view.xml',
        'report/account_vat_ledger_report.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
    "active": False
}
