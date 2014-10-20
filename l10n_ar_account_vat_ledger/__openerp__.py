{
    "name": "Argentina VAT Reports",
    "description": """
Argentina VAT Reports
=====================
Creates Sale and Purchase VAT report menus in
"accounting/reporting/taxes report"
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
        # 'wizard/report_prompt.xml',
        # 'report/report_data.xml',
        'account_vat_report_view.xml',
        'report/account_vat_ledger_report.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
    "active": False
}
