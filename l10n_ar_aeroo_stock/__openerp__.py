# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Like Stock Picking Aeroo Report',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Like Stock Picking Aeroo Report
===========================================
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'report_extended_stock',
        'l10n_ar_aeroo_base',
        'l10n_ar_invoice',
        'stock_voucher',
    ],
    'data': [
        'report_configuration_defaults_data.xml',
        'report.xml',
        'stock_picking_template.xml',
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
