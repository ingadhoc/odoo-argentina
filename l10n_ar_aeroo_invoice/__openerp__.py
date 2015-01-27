# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Like Invoice Aeroo Report',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Like Invoice Aeroo Report
=====================================
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'report_extended_account',
        'l10n_ar_invoice',
        'l10n_ar_aeroo_base',
    ],
    'data': [
        'report_configuration_defaults_data.xml',
        'invoice_report.xml',
        'invoice_template.xml',
        'report_view.xml',
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