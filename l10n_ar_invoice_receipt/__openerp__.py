# -*- coding: utf-8 -*-
{
    'name': 'Voucher Receipts and Invoice Integration',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'sequence': 14,
    'summary': '',
    'description': """
Receipt
=======
TODO
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'account_voucher_receipt',
        'l10n_ar_invoice',
    ],
    'data': [
        'views/receiptbook_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}