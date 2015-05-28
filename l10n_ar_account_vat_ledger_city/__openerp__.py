{
    "name": "Argentinian CITI Reports",
    "description": """
Argentinian CITI Reports
========================
Argentinian CITI Reportsto comply with RG3685
    """,
    "version": "0.1",
    'author': 'ADHOC SA',
    'website': 'www.ingadhoc.com',
    "depends": [
        "l10n_ar_account_vat_ledger",
    ],
    "category": "Reporting subsystems",
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_vat_report_view.xml',
    ],
    "installable": True,
    "active": False
}
