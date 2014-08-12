# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Like Invoice Report',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Like Invoice Report
===============================
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'report_extended',
    ],
    'data': [
        'report_paperformat.xml',
        'report_layout_view.xml',
        'view/report_ar_header.xml',
        'data/report_configuration_defaults_data.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: