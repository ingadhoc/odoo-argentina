# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Like Voucher Aeroo Report',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Like Voucher Aeroo Report
=====================================
Utilice este modulo en vez de l10n_ar_aeroo_receipt si prefiere no utilizar el modulo account_voucher_receipt.
    """,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'images': [
    ],
    'depends': [
        'report_extended_voucher',
        'account_check',
        'account_voucher_withholding',
        'l10n_ar_aeroo_base',
        'l10n_ar_invoice',
    ],
    'data': [
        'receipt_report.xml',
        'voucher_template.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
