# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Sale Total Fields',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Sale Total Fields
=============================
Add fields in sale orders so that you can print sale orders with vay included or not depending on VAT responsabilities
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'sale',
        'l10n_ar_invoice',
    ],
    'data': [
        'sale_view.xml',
        'res_company_view.xml',
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