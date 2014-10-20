# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Like Receipt Aeroo Report',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Like Receipt Aeroo Report
=====================================
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'report_extended_voucher_receipt',
        'account_check',
        'l10n_ar_aeroo_base',
        'l10n_ar_invoice',
    ],
    'data': [
        'receipt_report.xml',
        'voucher_receipt_template.xml',
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