# v7.0 - Beta.
{
    "name": "Argentina VAT Reports",
    "description": """
Argentina VAT Reports
=====================
Creates Sale and Purchase VAT report menus in "accounting/reporting/taxes report"

It requires pentaho_reports module, you can find it in https://github.com/WillowIT/Pentaho-reports-for-OpenERP
    """,
    "version": "0.1",
    'author': 'Sistemas ADHOC',
    'website': 'http://www.sistemasadhoc.com.ar',
    "depends": ["pentaho_reports", "l10n_ar_invoice"],
    "category": "Reporting subsystems",
    "data": [
            'wizard/report_prompt.xml',
            'report/report_data.xml',
             ],
    "installable": True,
    "active": False
}
