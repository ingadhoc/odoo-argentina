# -*- coding: utf-8 -*-


{
    'name': 'Hider Purchase/Sale Receipts Menus',
    'version': '1.0',
    'category': 'Argentinian Localization',
    'sequence': 14,
    'summary': 'localization, argentina, recepits, sale, purchase',
    'description': """
Hide Sale Receipt, Purchase recepit and Sale receipts analysis menus
    """,
    'author':  'Sistemas ADHOC',
    'website': 'www.sistemasadhoc.com.ar',
    'images': [
    ],
    'depends': [
        'account_voucher'
    ],
    'data': [
        'security_groups.xml',
        'account_voucher_view.xml',
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